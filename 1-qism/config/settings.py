import os
import secrets
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


def _secret_key():
    """DJANGO_SECRET_KEY from env, otherwise a random key persisted in .secret_key (never committed)."""
    env = os.environ.get("DJANGO_SECRET_KEY")
    if env:
        return env
    f = BASE_DIR / ".secret_key"
    if not f.exists():
        f.write_text(secrets.token_urlsafe(64))
    return f.read_text().strip()


SECRET_KEY = _secret_key()
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [h.strip() for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if h.strip()]
if os.environ.get("RENDER_EXTERNAL_HOSTNAME"):  # Render.com sets this automatically
    ALLOWED_HOSTS.append(os.environ["RENDER_EXTERNAL_HOSTNAME"])
CSRF_TRUSTED_ORIGINS = [o.strip() for o in os.environ.get("DJANGO_CSRF_ORIGINS", "").split(",") if o.strip()]
if os.environ.get("RENDER_EXTERNAL_URL"):
    CSRF_TRUSTED_ORIGINS.append(os.environ["RENDER_EXTERNAL_URL"])

INSTALLED_APPS = [
    "gym",  # first, so its admin/base_site.html (the branded admin look) wins over Django's default template
    "gym.admin_apps.GymAdminConfig", "django.contrib.auth", "django.contrib.contenttypes",
    "django.contrib.sessions", "django.contrib.messages", "django.contrib.staticfiles",
]
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "gym.middleware.LangMiddleware",
    "gym.middleware.StaffAreaMiddleware",
    "gym.middleware.CspMiddleware",
]
try:  # whitenoise serves static files in production; optional so local development needs only Django
    import whitenoise  # noqa: F401
    MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")
    STORAGES = {"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage" if not DEBUG
                                else "django.contrib.staticfiles.storage.StaticFilesStorage"}}
except ImportError:
    pass

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"
# Live chat. The in-memory layer works for one server process (start.bat, a single Render instance). With several
# processes set REDIS_URL and install channels-redis, so messages reach sockets held by other processes.
if os.environ.get("REDIS_URL"):
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels_redis.core.RedisChannelLayer", "CONFIG": {"hosts": [os.environ["REDIS_URL"]]}}}
else:
    CHANNEL_LAYERS = {"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}
TEMPLATES = [{
    # In development the template cache is off: under uvicorn (unlike runserver) nothing would otherwise reload edited templates.
    "BACKEND": "django.template.backends.django.DjangoTemplates", "DIRS": [], "APP_DIRS": not DEBUG,
    "OPTIONS": {"context_processors": [
        "django.template.context_processors.request", "django.contrib.auth.context_processors.auth",
        "django.contrib.messages.context_processors.messages", "gym.context.gym"],
        **({"loaders": ["django.template.loaders.filesystem.Loader", "django.template.loaders.app_directories.Loader"]} if DEBUG else {})},
}]

DATABASES = {"default": {"ENGINE": "django.db.backends.sqlite3", "NAME": Path(os.environ.get("FZ_DB", BASE_DIR / "db.sqlite3"))}}
if os.environ.get("DATABASE_URL"):  # PostgreSQL etc. on the hosting platform
    import dj_database_url
    DATABASES["default"] = dj_database_url.parse(os.environ["DATABASE_URL"], conn_max_age=600)

AUTH_USER_MODEL = "gym.User"
AUTH_PASSWORD_VALIDATORS = []  # the forms enforce their own 6-128 character rule
LANGUAGE_CODE = "uz"
LOCALE_PATHS = [BASE_DIR / "locale"]  # fills gaps in Django's Uzbek admin translation; rebuild with `manage.py build_locale`
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
LOGIN_URL = "/login/"

# cookies / security
SECURE = os.environ.get("FZ_SECURE_COOKIE", "0") == "1" or bool(os.environ.get("RENDER"))
SESSION_COOKIE_SAMESITE = "Lax"  # Lax so that following a link to the site keeps you signed in; POSTs stay CSRF-protected
CSRF_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = SECURE
SESSION_COOKIE_AGE = 7 * 86400
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"
if SECURE and not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SSL_REDIRECT", "1") == "1"
    SECURE_HSTS_SECONDS = 31536000

# app settings
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "").strip()
# Demo "Payme/Click/Uzum" buttons mark a payment as paid without any money moving. They exist only for development (DEBUG on) unless forced.
ALLOW_DEMO_PAYMENTS = os.environ.get("FZ_ALLOW_DEMO", "1" if DEBUG else "0") == "1"

# uploaded lesson videos live outside the static folder and are only streamed through a view that checks VIP access
MEDIA_ROOT = Path(os.environ.get("FZ_MEDIA_DIR", BASE_DIR / "media"))
MEDIA_URL = "/private-media/"  # intentionally not routed: files are never served directly
MAX_VIDEO_MB = int(os.environ.get("FZ_MAX_VIDEO_MB", "500"))
MAX_IMAGE_MB = int(os.environ.get("FZ_MAX_IMAGE_MB", "5"))

# logging: console always, a rotating file when FZ_LOG_DIR is set, Telegram alerts for errors when a bot token + admin chat are configured
_handlers = {
    "console": {"class": "logging.StreamHandler"},
    "telegram": {"class": "gym.logging_handlers.TelegramAlertHandler", "level": "ERROR"},
}
if os.environ.get("FZ_LOG_DIR"):
    Path(os.environ["FZ_LOG_DIR"]).mkdir(parents=True, exist_ok=True)
    _handlers["file"] = {"class": "logging.handlers.RotatingFileHandler", "filename": str(Path(os.environ["FZ_LOG_DIR"]) / "app.log"),
                         "maxBytes": 2_000_000, "backupCount": 5, "encoding": "utf-8"}
LOGGING = {
    "version": 1, "disable_existing_loggers": False, "handlers": _handlers,
    "loggers": {"django.request": {"handlers": list(_handlers), "level": "ERROR", "propagate": False},
                "gym": {"handlers": list(_handlers), "level": "INFO", "propagate": False}},
}
