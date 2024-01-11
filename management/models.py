from django.db import models
from django.contrib.auth.models import User


class ProductType(models.Model):
    product_type = models.CharField(max_length=255)
    image = models.ImageField(null=True, blank=True, upload_to="images/")

    def __str__(self):
        return self.product_type


class Product(models.Model):
    type = models.ForeignKey(ProductType, on_delete=models.PROTECT)
    name = models.CharField(max_length=255)
    barcode = models.CharField(max_length=255)
    price = models.IntegerField()
    expiry_date = models.DateField()
    quantity = models.IntegerField()
    scanned_quantity = models.IntegerField(default=1)
    image = models.ImageField(null=True, blank=True, upload_to="images/")

    def __str__(self):
        return self.name

    def multiply(self):
        return self.scanned_quantity * self.price


class CashierDynamicProducts(models.Model):
    cashier = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    type = models.ForeignKey(ProductType, on_delete=models.PROTECT)
    barcode = models.CharField(max_length=255)
    price = models.IntegerField()
    expiry_date = models.DateField()
    quantity = models.IntegerField()
    scanned_quantity = models.IntegerField(default=1)
    image = models.ImageField(null=True, blank=True, upload_to="images/")

    def __str__(self):
        return self.name

    def multiply(self):
        return self.scanned_quantity * self.price

    @classmethod
    def total_price(cls):
        # Calculate the total price by summing the product of quantity and price for all products
        return cls.objects.aggregate(total_price=models.Sum(models.F('scanned_quantity') * models.F('price')))['total_price'] or 0


class ScannedProductHeader(models.Model):
    cashier = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=255, blank=True, null=True)
    barcode = models.CharField(max_length=255, blank=True, null=True)
    price = models.IntegerField(blank=True, null=True)
    expiry_date = models.DateField(blank=True, null=True)
    change = models.IntegerField(null=True)


class ScannedProducts(models.Model):
    cashier = models.ForeignKey(User, on_delete=models.CASCADE)
    summed_product_price = models.IntegerField(null=True, blank=True)
    product = models.ManyToManyField(CashierDynamicProducts, blank=True)


class SoldProduct(models.Model):
    cashier = models.ForeignKey(User, on_delete=models.PROTECT)
    type = models.ForeignKey(ProductType, on_delete=models.PROTECT)
    name = models.CharField(max_length=255)
    barcode = models.CharField(max_length=255)
    price = models.IntegerField()
    expiry_date = models.DateField()
    sold_quantity = models.IntegerField()
    date_sold = models.DateTimeField(null=True)
    date_sold_no_time = models.DateField(null=True)

    def __str__(self):
        return self.name

    def multiply(self):
        return self.sold_quantity * self.price


class SoldProductHub(models.Model):
    cashier = models.ForeignKey(User, on_delete=models.PROTECT)
    product = models.ManyToManyField(SoldProduct)


class SoldProducts(models.Model):
    cashier = models.ForeignKey(User, on_delete=models.PROTECT)
    product = models.ManyToManyField(SoldProduct)
    # product = models.ManyToManyField(SoldProduct)
    total_price = models.IntegerField()
    date_sold = models.DateTimeField()
    date_sold_no_time = models.DateField()
    cash = models.IntegerField(null=True)
    change = models.IntegerField(null=True)


class SoldOutProduct(models.Model):
    name = models.CharField(max_length=255)
    type = models.ForeignKey(ProductType, on_delete=models.PROTECT)
    barcode = models.CharField(max_length=255)
    date_sold_out = models.DateField(auto_now_add=True)
    date_sold_out_time = models.DateTimeField(auto_now_add=True)
    price = models.IntegerField()


class Notification(models.Model):
    title = models.CharField(max_length=255)
    message = models.CharField(max_length=400)
    is_seen = models.BooleanField(default=False, null=True, blank=True)
    removed = models.BooleanField(default=False, null=True, blank=True)
    date = models.DateField(auto_now_add=True)
    date_time = models.DateTimeField(auto_now_add=True)
    identifier = models.CharField(max_length=500)

    class Meta:
        ordering = ['-date_time']
