"""Store_Management URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from management import views
from Store_Management import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='homepage'),
    path('login/', views.authentication, name='login'),
    path('logout/', views.logout_user, name='logout'),
    path('register/', views.register, name='register'),
    path('scanned-products/<str:username>/', views.scanning_products, name='scanned-products'),
    path('function/sell-products/<str:username>/', views.sell_scanned_products, name='sell-scanned-products'),
    path('function/add-dynamic-products/<str:username>/', views.add_dynamic_products, name='add-product-cashier'),
    path('scan/<str:username>/', views.scan_barcodes, name='scanning'),
    path('remove-scanned-product/<str:username>/<str:barcode>/', views.remove_scanned_product, name='remove-product'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('reports/', views.reports, name='reports'),
    path('products/expired/', views.expired_products, name='expiration'),
    path('products/sold-out/', views.sold_out_products, name='sold-out-products'),
    path('products/sold/', views.products_sold, name='sold-products'),
    path('products/select/<str:username>/', views.select_products_sell, name='select-sell'),
    path('products/select/cashier/<str:username>/', views.select_products_sell_cashier_group,
         name='select-sell-cashier'),
    path('test/<str:username>', views.update_scanned_products, name='test-update'),
    path('expired_products/', views.expired_products_json, name='expired-products-json'),
    path('delete-notification/<str:title>/<int:id>/', views.remove_notification, name='delete-notification'),
    path('seen-notifications/', views.seen_notifications, name='seen-notifications'),
    path('product/<int:id>/', views.product_info, name='product-info'),
    path('products/', views.products, name='products'),
    path('htmx/clear-change/<str:username>/', views.clear_scanned_header_change, name='htmx-clear-change'),
    path('add-quantity-htmx/<str:username>/<str:barcode>/', views.add_quantity_product,
         name='add-quantity'),
    path('subtract-quantity-htmx/<str:username>/<str:barcode>/', views.subtract_quantity_product,
         name='subtract-quantity'),
    path('registration/', views.registration_validation, name='registration-validation'),
    path('registrants-validation/', views.validation_registrants, name='registrant-validation'),
    path('confirm_registration/<str:username>/', views.confirm_registration, name='confirm-registration')
    # path('htmx/sell/<str:username>/', views.tester, name='test'),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# path('date-assign/', views.date_assign, name='assign'),
