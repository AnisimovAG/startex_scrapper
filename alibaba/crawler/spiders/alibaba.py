# -*- coding: utf-8 -*-
import asyncio
import sys
from typing import Optional

import scrapy
from json import loads
import requests
# from scrapypuppeteer import PuppeteerRequest as PuppeteerRequestOther, PuppeteerResponse
from asgiref.sync import sync_to_async
from scrapy_puppeteer import PuppeteerRequest
# from scrapypuppeteer.actions import Scroll, GoTo
import os

from scrapy_puppeteer.middlewares import as_deferred
from selectorlib import Extractor, Formatter

import re
import logging
from transliterate.decorators import transliterate_function

from ..alibaba_puppeteer import AlibabaPuppeteerRequest
from ..items import AlibabaItem
from ..settings import NEED_SECOND_PASS
from ...models import AlibabaProduct

logging.getLogger("selenium").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


@sync_to_async
def set_not_found_property():
    AlibabaProduct.objects.update(not_found=True)


def translit_or_none(text: Optional[str]) -> Optional[str]:
    if text:
        return translit(text)
    else:
        return text


@transliterate_function(language_code='ru', reversed=True)
def translit(text: str) -> str:
    return text


def get_clean_link(link: str) -> str:
    symbols = '#%"[]'
    result = link
    for symbol in symbols:
        result = result.replace(symbol, '')
    return result


class PhotoLink(Formatter):
    def format(self, text: str) -> str:
        return re.search(r'.+(?=\_)', text).group(0)


class Price(Formatter):
    def format(self, text: str) -> Optional[str]:
        text = text.replace(',', '.')
        price = re.findall(r'\d+\.\d+', text)
        if price:
            return price[0]
        return None

    @staticmethod
    def get_two_prices(text: str) -> Optional[str]:
        text = text.replace(',', '.')
        price = re.findall(r'\d+\.\d+', text)
        if len(price) > 0:
            return price[0], price[1] if len(price) > 1 else None
        return None


class VideoLink(Formatter):
    def format(self, text: str) -> Optional[str]:
        if text:
            return text.split('?')[0]
        return text


class AlibabaCrawlerSpider(scrapy.Spider):
    name = 'alibaba'
    allowed_domains = ['alibaba.com']
    search_extractor = Extractor.from_yaml_file(
        os.path.join(os.path.dirname(__file__), "../resources/search_results.yml"))
    product_extractor = Extractor.from_yaml_file(
        os.path.join(os.path.dirname(__file__), "../resources/product_details.yml"),
        formatters=[PhotoLink, VideoLink]
    )
    color_div_extractor = Extractor.from_yaml_file(
        os.path.join(os.path.dirname(__file__), "../resources/color_div.yml"))
    color_span_extractor = Extractor.from_yaml_file(
        os.path.join(os.path.dirname(__file__), "../resources/color_span.yml"))
    price_li_extractor = Extractor.from_yaml_file(
        os.path.join(os.path.dirname(__file__), "../resources/price_li.yml"),
        formatters=[Price]
    )
    price_cpan_extractor = Extractor.from_yaml_file(
        os.path.join(os.path.dirname(__file__), "../resources/price_cpan.yml"))
    logger = logging.getLogger()

    page = 1
    max_pages = 0

    def start_requests(self):

        url = "https://russian.alibaba.com/trade/search?spm=a27aq.13929326.IndustryCategory.2.5219393b5O16XC&CateId=100000266&SearchText=%D0%A2%D0%BA%D0%B0%D0%BD%D0%B8&language=ru&indexArea=product_en"

        yield AlibabaPuppeteerRequest(
            url=url,
            callback=self.parse_list,
            scroll_page=True,
            wait_for={
                'selectorOrFunctionOrTimeout': '//i[contains(@class, "ui2-icon-loading")]',
                'options': {'hidden': True}
            }
        )

    def parse_product_details(self, response):

        if response.status == 200:
            url_english = f'https:{response.text.split("english=")[1].split(",")[0]}'
            data = self.product_extractor.extract(response.text, base_url=response.url)
            product = AlibabaItem()
            product['id'] = data['id']
            product['sku'] = data['id']
            product['mpn'] = f'{data["id"]}-00'
            product['brand_name'] = {
                '@type': 'Brand',
                'name': 'Ali'
            }
            product['name'] = data['name']
            product['url'] = response.url
            product['product_description_html'] = data['product_description1'] if data['product_description1'] else \
            data[
                'product_description2']
            product['photos'] = data['photos']
            product['video'] = data['video']
            product['supplier_name'] = data['supplier_name']
            product['supplier_url'] = data['supplier_url']
            product['category'] = '/'.join(data['category']['hierarchy'])

            try:
                if '<li data-role="ladder-price-item"' in data['prices']:
                    prices = self.price_li_extractor.extract(data['prices'])
                    prices_dict = {f'price_{idx + 1}': i['price'] for idx, i in enumerate(prices['prices'])}
                    prices_dict.update(
                        {f'threshold_{idx + 1}': i['threshold'] for idx, i in enumerate(prices['prices'])})
                else:
                    prices = self.price_cpan_extractor.extract(data['prices'])
                    price2, price1 = Price.get_two_prices(prices['price'])
                    if price1:
                        prices_dict = {
                            'price_1': price1,
                            'threshold_1': f'<{prices["threshold"]}',
                            'price_2': price2,
                            'threshold_2': f'>={prices["threshold"]}',
                        }
                    else:
                        prices_dict = {'price_1': price2}
                product['prices'] = prices_dict
            except Exception as error:
                self.logger.error(f'Ошибка разбора цен в {response.url}')
                self.logger(error.with_traceback(sys.exc_info()[2]))
                product['prices'] = None

            try:
                if data['colors']:
                    if (data['colors'][0].startswith('<span') and data['colors'][-1].startswith('<span')) or \
                            data['colors'][0].startswith('<a '):
                        if '<img' in data['colors'][0]:
                            colors = {f'color_name{idx + 1}': self.color_span_extractor.extract(i)["photo_name"]
                                      for idx, i in enumerate(data['colors'])}
                            colors.update(
                                {f'color_photo{idx + 1}': self.color_span_extractor.extract(i)["photo"]
                                 for idx, i in enumerate(data['colors'])}
                            )
                        else:
                            colors = {f'color_name{idx + 1}': self.color_span_extractor.extract(i)["name"]
                                      for idx, i in enumerate(data['colors'])}
                    else:
                        colors = {f'color_name{idx + 1}': i for idx, i in enumerate(
                            filter(lambda x: x, [self.color_div_extractor.extract(j)["name"] for j in data['colors']]))}
                        colors.update(
                            {f'color_photo{idx + 1}': i
                             for idx, i in enumerate(filter(lambda x: x,
                                                            [self.color_div_extractor.extract(j)["photo"] for j in
                                                             data['colors']]))}
                        )
                else:
                    colors = None
                product['colors'] = colors
            except Exception as error:
                self.logger.error(f'Ошибка разбора цветов в {response.url}')
                self.logger(error.with_traceback(sys.exc_info()[2]))
                product['colors'] = None

            try:
                if data['production']:
                    product['production'] = {f'threshold_to_production{idx + 1}': i
                                             for idx, i in enumerate(data['production']['thresholds'][1:])}
                    product['production'].update(
                        {f'days_to_production{idx + 1}': i
                         for idx, i in enumerate(data['production']['days'][1:])}
                    )
                else:
                    product['production'] = None
            except Exception as error:
                self.logger.error(f'Ошибка разбора сроков изготовления в {response.url}')
                self.logger(error.with_traceback(sys.exc_info()[2]))
                product['production'] = None

            try:
                english = {item['attrNameId']: item['attrName'] for item in filter(lambda x: x.get('attrNameId'),
                                                                                   loads(
                                                                                       requests.get(
                                                                                           url_english).text.split(
                                                                                           '"productBasicProperties":')[
                                                                                           1].split(']')[0] + ']'))}
            except Exception as error:
                print(f'Ошибка запроса(requests) в {url_english}')
                print(error.with_traceback())

            try:
                product['quick_details'] = {english[i['attrNameId']] if english.get('attrNameId')
                                            else translit_or_none(i['attrName']): i['attrValue'] for i in
                                            loads(requests.get(response.url).text.split('"productBasicProperties":')[1].
                                                  split(']')[0] + ']')}
            except Exception as error:
                print(f'Ошибка запроса(requests) в {response.url}')
                print(error.with_traceback())

            try:
                if data['specification1']:
                    product['specification'] = {f'spec_{translit_or_none(i["name"])}': i['value'] for i in
                                                data['specification1']}
                elif data['specification2']:
                    product['specification'] = {f'spec_{translit_or_none(i["name"])}': i['value'] for i in
                                                data['specification2']}
                else:
                    product['specification'] = None
            except Exception as error:
                self.logger.error(f'Ошибка разбора спецификации в {response.url}')
                self.logger(error.with_traceback(sys.exc_info()[2]))
                product['specification'] = None

            yield product

    async def parse_list(self, response):
        data = self.search_extractor.extract(response.text, base_url=response.url)
        if data['products']:
            for product in data['products']:
                if product['link']:  # Может быть реклама, там линка нет
                    yield AlibabaPuppeteerRequest(
                        url=get_clean_link(product['link']),
                        callback=self.parse_product_details,
                        wait_until=['domcontentloaded', 'networkidle0']
                    )

            # Try paginating if there is data
            self.page += 1
            if self.max_pages == 0 or self.max_pages > self.page:
                if self.page == 2:
                    url = f'{response.request.url}&page=2'
                else:
                    url = re.sub('(^.*?&page\=)(\d+)(.*$)', rf"\g<1>{self.page}\g<3>", response.request.url)

                yield AlibabaPuppeteerRequest(
                    url=url,
                    callback=self.parse_list,
                    scroll_page=True,
                    wait_for={
                        'selectorOrFunctionOrTimeout': '//i[contains(@class, "ui2-icon-loading")]',
                        'options': {'hidden': True}
                    }
                )
        else:
            if NEED_SECOND_PASS:
                iterator = AlibabaProduct.objects.filter(not_found=True).iterator()
                while True:
                    try:
                        product = await sync_to_async(next)(iterator)
                        yield AlibabaPuppeteerRequest(
                            url=product.url,
                            callback=self.parse_product_details,
                            wait_until=['domcontentloaded', 'networkidle2']
                        )
                    except StopIteration:
                        break


