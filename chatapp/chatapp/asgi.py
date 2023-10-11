"""
ASGI config for chatapp project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/asgi/
"""

import os
import chat.routing
from django.core.asgi import get_asgi_application
# from chann
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django_channels_jwt_auth_middleware.auth import JWTAuthMiddlewareStack
# from django.chatapp.asgi import get_asgi_application
# from django.core.asgi
# from django.ch

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chatapp.settings')

django_asgi_app = get_asgi_application()
application =  ProtocolTypeRouter({
    'http':django_asgi_app,
    'websocket': AllowedHostsOriginValidator(
        JWTAuthMiddlewareStack(
            URLRouter(chat.routing.websocket_urlpaterns)
        )
    )
})
