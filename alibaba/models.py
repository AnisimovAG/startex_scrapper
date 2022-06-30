from django.db import models


class AlibabaProduct(models.Model):
    id = models.TextField(primary_key=True)
    sku = models.TextField()
    mpn = models.CharField(max_length=20)
    name = models.CharField(max_length=1000)
    url = models.URLField(null=True)
    brand_name = models.JSONField(null=True)
    product_description_html = models.TextField(null=True)
    prices = models.JSONField(null=True)
    colors = models.JSONField(null=True)
    production = models.JSONField(null=True)
    quick_details = models.JSONField(null=True)
    specification = models.JSONField(null=True)
    photos = models.JSONField(null=True)
    video = models.URLField(null=True)
    supplier_name = models.CharField(max_length=100, null=True)
    supplier_url = models.URLField(null=True)
    category = models.CharField(max_length=200, null=True)
    date_created = models.DateTimeField(verbose_name='Дата создания', auto_now_add=True)
    date_updated = models.DateTimeField(verbose_name='Дата обновления', auto_now=True, default=None, null=True)
    fields_to_update = models.JSONField(verbose_name='Обновленные поля', default=None, null=True)
    not_found = models.BooleanField(verbose_name="Не найдено в поиске Али", default=False, null=True)

    class Meta:
        managed = False
        db_table = 'partners_alibabaproduct'

    def __str__(self):
        return self.name
