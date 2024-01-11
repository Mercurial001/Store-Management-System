from channels.generic.websocket import AsyncWebsocketConsumer
import cv2
from .models import ScannedProducts, CashierDynamicProducts, ScannedProductHeader
import winsound
from django.contrib.auth.models import User
from pyzbar.pyzbar import decode


class YourConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()

    async def disconnect(self, close_code):
        pass

    async def receive(self, text_data):
        # Handle incoming messages if needed
        pass

    async def scan_barcodes(self, username):
        camera = cv2.VideoCapture(0)
        user = User.objects.get(username=username)
        scanned_product_list = ScannedProducts.objects.get(cashier=user)
        barcode_data = ''
        while True:
            ret, frame = camera.read()

            if not ret:
                print("Failed to capture frame.")
                break
            else:
                _, buffer = cv2.imencode('.jpg', frame)
                frame = buffer.tobytes()

                await self.send(text_data=frame)

                _, frame = camera.read()

                barcodes = decode(frame)
                tester = {}

                for barcode in barcodes:
                    barcode_data = barcode.data.decode('utf-8')
                    barcode_type = barcode.type
                    print(f"Found barcode: {barcode_data}, Type: {barcode_type}")

                    x, y, w, h = barcode.rect
                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    tester[barcode_data] = barcode_type
                    barcode_details = [data for data, type in tester.items()]
                    barcode_data = barcode_details[0]

                    if CashierDynamicProducts.objects.filter(cashier=user, barcode=barcode_data).exists():
                        scanned_product = CashierDynamicProducts.objects.get(barcode=barcode_data, cashier=user)
                        scanned_product_list.product.add(scanned_product)
                        scanned_product_list.summed_product_price += scanned_product.price
                        scanned_product_list.save()
                        scanned_product.scanned_quantity += 1
                        scanned_product.save()

                        scanned_product_header, created = ScannedProductHeader.objects.get_or_create(cashier=user)
                        scanned_product_header.name = scanned_product.name
                        scanned_product_header.barcode = scanned_product.barcode
                        scanned_product_header.expiry_date = scanned_product.expiry_date
                        scanned_product_header.price = scanned_product.price
                        scanned_product_header.save()

                        message = {'success': 'Some message'}
                        await self.send_json_message(message)
                    else:
                        message = {'error': 'Some message'}
                        await self.send_json_message(message)


# import json
# from channels.generic.websocket import WebsocketConsumer
#
#
# class ScanConsumer(WebsocketConsumer):
#     def connect(self):
#         self.accept()
#
#         self.send(text_data=json.dumps({
#             'type': 'connected',
#             'message': 'You Are Connected',
#         }))
