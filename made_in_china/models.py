from django.db import models


class MadeInChinaCategory(models.Model):
    id = models.AutoField(primary_key=True)
    parent = models.ForeignKey('self', null=True, on_delete=models.CASCADE)
    name = models.TextField(db_index=True)
    date_created = models.DateTimeField('Дата создания', auto_now_add=True)

    class Meta:
        db_table = 'partners_madeinchinacategory'
        managed = False

    def __str__(self):
        return self.name


class MadeInChinaProduct(models.Model):
    id = models.CharField(max_length=20, primary_key=True, )
    name = models.CharField(max_length=1000)
    url = models.URLField(max_length=400, null=True)
    category = models.ForeignKey(MadeInChinaCategory, on_delete=models.CASCADE, null=True, default=None)
    category_string = models.CharField(max_length=200, null=True)
    date_created = models.DateTimeField('Дата создания', auto_now_add=True, null=True)
    video = models.URLField(max_length=400, null=True)
    product_images = models.JSONField(null=True)
    other_images = models.JSONField(null=True)
    prices = models.JSONField(null=True)
    moq = models.CharField(max_length=40, null=True)
    unit = models.CharField(max_length=20, null=True)
    product_info = models.JSONField(null=True)
    supplier_name = models.CharField(max_length=200, null=True)
    supplier_url = models.URLField(max_length=400, null=True)
    properties = models.JSONField(null=True)
    supplier_last_activity = models.DateTimeField(null=True)

    class Meta:
        db_table = 'partners_madeinchinaproduct'
        managed = False

    def __str__(self):
        return self.name
