"""ASGI entry point: normal pages over HTTP, live chat over WebSocket.

Run with:  python -m uvicorn config.asgi:application --port 8000   (start.bat does this)"""
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

from django.conf import settings  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402

django_app = get_asgi_application()  # sets Django up before anything imports models

from channels.auth import AuthMiddlewareStack  # noqa: E402
from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import AllowedHostsOriginValidator  # noqa: E402

from gym.routing import websocket_urlpatterns  # noqa: E402

if settings.DEBUG:  # runserver used to serve /static/ in development; under uvicorn this does the same
    from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
    django_app = ASGIStaticFilesHandler(django_app)

application = ProtocolTypeRouter({
    "http": django_app,
    # the Origin check is the WebSocket equivalent of CSRF protection: other sites cannot open a socket as our member
    "websocket": AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter(websocket_urlpatterns))),
})
