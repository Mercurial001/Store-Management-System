from django.shortcuts import render, redirect
from .models import Product, ScannedProducts, SoldProducts, CashierDynamicProducts, SoldProduct, \
    SoldProductHub, ScannedProductHeader, SoldOutProduct, ProductType, Notification
from .forms import ProductForm, CreateUserForm, ScannedProductAddQuantityForm, ProductTypeForm, ChangeProductForm
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from .decorators import unauthenticated_user, admin_group_required
from django.contrib.auth.models import Group, User
from django.utils import timezone
import cv2
from django.http import StreamingHttpResponse, JsonResponse, HttpResponseRedirect
from django.views.decorators import gzip
from pyzbar.pyzbar import decode
import winsound
from django.db.models import Sum, Count
from datetime import datetime, timedelta
from django.contrib.humanize.templatetags.humanize import naturaltime
from datetime import date
from django.db.models import Q
from .decorators import unauthenticated_user
from django.contrib.auth.decorators import login_required


@login_required(login_url='login')
def index(request):
    users = User.objects.all()
    product_form = ProductForm()
    product_type_form = ProductTypeForm()
    products = CashierDynamicProducts.objects.filter(cashier=1)
    notifications = Notification.objects.filter(removed=False)
    barcodes = []
    for product in products:
        barcodes.append(product.barcode)

    # cashier = User.objects.get(username=username)
    scanned_products = ScannedProducts.objects.filter(cashier=1)
    product_list = []
    for products in scanned_products:
        for product in products.product.all():
            products_data = [
                {'name': product.name,
                 'scanned_quantity': product.scanned_quantity,
                 'price': (product.scanned_quantity * product.price)},
            ]
            product_list.append(products_data)

    if request.method == 'POST':
        if 'add-new-product-btn' in request.POST:
            add_product_form = ProductForm(request.POST, request.FILES)
            if add_product_form.is_valid():
                product = add_product_form.save(commit=False)
                if Product.objects.filter(name=product.name).exists():
                    messages.error(request, "Product with that name already exists")
                elif Product.objects.filter(barcode=product.barcode).exists():
                    messages.error(request, "Product with that barcode already exists")
                else:
                    messages.success(request, "Product Successfully Added!")
                    product.save()

                    # Let's Create a dynamic products for cashiers
                    for user in users:
                        cashier_product = CashierDynamicProducts.objects.create(
                            cashier=user,
                            name=product.name,
                            type=product.type,
                            barcode=product.barcode,
                            price=product.price,
                            expiry_date=product.expiry_date,
                            quantity=product.quantity,
                            scanned_quantity=0,
                            image=product.image,
                        )
                        cashier_product.save()
        elif 'add-new-product-type-btn' in request.POST:
            product_type_form = ProductTypeForm(request.POST, request.FILES)
            if product_type_form.is_valid():
                product_type = product_type_form.save(commit=False)
                product_type.save()

    return render(request, 'base.html', {
        'product_form': product_form,
        'users': users,
        'scanned_products': product_list,
        'barcodes': barcodes,
        'product_type_form': product_type_form,
        'notifications': notifications,
    })


@login_required(login_url='login')
def dashboard(request):
    default_date = date.today()
    users = User.objects.all()
    notifications = Notification.objects.filter(removed=False)
    thirty_days_ago = timezone.now() - timedelta(days=30)
    product_type = ProductType.objects.all()

    current_date = timezone.now()
    thirty_days_ago = current_date - timedelta(days=30)

    product_types = {}
    for product in product_type:
        types = product.product_type
        product_types[types] = []

    prod_types = [types for types, list in product_types.items()]

    expired_products = Product.objects.filter(expiry_date__lte=current_date, expiry_date__gte=thirty_days_ago)

    thirty_days_from_now = current_date + timedelta(days=30)

    upcoming_expiring_products = Product.objects.filter(expiry_date__gte=current_date,
                                                        expiry_date__lte=thirty_days_from_now)

    sold_products_objects = SoldProducts.objects.filter(date_sold_no_time__gte=thirty_days_ago)

    sold_products_date = {}
    for products in sold_products_objects:
        for product in products.product.all():
            product_date = products.date_sold_no_time
            if product_date not in sold_products_date:
                sold_products_date[product_date] = [product.sold_quantity]
            else:
                sold_products_date[product_date].append(product.sold_quantity)

    summed_sold_products_quantities = [sum(quantity_list) for product, quantity_list in sold_products_date.items()]
    product_sold_date = [product_date.strftime('%Y-%m-%d') for product_date, quantity_list in sold_products_date.items()]

    sold_products = SoldProduct.objects.filter(date_sold_no_time__gte=thirty_days_ago)

    sold_products_list = {}
    for products in sold_products:
        product = products.name
        if product not in sold_products_list:
            sold_products_list[product] = [products.sold_quantity]
        else:
            sold_products_list[product].append(products.sold_quantity)

    summed_products = {product: sum(quantity_list) for product, quantity_list in sold_products_list.items()}

    summed_products_quantities = [sum(quantity_list) for product, quantity_list in sold_products_list.items()]
    summed_products_products = [product for product, quantity_list in sold_products_list.items()]

    sold_products_profits = SoldProducts.objects.filter(date_sold_no_time__gte=thirty_days_ago)

    sold_products_profit_list = {}
    for products in sold_products_profits:
        product_date = products.date_sold_no_time
        if product_date not in sold_products_profit_list:
            sold_products_profit_list[product_date] = [products.total_price]
        else:
            sold_products_profit_list[product_date].append(products.total_price)

    summed_sold_product_profit = [sum(product_price) for product_date, product_price in sold_products_profit_list.items()]
    sold_product_profit_date = [product_date.strftime('%Y-%m-%d') for product_date, product_price in sold_products_profit_list.items()]

    # Filtration of graphs
    selected_month_sold_product = request.GET.get('selected-month')
    selected_type_sold_product = request.GET.get('type-filter')
    selected_cashier_sold_product = request.GET.get('cashier-branch-filter')

    sold_products_list_filtered = {}
    sold_products_date_filtered = {}
    sold_products_profit_filtered = {}

    if selected_month_sold_product or selected_cashier_sold_product or selected_type_sold_product:

        # Convert the selected date to a Python date object
        selected_date = datetime.strptime(selected_month_sold_product + '-01', '%Y-%m-%d').date()
        selected_year = selected_date.year
        selected_month = selected_date.month

        sold_products_filtered = SoldProduct.objects.filter(
            date_sold_no_time__month=selected_month,
            date_sold_no_time__year=selected_year,
            type__product_type=selected_type_sold_product,
            cashier__username=selected_cashier_sold_product,
        )

        for products in sold_products_filtered:
            product = products.name
            if product not in sold_products_list_filtered:
                sold_products_list_filtered[product] = [products.sold_quantity]
            else:
                sold_products_list_filtered[product].append(products.sold_quantity)

        sold_products_objects_filtered = SoldProducts.objects.filter(
            date_sold_no_time__month=selected_month,
            date_sold_no_time__year=selected_year,
            product__type__product_type=selected_type_sold_product,
            cashier__username=selected_cashier_sold_product,
        )

        for products in sold_products_objects_filtered:
            for product in products.product.all():
                product_date = products.date_sold_no_time
                if product_date not in sold_products_date_filtered:
                    sold_products_date_filtered[product_date] = [product.sold_quantity]
                else:
                    sold_products_date_filtered[product_date].append(product.sold_quantity)

        sold_products_profits = SoldProducts.objects.filter(
            date_sold_no_time__month=selected_month,
            date_sold_no_time__year=selected_year,
            product__type__product_type=selected_type_sold_product,
            cashier__username=selected_cashier_sold_product,
        )

        sold_products_profit_filtered = {}
        for products in sold_products_profits:
            product_date = products.date_sold_no_time
            for product in products.product.all():
                if product_date not in sold_products_profit_filtered:
                    sold_products_profit_filtered[product_date] = [product.price]
                else:
                    sold_products_profit_filtered[product_date].append(product.price)

    # Filtered Products Quantity
    summed_sold_products_quantities_filtered = [
        sum(quantity_list) for product, quantity_list in sold_products_date_filtered.items()
    ]
    product_sold_date_filtered = [
        product_date.strftime('%Y-%m-%d') for product_date, quantity_list in sold_products_date_filtered.items()
    ]
    # Filtered Product Sales
    summed_products_quantities_filtered = [
        sum(quantity_list) for product, quantity_list in sold_products_list_filtered.items()
    ]
    summed_products_products_filtered = [
        product for product, quantity_list in sold_products_list_filtered.items()
    ]
    # Filtered Daily Profits
    summed_sold_product_profit_filtered = [
        sum(product_price) for product_date, product_price in sold_products_profit_filtered.items()
    ]
    sold_product_profit_date_filtered = [
        product_date.strftime('%Y-%m-%d') for product_date, product_price in sold_products_profit_filtered.items()
    ]

    revenue_list = {}
    revenues = SoldProducts.objects.all()
    for revenue in revenues:
        rev = revenue.total_price
        if rev not in revenue_list:
            revenue_list[rev] = [rev]
        else:
            revenue_list[rev].append(rev)

    total_revenue = [sum(rev_array) for rev, rev_array in revenue_list.items()]
    total_revenue_sum = sum(total_revenue) - 23433

    # revenues = SoldProducts.objects.values('total_price')
    # total_revenue = revenues.aggregate(total_revenue=Sum('total_price'))['total_revenue']
    return render(request, 'dashboard.html', {
        'total_revenue': total_revenue,
        'total_revenue_sum': total_revenue_sum,
        'summed_products': summed_products,
        'summed_products_quantities': summed_products_quantities,
        'summed_products_products': summed_products_products,
        'sold_products_date': sold_products_date,
        # 'products_sold_dates': products_sold_dates,
        # 'products_counts': products_counts,
        # 'data': data,
        'sold_products_list': sold_products_list,
        'summed_sold_products_quantities': summed_sold_products_quantities,
        'product_sold_date': product_sold_date,
        'expired_products': expired_products,
        'upcoming_expiring_products': upcoming_expiring_products,
        'notifications': notifications,
        'default_date': default_date,
        'product_type': product_type,
        'product_types': prod_types,
        'users': users,
        # Sold Product Profit
        'summed_sold_product_profit': summed_sold_product_profit,
        'sold_product_profit_date': sold_product_profit_date,
        # Sold Product Filters
        'selected_month_sold_product': selected_month_sold_product,
        'selected_type_sold_product': selected_type_sold_product,
        'selected_cashier_sold_product': selected_cashier_sold_product,
        # Filtered Dashboard Data Sold Products
        'summed_products_quantities_filtered': summed_products_quantities_filtered,
        'summed_products_products_filtered': summed_products_products_filtered,
        # Filtered Dashboard Data Daily Sales
        'summed_sold_products_quantities_filtered': summed_sold_products_quantities_filtered,
        'product_sold_date_filtered': product_sold_date_filtered,
        # Filtered Dashboard Data Daily Profits
        'summed_sold_product_profit_filtered': summed_sold_product_profit_filtered,
        'sold_product_profit_date_filtered': sold_product_profit_date_filtered,
    })


@unauthenticated_user
def authentication(request):
    notifications = Notification.objects.filter(removed=False)
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect('homepage')
        else:
            messages.error(request, "Invalid Form Data")

    return render(request, 'login.html', {

    })


@unauthenticated_user
def register(request):
    notifications = Notification.objects.all()
    if request.user.is_authenticated:
        return redirect('homepage')
    else:
        form = CreateUserForm
        if request.method == 'POST':
            form = CreateUserForm(request.POST)
            if form.is_valid():
                user_created = form.save(commit=False)
                user_created.save()

                new_user = User.objects.get(username=user_created.username)

                # Create a ScannedProducts Objects to address the scalability concern
                cashier, created = ScannedProducts.objects.get_or_create(
                    cashier=new_user,
                    summed_product_price=0,
                )
                cashier.save()

                scanned_product_header, created = ScannedProductHeader.objects.get_or_create(
                    cashier=new_user,
                )
                scanned_product_header.save()
                # Let's Create a Product for the Registered Cashier so as not to tamper the original product's details
                products = Product.objects.all()
                for product in products:
                    dynamic_cashier_products = CashierDynamicProducts.objects.create(cashier=user_created,
                                                                                     name=product.name,
                                                                                     type=product.type,
                                                                                     barcode=product.barcode,
                                                                                     price=product.price,
                                                                                     expiry_date=product.expiry_date,
                                                                                     quantity=product.quantity,
                                                                                     scanned_quantity=0,
                                                                                     image=product.image,
                                                                                     )
                    dynamic_cashier_products.save()

                # group = Group.objects.get(name='users')
                # userForm.groups.add(group)

                messages.success(request, 'Account successfully created ' + user_created.username)
                return redirect('login')

    return render(request, 'register.html', {'form': form})


def logout_user(request):
    logout(request)
    return redirect('login')


barcode_data = ''


@login_required(login_url='login')
@gzip.gzip_page
def scan_barcodes(request, username):
    def generate():
        camera = cv2.VideoCapture(0)
        user = User.objects.get(username=username)
        scanned_product_list = ScannedProducts.objects.get(cashier=user)
        global barcode_data
        while True:
            # Capture a frame from the camera
            ret, frame = camera.read()

            if not ret:
                print("Failed to capture frame.")
                break
            else:
                _, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')
                # Read a frame from the webcam
                _, frame = camera.read()

                # Decode barcodes
                barcodes = decode(frame)

                tester = {}

                # Iterate over detected barcodes
                for barcode in barcodes:
                    # Extract barcode data
                    barcode_datas = barcode.data.decode('utf-8')
                    barcode_type = barcode.type
                    print(f"Found barcode: {barcode_datas}, Type: {barcode_type}")

                    x, y, w, h = barcode.rect
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    tester[barcode_datas] = barcode_type
                    # scanned_product_barcode = request.GET.get['video']
                    barcode_details = [data for data, type in tester.items()]
                    barcode_data = barcode_details[0]

                    if CashierDynamicProducts.objects.filter(cashier=user, barcode=barcode_data).exists():
                        scanned_product = CashierDynamicProducts.objects.get(barcode=barcode_data, cashier=user)
                        scanned_product_list.product.add(scanned_product)

                        scanned_product_list.summed_product_price += scanned_product.price
                        scanned_product_list.save()

                        scanned_product.scanned_quantity += 1
                        scanned_product.save()

                        # Create scanned header
                        scanned_product_header, created = ScannedProductHeader.objects.get_or_create(cashier=user)
                        scanned_product_header.name = scanned_product.name
                        scanned_product_header.barcode = scanned_product.barcode
                        scanned_product_header.expiry_date = scanned_product.expiry_date
                        scanned_product_header.price = scanned_product.price
                        scanned_product_header.save()
                        winsound.Beep(1500, 200)
                        return JsonResponse({'hey': 'hey'})
                    else:
                        winsound.Beep(100, 500)

    response = StreamingHttpResponse(generate(), content_type="multipart/x-mixed-replace;boundary=frame")
    return response


@login_required(login_url='login')
def scanning_products(request, username):
    notifications = Notification.objects.filter(removed=False)
    user = User.objects.get(username=username)
    scanned_products = ScannedProducts.objects.filter(cashier=user)
    products = CashierDynamicProducts.objects.filter(cashier=user)
    scanned_product_header, created = ScannedProductHeader.objects.get_or_create(cashier=user)
    scanned_product_header.save()
    testing = CashierDynamicProducts.objects.all()
    scanned_product_list = ScannedProducts.objects.get(cashier=user)

    barcodes = []
    for product in products:
        barcodes.append(product.barcode)

    add_quantity_form = ScannedProductAddQuantityForm()

    global barcode_data

    product_main = Product.objects.filter(quantity__lte=0)
    for product in product_main:
        sold_out_product = SoldOutProduct.objects.create(
            name=product.name,
            barcode=product.barcode,
            price=product.price,
            type=product.type,
        )

        notification = Notification.objects.create(
            title=f'Sold Out Product: {product.name}',
            message=f'This is to notify you that the product, "{product.name}" is now out of stock.'
        )
        notification.save()

        sold_out_product.save()
        product.delete()

    dynamic_products = CashierDynamicProducts.objects.filter(quantity__lte=0)
    for dynamic_product in dynamic_products:
        dynamic_product.delete()

    if barcode_data:
        barcode_data_copy = barcode_data
        barcode_data = ''

        if CashierDynamicProducts.objects.filter(cashier=user, barcode=barcode_data_copy).exists():
            scanned_product = CashierDynamicProducts.objects.get(barcode=barcode_data_copy, cashier=user)
            return JsonResponse({'success': f'Product: {scanned_product.barcode}'})

    if request.method == 'POST':
        barcode = request.POST.get('barcode')
        form = ScannedProductAddQuantityForm(request.POST)
        if form.is_valid():
            quantity_form = form.save(commit=False)
            if CashierDynamicProducts.objects.filter(cashier=user, barcode=barcode).exists():

                product = CashierDynamicProducts.objects.get(cashier=user, barcode=barcode)
                total_sum = ScannedProducts.objects.get(cashier=user)

                product_multiplied_price = product.scanned_quantity * product.price
                total_sum.summed_product_price -= product_multiplied_price
                total_sum.save()

                product.scanned_quantity = quantity_form.scanned_quantity
                product.save()

                total_sum = ScannedProducts.objects.get(cashier=user)
                total_sum.summed_product_price += (product.price * quantity_form.scanned_quantity)
                total_sum.save()

    return render(request, 'scanned_product.html', {
        'scanned_products': scanned_products,
        'products': products,
        'user': user,
        'scanned_product_header': scanned_product_header,
        'add_quantity_form': add_quantity_form,
        'testing': testing,
        'barcode_data': barcode_data,
        'barcodes': barcodes,
        'notifications': notifications,
    })


@login_required(login_url='login')
def update_scanned_products(request, username):
    cashier = User.objects.get(username=username)
    scanned_products = ScannedProducts.objects.filter(cashier=cashier)
    product_list = []

    for products in scanned_products:
        for product in products.product.all():
            product_data = {
                'name': product.name,
                'scanned_quantity': product.scanned_quantity,
                'price': product.scanned_quantity * product.price,
                'barcode': product.barcode,
                'id': product.id,
            }
            product_list.append(product_data)

    return JsonResponse({'products': product_list})


@login_required(login_url='login')
def add_quantity_product(request, username, barcode):

    user = User.objects.get(username=username)

    scanned_product_list = ScannedProducts.objects.get(cashier=user)

    # scanned_product_barcode = request.GET.get['video']
    scanned_product = CashierDynamicProducts.objects.get(barcode=barcode, cashier=user)
    # scanned_product_list.product.add(scanned_product)

    scanned_product_list.summed_product_price += scanned_product.price
    scanned_product_list.save()

    scanned_product.scanned_quantity += 1
    # Newly Added Somehow I wanted to test this out, to make the quantities change in real time. 1/15/2024
    scanned_product.quantity -= 1
    scanned_product.save()

    referring_url = request.META.get('HTTP_REFERER')

    if referring_url:
        # Redirect back to the referring page
        return HttpResponseRedirect(referring_url)
    else:
        # If there's no referring URL, redirect to a default page
        return redirect('scanned-products', username=user.username)


@login_required(login_url='login')
def subtract_quantity_product(request, username, barcode):
    user = User.objects.get(username=username)

    scanned_product_list = ScannedProducts.objects.get(cashier=user)

    # scanned_product_barcode = request.GET.get['video']
    scanned_product = CashierDynamicProducts.objects.get(barcode=barcode, cashier=user)
    # scanned_product_list.product.add(scanned_product)

    scanned_product_list.summed_product_price -= scanned_product.price
    scanned_product_list.save()

    scanned_product.scanned_quantity -= 1
    # Newly Added Somehow I wanted to test this out, to make the quantities change in real time. 1/25/2024
    # It works like heaven
    scanned_product.quantity += 1
    scanned_product.save()

    referring_url = request.META.get('HTTP_REFERER')

    if referring_url:
        # Redirect back to the referring page
        return HttpResponseRedirect(referring_url)
    else:
        # If there's no referring URL, redirect to a default page
        return redirect('scanned-products', username=user.username)


@login_required(login_url='login')
def remove_scanned_product(request, username, barcode):
    user = User.objects.get(username=username)

    scanned_product_list = ScannedProducts.objects.get(cashier=user)

    # scanned_product_barcode = request.GET.get['video']
    scanned_product = CashierDynamicProducts.objects.get(barcode=barcode, cashier=user)
    scanned_product.quantity += scanned_product.scanned_quantity

    main_products = Product.objects.filter(name=scanned_product.name)
    for main_product in main_products:
        main_product.quantity = scanned_product.quantity
        main_product.save()

    dynamic_products = CashierDynamicProducts.objects.filter(name=scanned_product.name)
    for dynamic_product in dynamic_products:
        dynamic_product.quantity = scanned_product.quantity
        dynamic_product.save()

    scanned_product_list.product.remove(scanned_product)

    scanned_product_list.summed_product_price -= (scanned_product.price * scanned_product.scanned_quantity)
    scanned_product_list.save()

    scanned_product.scanned_quantity = 0
    scanned_product.save()

    referring_url = request.META.get('HTTP_REFERER')

    if referring_url:
        # Redirect back to the referring page
        return HttpResponseRedirect(referring_url)
    else:
        # If there's no referring URL, redirect to a default page
        return redirect('scanned-products', username=user.username)


@login_required(login_url='login')
def sell_scanned_products(request, username):
    user = User.objects.get(username=username)
    scanned_products = ScannedProducts.objects.filter(cashier=user)
    # Let's retrieve the models that we need for this operation
    product_types = ProductType.objects.all()
    products = CashierDynamicProducts.objects.filter(cashier=user)
    cashier = ScannedProducts.objects.get(cashier=user)
    scanned_products_header = ScannedProductHeader.objects.get(cashier=user)

    for product in cashier.product.all():
        # Let's create a SoldProduct object from products that are sold right after they are scanned.
        sold_product = SoldProduct.objects.create(
            cashier=user,
            name=product.name,
            type=product.type,
            barcode=product.barcode,
            price=product.price,
            expiry_date=product.expiry_date,
            sold_quantity=product.scanned_quantity,
            date_sold=timezone.now(),
            date_sold_no_time=timezone.now(),
        )
        sold_product.save()

        # Let's create a replica of the product to avoid the sold products being erased when the original product
        # stock is depleted

        product_sold, created = SoldProductHub.objects.get_or_create(cashier=user)
        product_sold.product.add(sold_product)
        product_sold.save()

        # The scanned quantity of the scanned product to revert it to its original state.
        product.scanned_quantity = 0
        product.save()

    # Create and derive the products that are temporarily stored in this hub
    sold_products_hub = SoldProductHub.objects.get(cashier=user)
    product_sold = [product for product in sold_products_hub.product.all()]

    cash = request.POST.get('cash')

    # Let's create a SoldProducts object
    sold_products = SoldProducts.objects.create(
        cashier=user,
        total_price=cashier.summed_product_price,
        date_sold=timezone.now(),
        date_sold_no_time=timezone.now(),
        cash=int(cash),
        change=(int(cash) - cashier.summed_product_price),
    )
    sold_products.product.add(*product_sold)
    sold_products.save()

    # Sets the scanned product header to default
    scanned_products_header.name = None
    scanned_products_header.barcode = None
    scanned_products_header.price = None
    scanned_products_header.expiry_date = None
    scanned_products_header.change = sold_products.change
    scanned_products_header.save()

    # remove the products in the ScannedProducts Hub
    cashier.summed_product_price = 0
    product = [product for product in products]
    cashier.product.remove(*product)
    cashier.save()

    product_main = Product.objects.filter(quantity__lte=0)
    for product in product_main:
        sold_out_product = SoldOutProduct.objects.create(
            name=product.name,
            barcode=product.barcode,
            price=product.price,
            type=product.type,
        )

        notification = Notification.objects.create(
            title=f'Sold Out Product: {product.name}',
            message=f'This is to notify you that the product, "{product.name}" is now out of stock.'
        )

        notification.save()

        sold_out_product.save()
        product.delete()

    dynamic_products = CashierDynamicProducts.objects.filter(quantity__lte=0)
    for dynamic_product in dynamic_products:
        dynamic_product.delete()

    products = CashierDynamicProducts.objects.filter(cashier=user)
    product_types_list = {}
    for producto in products:
        product_type = producto.type
        if product_type not in product_types_list:
            product_types_list[product_type] = [producto]
        else:
            product_types_list[product_type].append(producto)

    # Add the SoldProduct objects from the SoldProductHub model
    sold_products_hub.product.remove(*product_sold)
    sold_products_hub.save()

    return render(request, 'products_list.html', {
        'scanned_products_header': scanned_products_header,
        'products': products,
        'scanned_products': scanned_products,
        'product_types': product_types,
        'product_types_list': product_types_list,
    })


@login_required(login_url='login')
def add_dynamic_products(request, username):
    user = User.objects.get(username=username)
    products = Product.objects.all()
    for product in products:
        dynamic_cashier_products = CashierDynamicProducts.objects.create(
            cashier=user,
            name=product.name,
            barcode=product.barcode,
            price=product.price,
            expiry_date=product.expiry_date,
            quantity=product.quantity,
            scanned_quantity=product.scanned_quantity,
        )
        dynamic_cashier_products.save()
    return redirect('homepage')


@login_required(login_url='login')
def products_sold(request):
    notifications = Notification.objects.filter(removed=False)
    sold_products = SoldProducts.objects.all().order_by('-date_sold')
    return render(request, 'sold_products.html', {
        'sold_products': sold_products,
        'notifications': notifications,
    })


@login_required(login_url='login')
def expired_products(request):
    notifications = Notification.objects.filter(removed=False)
    current_date = timezone.now()
    thirty_days_ago = current_date - timedelta(days=30)

    expired_product = Product.objects.filter(expiry_date__lte=current_date, expiry_date__gte=thirty_days_ago)

    thirty_days_from_now = current_date + timedelta(days=30)

    upcoming_expiring_products = Product.objects.filter(expiry_date__gte=current_date,
                                                        expiry_date__lte=thirty_days_from_now)

    return render(request, 'expiration.html', {
        'expired_products': expired_product,
        'upcoming_expiring_products': upcoming_expiring_products,
        'notifications': notifications,
    })


@login_required(login_url='login')
def reports(request):
    notifications = Notification.objects.filter(removed=False)
    return render(request, 'reports.html', {
        'notifications': notifications,
    })


@login_required(login_url='login')
def sold_out_products(request):
    notifications = Notification.objects.filter(removed=False)
    products = SoldOutProduct.objects.all()
    return render(request, 'sold_out_products.html', {
        'products': products,
        'notifications': notifications,
    })


@login_required(login_url='login')
def select_products_sell(request, username):
    notifications = Notification.objects.filter(removed=False)
    cashier = User.objects.get(username=username)
    products = CashierDynamicProducts.objects.filter(cashier=cashier)
    scanned_products = ScannedProducts.objects.filter(cashier=cashier)
    scanned_products_header = ScannedProductHeader.objects.get(cashier=cashier)
    product_types = ProductType.objects.all()
    default_quantity = 1
    default_cash = 0

    scanned_product = ScannedProducts.objects.get(cashier=cashier)
    total_price_scanned_products = scanned_product.summed_product_price

    if request.method == 'POST':
        selected_products = request.POST.getlist('selectedProducts')
        selected_products_quantity = request.POST.getlist(f'product-quantity')
        scanned_product_list = ScannedProducts.objects.get(cashier=cashier)
        scanned_product_list.product.add(*selected_products)
        filtered_quantity = [value for value in selected_products_quantity if value]

        for id, quantity in zip(selected_products, filtered_quantity):
            product = CashierDynamicProducts.objects.get(id=id)
            product.scanned_quantity += int(quantity)
            scanned_product_list.summed_product_price += product.price * int(quantity)
            product.quantity -= int(quantity)
            product.save()

            main_products = Product.objects.filter(name=product.name)
            for main_product in main_products:
                main_product.quantity = product.quantity
                main_product.save()

            dynamic_products = CashierDynamicProducts.objects.filter(name=product.name)
            for dynamic_product in dynamic_products:
                dynamic_product.quantity = product.quantity
                dynamic_product.save()

        scanned_product_list.save()

    product_types_list = {}
    for producto in products:
        product_type = producto.type
        if product_type not in product_types_list:
            product_types_list[product_type] = [producto]
        else:
            product_types_list[product_type].append(producto)

    scanned_length = ScannedProducts.objects.filter(cashier=cashier).annotate(scanned_length=Count('product'))
    scanned_sum = scanned_length.aggregate(length_sum=Sum('scanned_length'))['length_sum']

    return render(request, 'select_sell_products.html', {
        'products': products,
        'default_quantity': default_quantity,
        'scanned_products': scanned_products,
        'product_types_list': product_types_list,
        'product_types': product_types,
        'notifications': notifications,
        'scanned_sum': scanned_sum,
        'default_cash': default_cash,
        'total_price_scanned_products': total_price_scanned_products,
        'scanned_products_header': scanned_products_header,
    })


@login_required(login_url='login')
def expired_products_json(request):
    product_main = Product.objects.filter(quantity__lte=0)
    running_low_products = Product.objects.filter(quantity__lte=4)
    for product in product_main:
        sold_out_product = SoldOutProduct.objects.create(
            name=product.name,
            barcode=product.barcode,
            price=product.price,
            type=product.type,
        )

        sold_out_product.save()

    for product in running_low_products:
        if product.quantity == 1:
            quantity_dynamic_word = 'quantity'
        else:
            quantity_dynamic_word = 'quantities'
        depletion_notification, created = Notification.objects.get_or_create(
            title=f'Product Nearing Depletion: {product.name}',
            message=f'This is to notify you that the product, "{product.name}" has only {product.quantity} {quantity_dynamic_word} left in stock.',
            identifier=f'Product Nearing Depletion Identifier: {product.name}-{product.id}-{product.quantity}-{product.barcode}'
        )
        depletion_notification.save()

    current_date = timezone.now()
    thirty_days_ago = current_date - timedelta(days=30)
    now = timezone.now().date()
    # Format the date and time into the desired numeric representation

    expired_product_list = []
    expired_product = Product.objects.filter(expiry_date__lte=current_date, expiry_date__gte=thirty_days_ago)
    for product in expired_product:

        expired_notifications, created = Notification.objects.get_or_create(
            title=f'Expired Product: {product.name}',
            message=f'This is to notify you that the product, "{product.name}" is pass the expiration date.',
            identifier=f'Expired Products Identifier: {product.name}-{product.id}'
        )

        expired_product_data = {
            'name': product.name,
            'id': product.id,
            'expiry_date': product.expiry_date,
        }
        expired_notifications.save()

        expired_product_list.append(expired_product_data)

    thirty_days_from_now = current_date + timedelta(days=30)

    upcoming_expiring_products_list = []
    upcoming_expiring_products = Product.objects.filter(expiry_date__gte=current_date,
                                                        expiry_date__lte=thirty_days_from_now)

    for product in upcoming_expiring_products:
        difference = product.expiry_date - now
        days_until_expiry = difference.days
        if days_until_expiry == 1:
            days_label = 'day'
        else:
            days_label = 'days'
        upcoming_expiration, created = Notification.objects.get_or_create(
            title=f'Product Nearing Expiration: {product.name}',
            message=f'This is to notify you that the product, "{product.name}", '
                    f'will be expired {days_until_expiry} {days_label} from now.',
            identifier=f' Upcoming Expirations Identifier: {product.name}-{product.id}'
        )
        expiring_product_data = {
            'name': product.name,
            'id': product.id,
            'expiry_date': product.expiry_date,
        }
        upcoming_expiring_products_list.append(expiring_product_data)
        upcoming_expiration.save()

    notifications = Notification.objects.filter(removed=False)
    notification_list = []

    unseen_notifications = Notification.objects.filter(is_seen=False).annotate(unseen_notifications=Count('is_seen'))
    unseen_sum = unseen_notifications.aggregate(unseen=Sum('unseen_notifications'))['unseen']

    for notification in notifications:
        notification_data = {
            'title': notification.title,
            'message': notification.message,
            'time': naturaltime(notification.date_time),
            'id': notification.id,
            'unseen': unseen_sum
        }
        notification_list.append(notification_data)

    return JsonResponse({
        'expired_products': expired_product_list,
        'expiring_products': upcoming_expiring_products_list,
        'notification': notification_list,
    })


@login_required(login_url='login')
def remove_notification(request, title, id):
    notification = Notification.objects.get(title=title, id=id)
    notification.removed = True
    notification.save()

    # Assuming you want to send a JSON response to confirm the removal
    return JsonResponse({'message': 'Notification removed successfully'})


@login_required(login_url='login')
def seen_notifications(request):
    try:
        notifications = Notification.objects.all()
        for notification in notifications:
            notification.is_seen = True
            notification.save()

        # Return a success response
        return JsonResponse({'status': 'success'})

    except ValueError as e:
        # Print the error for debugging purposes
        print('Error marking notifications as seen:', str(e))

        # Return an error response
        return JsonResponse({'status': 'error', 'message': str(e)})


@login_required(login_url='login')
def clear_scanned_header_change(request, username):
    cashier = User.objects.get(username=username)
    scanned_products_header = ScannedProductHeader.objects.get(cashier=cashier)

    scanned_products_header.change = None
    scanned_products_header.save()

    return render(request, 'clear_change.html', {
        'scanned_products_header': scanned_products_header,
    })


@login_required(login_url='login')
def product_info(request, id):
    product = Product.objects.get(id=id)
    product_form = ChangeProductForm(instance=product)
    if request.method == 'POST':
        form = ChangeProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            product_data = form.save(commit=False)
            dynamic_products = CashierDynamicProducts.objects.filter(Q(name=product_data.name) |
                                                                     Q(barcode=product_data.barcode))
            for dynamic_product in dynamic_products:
                dynamic_product.name = product_data.name
                dynamic_product.type = product_data.type
                dynamic_product.barcode = product_data.barcode
                dynamic_product.price = product_data.price
                dynamic_product.expiry_date = product_data.expiry_date
                dynamic_product.quantity = product_data.quantity
                dynamic_product.image = product_data.image
                dynamic_product.save()
            product_data.save()
            return redirect('product-info', id=product.id)

    return render(request, 'product_profile.html', {
        'product': product,
        'product_form': product_form,
    })


@login_required(login_url='login')
def products(request):
    notifications = Notification.objects.filter(removed=False)
    products = Product.objects.all()
    product_types_list = {}
    for producto in products:
        product_type = producto.type
        if product_type not in product_types_list:
            product_types_list[product_type] = [producto]
        else:
            product_types_list[product_type].append(producto)
    return render(request, 'products.html', {
        'product_types_list': product_types_list,
        'notifications': notifications,
    })

