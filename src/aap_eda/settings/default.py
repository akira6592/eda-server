#  Copyright 2022 Red Hat, Inc.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
"""
Django settings.

For more information on this file, see
https://docs.djangoproject.com/en/4.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/4.1/ref/settings/

Quick-start development settings - unsuitable for production
See https://docs.djangoproject.com/en/4.1/howto/deployment/checklist/

Common settings:

The following values can be defined as well as environment variables
with the prefix EDA_:

* SETTINGS_FILE - An path to file to load settings from
    Default: /etc/eda/settings.yaml
* SECRET_KEY - A Django secret key.
* SECRET_KEY_FILE - A file path to load Django secret key from.
    Example:
      export SECRET_KEY_FILE=/etc/eda
* DEBUG
* ALLOWED_HOSTS - A list of allowed hostnames or
    a comma separated string.
    Ex: export EDA_ALLOWED_HOSTS = "localhost,127.0.0.1"
    Ex: export EDA_ALLOWED_HOSTS = '["localhost", "127.0.0.1"]'
* SESSION_COOKIE_AGE - Session cookie expiration time

Database settings:

* DB_HOST - Database hostname (default: "127.0.0.1")
* DB_PORT - Database port (default: 5432)
* DB_USER - Database username (default: "postgres")
* DB_PASSWORD - Database user password (default: None)
* DB_NAME - Database name (default: "eda")

Redis queue settings:

* MQ_UNIX_SOCKET_PATH - Redis unix socket path, mutually exclusive with
    host and port (default: None)
* MQ_HOST - Redis queue hostname (default: "127.0.0.1")
* MQ_PORT - Redis queue port (default: 6379)
* MQ_DB - Redis queue database (default: 0)
"""
import dynaconf
from django.core.exceptions import ImproperlyConfigured

default_settings_file = "/etc/eda/settings.yaml"

settings = dynaconf.Dynaconf(
    envvar="EDA_SETTINGS_FILE",
    envvar_prefix="EDA",
    settings_file=default_settings_file,
)


# ---------------------------------------------------------
# DJANGO SETTINGS
# ---------------------------------------------------------
def _get_secret_key() -> str:
    secret_key = settings.get("SECRET_KEY")
    secret_key_file = settings.get("SECRET_KEY_FILE")
    if secret_key and secret_key_file:
        raise ImproperlyConfigured(
            'Settings parameters "SECRET_KEY" and "SECRET_KEY_FILE"'
            " are mutually exclusive."
        )
    if secret_key:
        return secret_key
    if secret_key_file:
        with open(secret_key_file) as fp:
            return fp.read().strip()
    raise ImproperlyConfigured(
        'Either "SECRET_KEY" or "SECRET_KEY_FILE" settings'
        " parameters must be set."
    )


SECRET_KEY = _get_secret_key()

DEBUG = settings.get("DEBUG", False)

ALLOWED_HOSTS = settings.get("ALLOWED_HOSTS", [])
ALLOWED_HOSTS = (
    ALLOWED_HOSTS.split(",")
    if isinstance(ALLOWED_HOSTS, str)
    else ALLOWED_HOSTS
)

# Session settings
SESSION_COOKIE_AGE = settings.get("SESSION_COOKIE_AGE", 1800)
SESSION_SAVE_EVERY_REQUEST = True

# Application definition
INSTALLED_APPS = [
    "daphne",
    # Django apps
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.staticfiles",
    # Third party apps
    "rest_framework",
    "drf_spectacular",
    "django_rq",
    "django_filters",
    # Local apps
    "aap_eda.api",
    "aap_eda.core",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "aap_eda.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
            ],
        },
    },
]

WSGI_APPLICATION = "aap_eda.wsgi.application"

ASGI_APPLICATION = "aap_eda.asgi.application"


# Database
# https://docs.djangoproject.com/en/4.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "HOST": settings.get("DB_HOST", "127.0.0.1"),
        "PORT": settings.get("DB_PORT", 5432),
        "USER": settings.get("DB_USER", "postgres"),
        "PASSWORD": settings.get("DB_PASSWORD"),
        "NAME": settings.get("DB_NAME", "eda"),
    }
}


# Password validation
# https://docs.djangoproject.com/en/4.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",  # noqa: E501
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",  # noqa: E501
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",  # noqa: E501
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",  # noqa: E501
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.1/topics/i18n/

LANGUAGE_CODE = "en-us"

USE_I18N = True

TIME_ZONE = "UTC"

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.1/howto/static-files/

STATIC_URL = "static/"

MEDIA_ROOT = settings.get("MEDIA_ROOT", "/var/lib/eda/files")

# Default primary key field type
# https://docs.djangoproject.com/en/4.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

AUTH_USER_MODEL = "core.User"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_PAGINATION_CLASS": "aap_eda.api.pagination.DefaultPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "aap_eda.api.authentication.SessionAuthentication",
        "rest_framework.authentication.BasicAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
        "aap_eda.api.permissions.RoleBasedPermission",
    ],
    "TEST_REQUEST_DEFAULT_FORMAT": "json",
}

# ---------------------------------------------------------
# TASKING SETTINGS
# ---------------------------------------------------------
RQ = {
    "QUEUE_CLASS": "aap_eda.core.tasking.Queue",
    "JOB_CLASS": "aap_eda.core.tasking.Job",
}

RQ_UNIX_SOCKET_PATH = settings.get("MQ_UNIX_SOCKET_PATH", None)

if RQ_UNIX_SOCKET_PATH:
    RQ_QUEUES = {
        "default": {
            "UNIX_SOCKET_PATH": RQ_UNIX_SOCKET_PATH,
        },
        "activation": {
            "UNIX_SOCKET_PATH": RQ_UNIX_SOCKET_PATH,
        },
    }
else:
    RQ_QUEUES = {
        "default": {
            "HOST": settings.get("MQ_HOST", "localhost"),
            "PORT": settings.get("MQ_PORT", 6379),
            "DEFAULT_TIMEOUT": -1,
        },
        "activation": {
            "HOST": settings.get("MQ_HOST", "localhost"),
            "PORT": settings.get("MQ_PORT", 6379),
            "DEFAULT_TIMEOUT": -1,
        },
    }
RQ_QUEUES["default"]["DB"] = settings.get("MQ_DB", 0)
RQ_QUEUES["activation"]["DB"] = settings.get("MQ_DB", 0)

RQ_STARTUP_JOBS = []
RQ_PERIODIC_JOBS = []
RQ_CRON_JOBS = []
RQ_SCHEDULER_JOB_INTERVAL = settings.get("SCHEDULER_JOB_INTERVAL", 5)

# ---------------------------------------------------------
# APPLICATION SETTINGS
# ---------------------------------------------------------

API_PREFIX = settings.get("API_PREFIX", "api/eda").strip("/")

SPECTACULAR_SETTINGS = {
    "TITLE": "Event Driven Ansible API",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": f"/{API_PREFIX}/v[0-9]",
    "SCHEMA_PATH_PREFIX_TRIM": True,
    "SERVERS": [{"url": f"/{API_PREFIX}/v1"}],
    "PREPROCESSING_HOOKS": [
        "aap_eda.api.openapi.preprocess_filter_api_routes"
    ],
}

# ---------------------------------------------------------
# LOGGING SETTINGS
# ---------------------------------------------------------

APP_LOG_LEVEL = settings.get("APP_LOG_LEVEL", "INFO")

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {
            "format": "{asctime} {levelname:<8} {message}",
            "style": "{",
        },
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
    },
    "root": {"handlers": ["console"], "level": "WARNING"},
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "WARNING",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.channels.server": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "aap_eda": {
            "handlers": ["console"],
            "level": APP_LOG_LEVEL,
            "propagate": False,
        },
    },
}

# ---------------------------------------------------------
# CONTROLLER SETTINGS
# ---------------------------------------------------------

EDA_CONTROLLER_URL = settings.get("CONTROLLER_URL", "default_controller_url")
EDA_CONTROLLER_TOKEN = settings.get(
    "CONTROLLER_TOKEN", "default_controller_token"
)
EDA_CONTROLLER_SSL_VERIFY = settings.get("CONTROLLER_SSL_VERIFY", "yes")

# ---------------------------------------------------------
# DEPLOYMENT SETTINGS
# ---------------------------------------------------------

DEPLOYMENT_TYPE = settings.get("DEPLOYMENT_TYPE", "local")
WEBSOCKET_BASE_URL = settings.get("WEBSOCKET_BASE_URL", "ws://localhost:8000")
WEBSOCKET_SSL_VERIFY = settings.get("WEBSOCKET_SSL_VERIFY", "yes")
PODMAN_SOCKET_URL = settings.get("PODMAN_SOCKET_URL", None)
PODMAN_MEM_LIMIT = settings.get("PODMAN_MEM_LIMIT", "200m")
PODMAN_ENV_VARS = settings.get("PODMAN_ENV_VARS", {})
PODMAN_MOUNTS = settings.get("PODMAN_MOUNTS", [])
PODMAN_EXTRA_ARGS = settings.get("PODMAN_EXTRA_ARGS", {})

# ---------------------------------------------------------
# RULEBOOK LIVENESS SETTINGS
# ---------------------------------------------------------

RULEBOOK_LIVENESS_CHECK_SECONDS = settings.get(
    "RULEBOOK_LIVENESS_CHECK_SECONDS", 300
)
RULEBOOK_LIVENESS_TIMEOUT_SECONDS = settings.get(
    "RULEBOOK_LIVENESS_TIMEOUT_SECONDS", 610
)
ACTIVATION_RESTART_SECONDS_ON_COMPLETE = settings.get(
    "ACTIVATION_RESTART_SECONDS_ON_COMPLETE", 0
)
ACTIVATION_RESTART_SECONDS_ON_FAILURE = settings.get(
    "ACTIVATION_RESTART_SECONDS_ON_FAILURE", 60
)
ACTIVATION_MAX_RESTARTS_ON_FAILURE = settings.get(
    "ACTIVATION_MAX_RESTARTS_ON_FAILURE", 5
)

# ---------------------------------------------------------
# RULEBOOK ENGINE LOG LEVEL
# ---------------------------------------------------------
ANSIBLE_RULEBOOK_LOG_LEVEL = settings.get("ANSIBLE_RULEBOOK_LOG_LEVEL", "-v")
ANSIBLE_RULEBOOK_FLUSH_AFTER = settings.get("ANSIBLE_RULEBOOK_FLUSH_AFTER", 1)
