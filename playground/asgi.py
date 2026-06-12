import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
import sessions_app.routing

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "playground.settings")

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        URLRouter(sessions_app.routing.websocket_urlpatterns)
    ),
})
