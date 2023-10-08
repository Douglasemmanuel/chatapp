from django.urls import path

from . import consumers

websocket_urlpaterns = [
    path('chat/', consumers.ChatConsumer.as_asgi())
]
