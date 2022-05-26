from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.options import Options
import requests
from bs4 import BeautifulSoup

from selenium.common.exceptions import NoSuchElementException

from PIL import Image
import io

import time

import pandas as pd

import utils.functions as F
import utils.data as data

from absl import app
from absl import flags
from absl import logging

FLAGS = flags.FLAGS
flags.DEFINE_string('pref_name', 'Yamagata', 'pref name')
flags.DEFINE_string('target', 'suumo', 'suumo or jalan')

def suumo():
    logging.info('Starting suumo scraping')
    house_id = 0
    pref_sum_count = 0

    for url in [data.urls[FLAGS.pref_name]]:
        prefecture_name = FLAGS.pref_name
        pref_sum_count += 1
        url = url
        data_list = []
        page_count = 0

        logging.info(pref_sum_count, prefecture_name)

        options = Options()
        options.add_argument('--headless')
        browser = webdriver.Chrome(ChromeDriverManager().install(), options=options)
        browser.get(url)

	# 次へをクリックして、ページがなくなるまで繰り返しページを探索する
        while True:
            url = browser.current_url
            logging.info(url)
            #ブラウザの起動
            options = Options()
            options.add_argument('--headless')
            browser = webdriver.Chrome(ChromeDriverManager().install(), options=options)

            browser.get(url)

            try:
                res = requests.get(url)
                soup = BeautifulSoup(res.content, 'html.parser')
                urls = F.get_urls(soup) #個別ページのURLを取得
                house_info, house_id = F.get_index_info(urls, data_list, house_id)

                browser.find_element_by_link_text('次へ').click()
                if page_count % 10 == 0:
                    logging.info("pages:{0}".format(page_count))
                    logging.info('==============================================')
                    time.sleep(60)
                time.sleep(60)

                houses_dict = {}
                img_list = []

                for house in house_info:
                    # Pandasで加工しやすいようにKeyが一つの辞書に家の情報を変更する
                    house_id, house_dict = F.edit_house_data(house)
                    houses_dict[house_id] = house_dict
                    # Houseの画像は変更が必要ないので、そのままリストに追加する
                    # ただ、一つづつ取り出して追加する必要があるので、要注意
                    img_list += house['imgs']

                attribute_df = pd.DataFrame(houses_dict).transpose()
                attribute_df.to_csv('csv/suumo/attribute_{filename}_{page_num}.csv'.format(filename = prefecture_name, page_num=page_count))
                imgs_df = pd.DataFrame(img_list)
                imgs_df.to_csv('csv/suumo/imgs_{filename}_{page_num}.csv'.format(filename = prefecture_name, page_num=page_count))

                page_count += 1

            except NoSuchElementException:
                browser.quit()
                break

        logging.info('browser quit')

def jalan():
    logging.info('Starting jalan scraping')
    pref_sum_count = 0

    for url in [data.jalan_urls['Yamagata']]:
        prefecture_name = 'Yamagata'
        pref_sum_count += 1
        landmark_count = 0
        url = url
        data_list = [] #多分いらない
        page_count = 0

        logging.info(pref_sum_count, prefecture_name)

        options = Options()
        options.add_argument('--headless')
        browser = webdriver.Chrome(ChromeDriverManager().install(), options=options)
        browser.get(url)

        # 次へをクリックして、観光地自体のページがなくなるまで繰り返しページを探索する
        while True:
            url = browser.current_url
            logging.info(url)
            #ブラウザの起動
            # ⓪任意の県だけのページを取得
            options = Options()
            options.add_argument('--headless')
            browser = webdriver.Chrome(ChromeDriverManager().install(), options=options)
            browser.get(url)

            try:
                res = requests.get(url)
                soup = BeautifulSoup(res.content, 'html.parser', from_encoding='utf-8')
                urls = F.get_urls(soup, target='jalan') #⓪任意の件に含まれる1ページの全観光地のリンク

                for url in urls:
                    # ①一つの観光地についての口コミ１ページ
                    page_url = "https:" + url + 'kuchikomi'
                    review_count = 0
                    while True:
                        options = Options()
                        options.add_argument('--headless')
                        browser_page = webdriver.Chrome(ChromeDriverManager().install(), options=options)
                        browser_page.get(page_url)

                        page_res = requests.get(page_url)

                        page_current_url = browser_page.current_url
                        page_soup = BeautifulSoup(page_res.content, 'html.parser')

                        # ①観光地のレビュー、一覧ページ
                        all_content = page_soup.find_all('div', attrs={'class' : 'item-listContents'})
                        reviews_dict = {}
                        reviews_img_dict = {}
                        for content in all_content:

                            if F.is_existing_img(content):
                                # ②
                                review_page_soup = F.get_review_page_soup(content)
                                review_property_dict = F.get_jalan_review(review_count, content, review_page_soup)
                                print('img existing content url', review_property_dict['review_page_url'])
                                img_name_list = F.get_review_img(landmark_count, review_count, review_page_soup)

                                review_count += 1
                            page_count += 1

                        try:
                            browser_page.find_element_by_link_text('次へ').click()
                            page_current_url = browser_page.current_url
                            page_url = browser_page.current_url
                        except NoSuchElementException:
                            browser.quit()
                            break

                    reviews_dict[review_count] = {
                                            "レビューID" : review_property_dict['review_id'],
                                            "レビューURL" : review_property_dict['review_page_url'],
                                            "タイトル" : review_property_dict['title'],
                                            "レビュー" : review_property_dict['review'],
                                            "行った時期" : review_property_dict['行った時期'],
                                            "混雑具合" : review_property_dict['混雑具合'],
                                            "滞在時間" : review_property_dict['滞在時間'],
                                            "投稿日" : review_property_dict['投稿日'],
                                            }
                    reviews_img_dict[review_count] = {"imgs" : img_name_list}

                    attribute_df = pd.DataFrame(reviews_dict).transpose()
                    attribute_df.to_csv('csv/jalan/attribute_{filename}_{landmark_count}.csv'.format(filename = prefecture_name, landmark_count=landmark_count))
                    imgs_df = pd.DataFrame(reviews_img_dict)
                    imgs_df.to_csv('csv/jalan/imgs_{filename}_{landmark_count}.csv'.format(filename = prefecture_name, landmark_count=landmark_count))

                    landmark_count += 1

            except NoSuchElementException:
                browser.quit()
                break

        logging.info('browser quit')

def main(argv):
    if FLAGS.target == 'suumo':
        suumo()
    elif FLAGS.target == 'jalan':
	    jalan()

if __name__ == '__main__':
    app.run(main)