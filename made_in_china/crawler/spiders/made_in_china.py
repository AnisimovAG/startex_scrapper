# -*- coding: utf-8 -*-
import json
from datetime import datetime
from django.utils import timezone
from typing import Optional

import scrapy
import os
from html import unescape
from selectorlib import Extractor, Formatter

from scrapper.base import truncate_table
from ...models import MadeInChinaCategory
import re
import logging
from ..items import MadeInChinaItem

logging.getLogger("urllib3").setLevel(logging.WARNING)


def get_clean_link(link: str) -> str:
    symbols = '#%"[]'
    result = link
    for symbol in symbols:
        result = result.replace(symbol, '')
    return result


class VideoLink(Formatter):
    def format(self, text: str) -> str:
        return json.loads(text)['videoUrl']


class MoqUnit(Formatter):
    def format(self, text: str) -> Optional[dict]:
        if not text:
            return None
        return {
            'moq': re.sub(r'(\d)\s+(\d)', r'\1\2', text),
            'unit': ' '.join(re.findall(r'[A-Za-zА-яёË]+', text))
        }


class StripColon(Formatter):
    def format(self, text: str) -> str:
        return text.strip(':')


class Unit(Formatter):
    def format(self, text: str) -> str:
        return ' '.join(re.findall(r'[A-Za-zА-яёË]+', text.split('/').pop()))


class Threshold(Formatter):
    def format(self, text: str) -> int:
        return int(''.join(re.findall(r'\d+', text.split('-')[0])) or 0)


class BigPhotoLink(Formatter):
    def format(self, text: str):
        text = re.sub(r'\d+', '2', unescape(text), 1)
        return text if text.startswith('https:') else f'https:{text}'


class AddProtocolHTTPS(Formatter):
    def format(self, text: str):
        return f'https:{unescape(text)}'


class Name(Formatter):
    def format(self, text: str):
        return text.replace('\n', '').strip()


class OnlyOnePrice(Formatter):
    def format(self, text: str) -> list:
        text = text.replace(',', '.')
        return [float(i) for i in reversed(re.findall(r'\d+\.\d+', text))] or [0]


class Price(Formatter):
    def format(self, text: str) -> Optional[float]:
        text = text.replace(',', '.')
        price = re.findall(r'\d+\.\d+', text)
        if price:
            return float(price[0])
        return None

    @staticmethod
    def get_two_prices(text: str):
        text = text.replace(',', '.')
        price = re.findall(r'\d+\.\d+', text)
        if len(price) > 0:
            return price[0], price[1] if len(price) > 1 else None
        return None


class LastActivityDate(Formatter):
    def format(self, text: str) -> datetime:
        return timezone.make_aware(
            datetime.strptime(text.replace('Дата Последнего Входа: ', ''), '%b %d, %Y'),
            timezone.get_current_timezone(),
            True
        )

class MadeInChinaCrawlerSpider(scrapy.Spider):
    name = 'made_in_china'
    allowed_domains = ['made-in-china.com']
    start_urls = [
        'https://ru.made-in-china.com/category23_Textile/Military-Material_yuyyssssss_1.html',
        'https://ru.made-in-china.com/category23_Textile/Denim_yungssssss_1.html',
        'https://ru.made-in-china.com/category23_Textile/Compound-Fabric_yusgssssss_1.html',
        'https://ru.made-in-china.com/category23_Textile/Linen_yuysssssss_1.html',
        'https://ru.made-in-china.com/category23_Textile/Nylon-Fabric_yunhssssss_1.html',
        'https://ru.made-in-china.com/category23_Textile/Printed-Color-woven-Cloth_yuyissssss_1.html',
        'https://ru.made-in-china.com/category23_Textile/Polyester-Fabric_yunessssss_1.html',
        'https://ru.made-in-china.com/category23_Textile/Glistening-Fabric_yuunssssss_1.html',
        'https://ru.made-in-china.com/category23_Textile/Grey-Fabric_yuugssssss_1.html',
        'https://ru.made-in-china.com/category23_Textile/Knitting-Crocheting-Fabric_yuuhssssss_1.html',
        'https://ru.made-in-china.com/category23_Textile/Functional-Textile_yuuissssss_1.html',
        'https://ru.made-in-china.com/category23_Textile/Chemical-Fabrics_1.html',
        'https://ru.made-in-china.com/category23_Textile/Cotton_yushssssss_1.html',
        'https://ru.made-in-china.com/category23_Textile/Silk_yuyhssssss_1.html',
        'https://ru.made-in-china.com/category23_Textile/Leather-Leatheroid_yuuossssss_1.html',
    ]
    search_extractor = Extractor.from_yaml_file(
        os.path.join(os.path.dirname(__file__), "../resources/search_results.yml"),
        formatters=[MoqUnit]
    )
    product_extractor = Extractor.from_yaml_file(
        os.path.join(os.path.dirname(__file__), "../resources/product_details.yml"),
        formatters=[
            Name,
            Price,
            OnlyOnePrice,
            AddProtocolHTTPS,
            Threshold,
            VideoLink,
            BigPhotoLink,
            Unit,
            LastActivityDate
        ]
    )
    spec_keys_eng_extractor = Extractor.from_yaml_file(
        os.path.join(os.path.dirname(__file__), "../resources/keys_english.yml"), formatters=[StripColon])
    logger = logging.getLogger()
    categories = {i.name: i for i in MadeInChinaCategory.objects.all()}

    page = 1
    max_pages = 0

    def start_requests(self):
        truncate_table('madeinchina')
        return super(MadeInChinaCrawlerSpider, self).start_requests()

    def create_product(self, response, data, url):
        if data['prices_thresholds']:
            prices = data['prices_thresholds']['prices_div'] or data['prices_thresholds']['prices_table'] or [0]
            thresholds = data['prices_thresholds']['thresholds'] or data['prices_thresholds']['thresholds_alt'] or [
                data['moq']]
        else:
            prices = [0]
            thresholds = [0]
        data['product_images'] = data['product_images'] or data['product_images_alt']
        keys_english = self.spec_keys_eng_extractor.extract(response.text)

        product = MadeInChinaItem()
        product['url'] = url
        product['category_string'] = '/'.join(data['category']['hierarchy'])
        product['category'] = self.get_or_create_category(data['category']['hierarchy'])
        product['prices'] = {f'price_{idx + 1}': i for idx, i in enumerate(prices)}
        product['prices'].update(
            {f'threshold_{idx + 1}': i for idx, i in enumerate(thresholds)}
        )
        product['moq'] = data['moq'] or str(thresholds[0]) + (f' {data["unit"]}' if data['unit'] else '')
        if data['specification_values'] and keys_english['specification_keys']:
            product['product_info'] = dict(zip(keys_english['specification_keys'], data['specification_values']))
        if data['property_values'] and keys_english['property_keys']:
            product['properties'] = dict(zip(keys_english['property_keys'], data['property_values']))

        for field in product.fields.keys():
            if field in data.keys() and not(getattr(product.instance, field)):
                product[field] = data[field]

        yield product

    def parse_product_details(self, response, moq_unit):
        
        if response.status == 200:
            data = self.product_extractor.extract(response.text, base_url=response.url)
            data.update({'moq': moq_unit['moq']})
            data['unit'] = moq_unit['unit'] or data['unit']
            yield scrapy.Request(
                url=data['url_english'],
                callback=self.create_product,
                cb_kwargs={'data': data, 'url': response.url},
                headers={'Referer': response.request.headers.get('Referer')}
            )
        else:
            self.logger.error(f'Status {response.status} in {response.url}')

    def parse(self, response):
        data = self.search_extractor.extract(response.text, base_url=response.url)
        if response.status == 200:
            if data['products']:
                for product in data['products']:
                    if not product['moq_unit']:
                        product.update({'moq_unit': {'moq': None, 'unit': None}})
                    yield scrapy.Request(
                        url=product['link'],
                        callback=self.parse_product_details,
                        cb_kwargs={'moq_unit': product['moq_unit']}
                    )
                if data['next_page']:
                    yield scrapy.Request(url=data['next_page'], callback=self.parse)
            else:
                self.logger.error(response.url)
        else:
            self.logger.error(f'GET {response.url} status {response.status}')

    def get_or_create_category(self, hierarchy: list) -> MadeInChinaCategory:
        category = hierarchy.pop()
        if not(result := self.categories.get(category)):
            parent = None
            if hierarchy:
                parent = self.get_or_create_category(hierarchy)
            result = MadeInChinaCategory.objects.create(name=category, parent=parent)
            self.categories.update({category: result})
        return result
