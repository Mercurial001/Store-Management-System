"""
ASGI config for Store_Management project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.2/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
from management import routing
import management

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Store_Management.settings')


application = ProtocolTypeRouter({
    'websocket': AuthMiddlewareStack(
        URLRouter(
            management.routing.websocket_urlpatterns
        )
    ),
})
