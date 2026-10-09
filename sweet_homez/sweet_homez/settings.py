"""
Django settings for SweetHomez.

Production configuration:
    Domain: sweethomestz.com
    Web Server: Nginx
    Application Server: Gunicorn
    Database: PostgreSQL
"""

import os
from datetime import timedelta
from pathlib import Path


# ============================================================
# BASE DIRECTORY AND ENVIRONMENT
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent


def load_local_env(path):
    """Load .env variables without overriding existing environment variables."""
    if not path.exists():
        return

    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()

        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)

        os.environ.setdefault(
            key.strip(),
            value.strip().strip('"').strip("'")
        )


load_local_env(BASE_DIR / ".env")


def env_bool(name, default=False):
    return os.getenv(name, str(default)).lower() in (
        "true", "1", "yes", "on"
    )


# ============================================================
# SECURITY SETTINGS
# ============================================================

SECRET_KEY = os.getenv("DJANGO_SECRET_KEY", "")

if not SECRET_KEY:
    raise RuntimeError("DJANGO_SECRET_KEY must be configured.")


DEBUG = env_bool("DJANGO_DEBUG", False)


ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv(
        "DJANGO_ALLOWED_HOSTS",
        "sweethomestz.com,www.sweethomestz.com,localhost,127.0.0.1"
    ).split(",")
    if host.strip()
]


CSRF_TRUSTED_ORIGINS = [
    "https://sweethomestz.com",
    "https://www.sweethomestz.com",
]


# Trust HTTPS information passed by the local Nginx reverse proxy.
# Nginx must overwrite X-Forwarded-Proto with its own $scheme.
SECURE_PROXY_SSL_HEADER = (
    "HTTP_X_FORWARDED_PROTO",
    "https",
)


# Enable SSL redirect only after HTTPS is configured.
SECURE_SSL_REDIRECT = env_bool(
    "DJANGO_SECURE_SSL_REDIRECT",
    False
)


# Use secure cookies after HTTPS is operational.
SESSION_COOKIE_SECURE = env_bool(
    "DJANGO_SESSION_COOKIE_SECURE",
    False
)

CSRF_COOKIE_SECURE = env_bool(
    "DJANGO_CSRF_COOKIE_SECURE",
    False
)


# HTTP Strict Transport Security.
# Keep disabled initially; enable after verifying HTTPS.
SECURE_HSTS_SECONDS = int(
    os.getenv("DJANGO_SECURE_HSTS_SECONDS", "0")
)

SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False


SECURE_CONTENT_TYPE_NOSNIFF = True

X_FRAME_OPTIONS = "DENY"


# ============================================================
# API KEY
# ============================================================

API_KEY = os.getenv("API_KEY", "")

if not API_KEY:
    raise RuntimeError(
        "API_KEY must be configured in the environment or .env file."
    )


# ============================================================
# INSTALLED APPLICATIONS
# ============================================================

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Third-party applications
    "rest_framework",
    "drf_spectacular",
    "rest_framework_simplejwt.token_blacklist",

    # SweetHomez applications
    "users",
    "houses",
    "lookups",
    "assistant.apps.AssistantConfig",
]


# ============================================================
# MIDDLEWARE
# ============================================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",

    "sweet_homez.middleware.RequireAPIKeyMiddleware",

    "django.contrib.sessions.middleware.SessionMiddleware",

    "houses.middleware.QueryParameterLocaleMiddleware",

    "django.middleware.common.CommonMiddleware",

    "django.middleware.csrf.CsrfViewMiddleware",

    "django.contrib.auth.middleware.AuthenticationMiddleware",

    "django.contrib.messages.middleware.MessageMiddleware",

    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ============================================================
# URL AND WSGI CONFIGURATION
# ============================================================

ROOT_URLCONF = "sweet_homez.urls"

WSGI_APPLICATION = "sweet_homez.wsgi.application"


# ============================================================
# TEMPLATES
# ============================================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",

        "DIRS": [],

        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ============================================================
# DATABASE CONFIGURATION - POSTGRESQL
# ============================================================

DATABASES = {
    "default": {
        "ENGINE": os.getenv(
            "DB_ENGINE",
            "django.db.backends.postgresql"
        ),

        "NAME": os.getenv(
            "DB_NAME",
            "sweet_homez_db"
        ),

        "USER": os.getenv(
            "DB_USER",
            "sweet_homez"
        ),

        "PASSWORD": os.getenv(
            "DB_PASSWORD",
            ""
        ),

        "HOST": os.getenv(
            "DB_HOST",
            "127.0.0.1"
        ),

        "PORT": os.getenv(
            "DB_PORT",
            "5432"
        ),

        "CONN_MAX_AGE": 60,
    }
}


# Preserve SQLite support when explicitly configured.
if DATABASES["default"]["ENGINE"] == "django.db.backends.sqlite3":
    DATABASES["default"] = {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / os.getenv(
            "SQLITE_NAME",
            "db.sqlite3"
        ),
    }


# ============================================================
# PASSWORD VALIDATION
# ============================================================

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]


# ============================================================
# INTERNATIONALIZATION
# ============================================================

LANGUAGE_CODE = "en"

LANGUAGES = [
    ("en", "English"),
    ("sw", "Kiswahili"),
]

LOCALE_PATHS = [
    BASE_DIR / "locale"
]

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True


# ============================================================
# STATIC FILES - NGINX
# ============================================================

STATIC_URL = "/static/"

STATIC_ROOT = BASE_DIR / "staticfiles"


# ============================================================
# MEDIA FILES - USER UPLOADS
# ============================================================

MEDIA_URL = "/media/"

MEDIA_ROOT = BASE_DIR / "media"


# ============================================================
# CUSTOM USER MODEL
# ============================================================

AUTH_USER_MODEL = "users.User"


AUTHENTICATION_BACKENDS = [
    "users.backends.RolePermissionBackend",
]


# ============================================================
# DJANGO REST FRAMEWORK
# ============================================================

REST_FRAMEWORK = {

    "DEFAULT_AUTHENTICATION_CLASSES": (
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ),

    "DEFAULT_PERMISSION_CLASSES": (
        "rest_framework.permissions.IsAuthenticated",
    ),

    "DEFAULT_SCHEMA_CLASS":
        "drf_spectacular.openapi.AutoSchema",

    "DEFAULT_PAGINATION_CLASS":
        "rest_framework.pagination.PageNumberPagination",

    "PAGE_SIZE": 20,
}


# ============================================================
# SWAGGER / OPENAPI
# ============================================================

SPECTACULAR_SETTINGS = {

    "TITLE": "SweetHomez API",

    "DESCRIPTION": (
        "Authentication and role-based user management API."
    ),

    "VERSION": "1.0.0",

    "SERVE_INCLUDE_SCHEMA": False,

    "SWAGGER_UI_SETTINGS": {
        "persistAuthorization": True,
    },

    "APPEND_COMPONENTS": {
        "securitySchemes": {
            "ApiKeyAuth": {
                "type": "apiKey",
                "in": "header",
                "name": "X-API-Key",
            },
        },
    },

    "POSTPROCESSING_HOOKS": [
        "drf_spectacular.hooks.postprocess_schema_enums",
        "sweet_homez.schema.require_api_key",
    ],
}


# ============================================================
# JWT AUTHENTICATION
# ============================================================

SIMPLE_JWT = {

    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=15),

    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),

    "ROTATE_REFRESH_TOKENS": True,

    "BLACKLIST_AFTER_ROTATION": True,
}


# ============================================================
# EMAIL CONFIGURATION
# ============================================================

MAILERS = {
    "default": {
        "BACKEND": os.getenv(
            "DJANGO_EMAIL_BACKEND",
            "django.core.mail.backends.console.EmailBackend"
        ),
    },
}

DEFAULT_FROM_EMAIL = os.getenv(
    "DEFAULT_FROM_EMAIL",
    "noreply@sweethomestz.com"
)


# ============================================================
# SWEET HOMEZ AI ASSISTANT
# ============================================================

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-6-luna")


# ============================================================
# LOGGING
# ============================================================

LOGGING = {
    "version": 1,

    "disable_existing_loggers": False,

    "formatters": {
        "verbose": {
            "format": (
                "[{asctime}] {levelname} "
                "{name}: {message}"
            ),
            "style": "{",
        },
    },

    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
    },

    "root": {
        "handlers": ["console"],
        "level": "INFO",
    },

    "loggers": {
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
    },
}


# ============================================================
# DEFAULT PRIMARY KEY
# ============================================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"
