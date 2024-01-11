from django.contrib import admin
from .models import Product
from .models import ScannedProducts
from .models import SoldProducts
from .models import CashierDynamicProducts
from .models import SoldProduct
from .models import SoldProductHub
from .models import ScannedProductHeader
from .models import SoldOutProduct
from .models import ProductType
from .models import Notification


class NotificationAdmin(admin.ModelAdmin):
    list_display = ('title', )


class ProductTypeAdmin(admin.ModelAdmin):
    list_display = ('product_type',)


class SoldOutProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'date_sold_out')


class ScannedProductHeaderAdmin(admin.ModelAdmin):
    list_display = ('cashier', 'name', 'barcode')

    def has_add_permission(self, request):
        # Disable the ability to add new FineRate objects
        return False

    def has_delete_permission(self, request, obj=None):
        # Disable the ability to delete FineRate objects
        return False


class SoldProductHubAdmin(admin.ModelAdmin):
    list_display = ('cashier', )


class SoldProductsAdmin(admin.ModelAdmin):
    list_display = ('cashier', 'total_price', 'date_sold', 'date_sold_no_time')


class SoldProductAdmin(admin.ModelAdmin):
    list_display = ('cashier', 'name', 'sold_quantity')


class CashierDynamicProductsAdmin(admin.ModelAdmin):
    list_display = ('cashier', 'name')


class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'expiry_date', 'barcode')


class ScannedProductsAdmin(admin.ModelAdmin):
    list_display = ('cashier',)


admin.site.register(Notification, NotificationAdmin)
admin.site.register(ProductType, ProductTypeAdmin)
admin.site.register(SoldOutProduct, SoldOutProductAdmin)
admin.site.register(ScannedProductHeader, ScannedProductHeaderAdmin)
admin.site.register(SoldProductHub, SoldProductHubAdmin)
admin.site.register(SoldProducts, SoldProductsAdmin)
admin.site.register(SoldProduct, SoldProductAdmin)
admin.site.register(CashierDynamicProducts, CashierDynamicProductsAdmin)
admin.site.register(ScannedProducts, ScannedProductsAdmin)
admin.site.register(Product, ProductAdmin)

