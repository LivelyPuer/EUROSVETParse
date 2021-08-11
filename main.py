import asyncio
import logging
import sys
import time
import traceback

import requests
import datetime as dt
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from lxml import etree
from lxml.etree import ParserError
import csv

properties = ['Наименование', "Код товара", "Артикул", "Серия", "Торговая марка", "Цена", "URL адрес", "Фото товара",
              "Вес", "Размеры"]
# TODO  артикул: {свойство: характеристика}
products = {}
CATEGORY = "Категория: "
FORMAT = '%(asctime)-15s %(message)s'
START_TIME = dt.datetime.now().strftime("%d.%m.%Y(%H.%M.%f)")
PROPERTY = "Свойство: "
logging.basicConfig(filename=f'logs/{START_TIME}.log', filemode='w', level=logging.DEBUG,
                    format=FORMAT)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))


def delta_start_now_time():
    return str(time.time() - start_time_perser)


def check_dimensions(dimensions_dict: dict):
    if len(dimensions_dict.keys()) == 3:
        return f'{dimensions_dict["Ширина"]}x{dimensions_dict["Высота"]}x{dimensions_dict["Длина"]}'
    return None


async def get_product(url: str):
    logging.info("Start product: " + url)
    url_name = url.split('/')[-1]
    headers = {'Content-Type': 'text/html', }
    response = requests.get(url, headers=headers)
    html_doc = response.content
    try:
        parser = etree.HTMLParser(encoding='utf-8')
        html_dom = etree.HTML(html_doc, parser)
    except ParserError as e:
        logging.error(e)
    if url_name not in products.keys():
        short_name = html_dom.xpath('//h1[@class="mt0 mb5 hidden-sm hidden-xs"]/text()')[0].strip()
        table = html_dom.xpath('//li[@class="mb5"]/text()')

        try:
            price = html_dom.xpath('//div[@class="h1 mt5 mb30"]/strong/text()')[0].split('\u20bd')[0].strip()
        except:
            price = ""
        products[url_name] = {"count": 1, "Цена": price, "URL адрес": url_name}
        for item in table:
            ikey, ivalue = item.split(":")[0].strip(), item.split(":")[-1].strip()
            if table[0].split(":")[0].strip() in ["Код товара", "Артикул", "Серия", "Торговая марка"]:
                products[url_name][ikey] = ivalue
        try:
            products[url_name]['Наименование'] = short_name + " " + products[url_name]["Артикул"]
        except:
            pass
        # print(html_dom.xpath('//div[@class="main-photo-container lightSlider lSFade lsGrab"]'))
        photos = '; '.join(list(map(lambda x: "https:" + x, html_dom.xpath(
            '//a[contains(@class,"main-photo-link")]/@href'))))
        products[url_name]["Фото товара"] = photos
        logging.debug(photos)
        # exit()

        i = 0
        now_pr = ''
        dimensions = {}
        for property_product in html_dom.xpath('//table[@class="table table-condensed"]//tr/td/text()'):
            pr_items = property_product.strip()
            if pr_items == "Вес":
                now_pr = "Вес"
            elif pr_items in ["Длина", "Ширина", "Высота"] and pr_items not in dimensions.keys():
                dimensions[pr_items] = ""
                now_pr = pr_items
                i += 1
                continue
            elif now_pr in ["Длина", "Ширина", "Высота"]:
                dimensions[now_pr] = pr_items.split('мм')[0].strip()
                out = check_dimensions(dimensions)
                if out is not None:
                    products[url_name]["Размеры"] = out
                i += 1
                now_pr = ""
                continue
            elif i % 2 == 0:
                if PROPERTY + pr_items not in properties:
                    properties.append(PROPERTY + pr_items)
                now_pr = PROPERTY + pr_items
            else:
                if now_pr in products[url_name].keys():
                    i += 1
                    continue
                if now_pr == "Вес":
                    products[url_name][now_pr] = pr_items.split("кг")[0].strip()
                else:
                    products[url_name][now_pr] = pr_items
            i += 1
    else:
        products[url_name]["count"] += 1
        logging.info("Повтор: " + str(products[url_name]["count"]))
    count_product = products[url_name]["count"]
    now_category = CATEGORY + str(count_product)
    if now_category not in properties:
        properties.append(now_category)
    products[url_name][now_category] = ' >> '.join(
        [a.strip() for a in html_dom.xpath('//ol[@class="breadcrumb"]/li[position() > 1]/a/text()')])
    logging.info("Dimensions: " + products[url_name]["Размеры"])
    logging.info("Time spent: " + delta_start_now_time())
    logging.info("End product: " + url)


def get_catalog(url, products: list):
    logging.info("Start catalog: " + url)
    i = 0
    while i < len(products):
        try:
            logging.info(f"Complite {i + 1}/{len(products)}")
            asyncio.run(get_product(products[i].get_attribute("href")))
            i += 1
        except Exception as e:
            logging.error(e)
            logging.error(traceback.format_exc())

    logging.info("Time spent: " + delta_start_now_time())
    logging.info("End catalog: " + url)


start_time_perser = time.time()
chrome_options = Options()
chrome_options.add_argument('--headless')
driver = webdriver.Chrome(options=chrome_options)
driver.implicitly_wait(30)
driver.maximize_window()

driver.get("https://eurosvet.ru/catalog/lustri")
elems = driver.find_elements_by_xpath('//div[@class="mb30 filters"][1]//li/a')
catalogs = [elem.get_attribute("href") for elem in elems]
for catalog in catalogs:
    driver.get(catalog)
    driver.find_element_by_xpath('//div[@class="pull-right mr15-xs"]//button').click()
    driver.find_element_by_xpath(
        '//div[@class="pull-right mr15-xs"]//li/a[@data-catalog-navigation-item="3000"]').click()
    while True:
        try:
            time.sleep(10)
            products_by = driver.find_elements_by_xpath('//a[@class="product-item-link relative"]')
            get_catalog(driver.current_url, products_by)
            break
        except:
            time.sleep(10)

logging.info("All catalogs was parsed: " + delta_start_now_time())
logging.info(f"Start write to csv/{START_TIME}.csv")
with open(f'csv/{START_TIME}.csv', 'w', encoding='utf-8', newline="") as csvfile:
    writer = csv.DictWriter(csvfile, fieldnames=properties, delimiter=";")
    writer.writeheader()
    for value in products.values():
        del value["count"]
        writer.writerow(value)
    csvfile.close()
logging.info("Successful! " + f"Time spent: {delta_start_now_time()}")
