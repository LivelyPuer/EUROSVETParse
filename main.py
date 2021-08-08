import asyncio
import time
import requests
import datetime as dt
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from lxml import etree
from lxml.etree import ParserError

properties = ['Наименование', "Код товара", "Артикул", "Серия", "Торговая марка"]
# TODO  артикул: {свойство: характеристика}
products = {}


def printl(s, prefix='', suffix=""):
    print(prefix + str(s) + suffix + "\033[0m")
    with open(f"logs/{START_TIME}.log", "a+") as log:
        log.write(f"[{dt.datetime.now().strftime('%H:%M:%f(%d.%m.%Y)')}] " + str(s) + "\n")
        log.close()


def start_log():
    with open(f"logs/{START_TIME}.log", "a+") as log:
        log.write(START_TIME + '\n')
        log.write("Start logging...\n")


async def get_product(url: str):
    printl("Start product: " + url)
    url_name = url.split('/')[-1]
    headers = {'Content-Type': 'text/html', }
    response = requests.get(url, headers=headers)
    html_doc = response.content
    try:
        parser = etree.HTMLParser(encoding='utf-8')
        html_dom = etree.HTML(html_doc, parser)
    except ParserError as e:
        print(e)
    if url_name not in products.keys():
        short_name = html_dom.xpath('//h1[@class="mt0 mb5 hidden-sm hidden-xs"]/text()')[0].strip()
        table1 = html_dom.xpath('//li[@class="mb5"]/text()')
        code = table1[0].split(":")[-1].strip()
        article = table1[1].split(":")[-1].strip()
        series = table1[2].split(":")[-1].strip()
        mark = table1[3].split(":")[-1].strip()
        products[url_name] = {'Наименование': short_name + " " + article, "Код товара": code, "Артикул": article,
                             "Серия": series, "Торговая марка": mark}
        i = 0
        now_pr = ''
        for property_product in html_dom.xpath('//table[@class="table table-condensed"]//tr/td/text()'):
            pr_items = property_product.strip()
            if i % 2 == 0:
                if pr_items not in properties:
                    properties.append(pr_items)
                now_pr = pr_items
            else:
                products[url_name][now_pr] = pr_items
            i += 1
    print(properties)
    printl("End product: " + url)


def get_catalog(url, products: list):
    printl("Start catalog: " + url)
    i = 0
    while i < len(products):
        try:
            asyncio.run(get_product(products[i].get_attribute("href")))
            i += 1
        except Exception as e:
            printl(e)

    printl("End catalog: " + url)


START_TIME = dt.datetime.now().strftime("%H.%M.%f(%d.%m.%Y)")
start_log()
chrome_options = Options()
chrome_options.add_argument('--headless')
driver = webdriver.Chrome(options=chrome_options)
driver.implicitly_wait(30)
driver.maximize_window()

driver.get("https://eurosvet.ru/catalog/lustri")
elems = driver.find_elements_by_xpath('//div[@class="mb30 filters"][1]//li/a')
print(elems)
catalogs = [elem.get_attribute("href") for elem in elems]
printl(catalogs)
for catalog in catalogs:
    driver.get(catalog)
    driver.find_element_by_xpath('//div[@class="pull-right mr15-xs"]//button').click()
    driver.find_element_by_xpath(
        '//div[@class="pull-right mr15-xs"]//li/a[@data-catalog-navigation-item="3000"]').click()
    time.sleep(5)
    products_by = driver.find_elements_by_xpath('//a[@class="product-item-link relative"]')
    get_catalog(driver.current_url, products_by)
    print(products)
printl("Complite!", prefix="\033[32m")
