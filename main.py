import asyncio
import logging
import sys
import time
import traceback
from pprint import pprint

import requests
import datetime as dt
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from lxml import etree
from lxml.etree import ParserError
import csv

properties = ['Наименование', "Код товара", "Артикул", "Свойство: Серия", "Свойство: Бренд", "Цена", "URL адрес",
              "Фото товара",
              "Вес в кг", "Размеры в мм", "Категория: 1", "Краткое описание", "Описание", "Свойство: Помещение",
              "Свойство: Рекомендуемая площадь освещения", "Количество", "Свойство: Тип светильника",
              "Свойство: Стили и тенденции", "Свойство: Торговые марки",
              "Видео"]
need_properties = ["Вес", "Рекомендуемая площадь освещения", "Помещение", "Длина", "Ширина", "Высота"]
properties_w_pr = ["Рекомендуемая площадь освещения", "Помещение"]
# TODO  артикул: {свойство: характеристика}
products = {}
CATEGORY = "Категория: "
FORMAT = '%(asctime)-15s %(message)s'
START_TIME = dt.datetime.now().strftime("%d.%m.%Y(%H.%M.%f)")
PROPERTY = "Свойство: "
logging.basicConfig(filename=f'logs/{START_TIME}.log', filemode='w', level=logging.DEBUG,
                    format=FORMAT)
logging.getLogger().addHandler(logging.StreamHandler(sys.stdout))
change = {"Торговая марка": "Свойство: Бренд"}

# LOCATORS
SHORT_NAME = '//h1[@class="mt0 mb5 hidden-sm hidden-xs"]/text()'


def tuple_parse(tuples: lambda x: list(tuple(x))) -> dict:
    d_out = {"Описание": ""}
    tmp = {}
    for t_key, t_value in tuples:
        t_key, t_value = t_key.strip(), t_value.strip()
        if t_key in need_properties:
            if t_key in properties_w_pr:
                d_out[PROPERTY + t_key] = t_value if "м кв." not in t_value else t_value.split("м кв.")[0].strip()
            elif t_key == "Вес":
                d_out[t_key + " в кг"] = float(t_value.split("кг")[0].strip())
            else:
                tmp[t_key] = t_value.split('мм')[0].strip()
                out = check_dimensions(tmp)
                if out is not None:
                    d_out["Размеры в мм"] = out
        d_out["Описание"] += f'{t_key}: {t_value}<br>'
    return d_out


def delta_start_now_time():
    return str(time.time() - start_time_perser)


def check_dimensions(dimensions_dict: dict):
    if len(dimensions_dict.keys()) == 3 and '0' not in dimensions_dict.values():
        return f'{dimensions_dict["Ширина"]}x{dimensions_dict["Высота"]}x{dimensions_dict["Длина"]}'
    return None


def get_product(url: str, catalog_name_l: str, type_catalog: str):
    logging.info("Start product: " + url)
    try:
        url_name = url.split('/')[-1]
        headers = {'Content-Type': 'text/html', }
        response = requests.get(url, headers=headers)
        html_doc = response.content
        try:
            parser = etree.HTMLParser(encoding='utf-8')
            html_dom = etree.HTML(html_doc, parser)
        except ParserError as e:
            logging.error(e)
            return
        if url_name not in products.keys():
            short_name = html_dom.xpath(SHORT_NAME)[0].strip()
            table = html_dom.xpath('//li[@class="mb5"]/text()')

            try:
                price = html_dom.xpath('//div[@class="h1 mt5 mb30"]/strong/text()')[0].split('\u20bd')[0].strip()
            except:
                price = ""
            products[url_name] = {"Цена": price, "URL адрес": url_name, "Категория: 1": "Евросвет",
                                  "Краткое описание": '',
                                  "Описание": "",
                                  "Количество": 1000, "Свойство: Тип светильника": "",
                                  "Свойство: Стили и тенденции": "", "Свойство: Торговые марки": ""}
            for item in table:
                ikey, ivalue = item.split(":")[0].strip(), item.split(":")[-1].strip()
                if ikey in ["Код товара", "Артикул", "Серия", "Торговая марка"]:
                    ikey = change.get(ikey, ikey)
                    if ikey == "Серия":
                        products[url_name]["Свойство: Серия"] = ivalue
                    else:
                        products[url_name][ikey] = ivalue
                        products[url_name]["Краткое описание"] += item.strip() + '<br>'
            try:
                products[url_name]['Наименование'] = short_name + " " + products[url_name]["Артикул"]
            except:
                pass
            # print(html_dom.xpath('//div[@class="main-photo-container lightSlider lSFade lsGrab"]'))
            photos = '; '.join(list(map(lambda x: "https:" + x, html_dom.xpath(
                '//a[contains(@class,"main-photo-link")][not(contains(@href, ".svg"))]/@href'))))
            products[url_name]["Фото товара"] = photos
            try:
                video = "https:" + html_dom.xpath("//a//video//source/@src")[0]
                products[url_name]["Видео"] = video
            except:
                pass
            logging.debug(photos)
            i = 0
            table_properties = []
            for property_product in html_dom.xpath('//table[@class="table table-condensed"]//tr/td/text()'):
                pr_items = property_product.strip()
                if i % 2 == 0:
                    table_properties.append([pr_items])
                else:
                    table_properties[-1].append(pr_items)
                i += 1
            for key, value in tuple_parse(table_properties).items():
                products[url_name][key] = value
        products[url_name][PROPERTY + type_catalog] += f'{catalog_name_l}; '
        logging.info("Time spent: " + delta_start_now_time())
        logging.info("End product: " + url)
    except Exception as e:
        tb = sys.exc_info()[2]
        tbinfo = traceback.format_tb(tb)[0]
        logging.error("Not spent, product: " + url)
        logging.error(e.__class__)
        logging.error(tbinfo)


def get_catalog(url, in_products: list, catalog_name_l: str, type_catalog: str):
    logging.info("Start catalog: " + url)
    i = 0
    while i < len(in_products):
        try:
            get_product(in_products[i].get_attribute("href"), catalog_name_l, type_catalog)
            logging.info(f"Complite {i + 1}/{len(in_products)}")
            i += 1
        except Exception as e:
            logging.error(e)
            logging.error(traceback.format_exc())
            continue

    logging.info("Time spent: " + delta_start_now_time())
    logging.info("End catalog: " + url)


def for_catalog(urls: list, type_catalog: str):
    for catalog in urls:
        driver.get(catalog)
        catalog_name = driver.find_element_by_xpath('//h1[@class="mt10 mb10"]').text
        driver.find_element_by_xpath('//div[@class="pull-right mr15-xs"]//button').click()
        driver.find_element_by_xpath(
            '//div[@class="pull-right mr15-xs"]//li/a[@data-catalog-navigation-item="3000"]').click()
        while True:
            try:
                time.sleep(15)
                products_by = driver.find_elements_by_xpath('//a[@class="product-item-link relative"]')
                get_catalog(driver.current_url, products_by, catalog_name, type_catalog)
                print(driver.current_url)
                break
            except:
                time.sleep(10)
                continue
    logging.info(f"Catalog: {type_catalog} successful!")
    return


start_time_perser = time.time()
chrome_options = Options()
chrome_options.add_argument('--headless')
driver = webdriver.Chrome(options=chrome_options)
driver.implicitly_wait(30)
driver.maximize_window()

driver.get("https://eurosvet.ru/catalog/lustri")
elems = driver.find_elements_by_xpath('//ul[@id="filters-type"]//li/a')
catalog_type = (
    [elem.get_attribute("href") for elem in driver.find_elements_by_xpath('//ul[@id="filters-type"]//li/a')],
    "Тип светильника")
catalog_style = (
    [elem.get_attribute("href") for elem in driver.find_elements_by_xpath('//ul[@id="filters-style"]//li/a')],
    "Стили и тенденции")
catalog_brend = (
    [elem.get_attribute("href") for elem in driver.find_elements_by_xpath('//ul[@id="filters-trademark"]//li/a')],
    "Торговые марки")
logging.info(f'Count catalogs {len(catalog_type[0]) + len(catalog_style[0]) + len(catalog_brend[0])}')

for_catalog(*catalog_type)
for_catalog(*catalog_style)
for_catalog(*catalog_brend)

logging.info("All catalogs was parsed: " + delta_start_now_time())
logging.info(f"Start write to csv/{START_TIME}.csv")
try:
    with open(f'csv/{START_TIME}.csv', 'w', encoding='utf-8', newline="") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=properties, delimiter=";")
        writer.writeheader()
        for values in products.values():
            writer.writerow(values)
        csvfile.close()
    logging.info("Successful! " + f"Time spent: {delta_start_now_time()}")
except Exception as e:
    logging.error(e)
    logging.error(traceback.format_exc())
    logging.error("Csv crash!!")
    file = open(f"crash/{START_TIME}.txt", "w", encoding="utf-8")
    file.write(str(products))
    file.close()
    logging.info(f"Successful save crash file: crash/{START_TIME}.txt")
