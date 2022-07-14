# -*- coding: utf-8 -*-

# Define your item pipelines here
#
# Don't forget to add your pipeline to the ITEM_PIPELINES setting
# See: https://docs.scrapy.org/en/latest/topics/item-pipeline.html
from collections import Counter

from scrapy import signals
from pydispatch import dispatcher

from ..models import AlibabaProduct
from .settings import UPDATE_ITEMS
from scraper.utils import send_email
from asgiref.sync import sync_to_async


def compare_lists(a, b):
    return sorted(a) == sorted(b)


def compare_dicts(a: dict, b: dict) -> bool:
    return Counter(a) == Counter(b)


class AlibabaPipeline(object):
    updated_records = []
    second_pass = False

    def __init__(self):
        dispatcher.connect(self.spider_closed, signals.spider_closed)

    async def process_item(self, item, spider):
        try:
            instance = await sync_to_async(AlibabaProduct.objects.get)(pk=item['id'])
            instance.not_found = False
            updated_fields = {}
            old_updated_fields = instance.fields_to_update or {}
            old_fields = old_updated_fields.keys()
            for field in item.keys():
                if field == "product_description_html":
                    continue
                old = getattr(instance, field)
                new = item[field]
                if isinstance(new, dict):
                    updated = not compare_dicts(old, new)
                elif isinstance(new, list):
                    updated = not compare_lists(old, new)
                else:
                    updated = old != new
                if updated:
                    updated_fields.update({
                        field: {
                            'old': old if field not in old_fields else old_updated_fields[field],
                            'new': new
                        }
                    })

            if updated_fields:
                self.updated_records.append({
                    'id': item['id'],
                    'url': item['url'],
                    'diff': updated_fields
                })
                if UPDATE_ITEMS:
                    fields = list(updated_fields.keys())
                    fields_to_update = {}
                    for field in fields:
                        fields_to_update[field] = updated_fields[field]['old']
                        setattr(instance, field, updated_fields[field]['new'])
                    instance.fields_to_update = {
                        **old_updated_fields,
                        **{field: updated_fields[field]['old'] for field in fields}
                    }
                    fields.append('fields_to_update')
                    fields.append('not_found')
            else:
                fields = ['not_found']
            await sync_to_async(instance.save)(update_fields=fields)
        except AlibabaProduct.DoesNotExist:
            await sync_to_async(AlibabaProduct.objects.create)(**item)
        return item

    def spider_closed(self, spider):
        send_email(spider.name, self.updated_records, UPDATE_ITEMS)



