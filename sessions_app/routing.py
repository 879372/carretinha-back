from django.urls import re_path
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/session/(?P<public_token>[^/]+)/$", consumers.SessionConsumer.as_asgi()),
]
