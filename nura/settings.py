import os
import sys
from pathlib import Path
from urllib.parse import unquote, urlparse
from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# Agregar la carpeta services a sys.path para encontrar la app chat
sys.path.insert(0, str(BASE_DIR / "services"))


SECRET_KEY = os.getenv('DJANGO_SECRET_KEY', 'unsafe-secret-key-for-dev-only-change-me')
DEBUG = os.getenv('DJANGO_DEBUG', 'True') == 'True'
ALLOWED_HOSTS = os.getenv('DJANGO_ALLOWED_HOSTS', '*').split(',')


INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'rest_framework',
    'rest_framework_simplejwt',
    'rest_framework_simplejwt.token_blacklist',
    'dj_rest_auth',
    'dj_rest_auth.registration',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'chat',
    'corsheaders',
    'drf_spectacular',
]

AUTHENTICATION_BACKENDS = [
    'django.contrib.auth.backends.ModelBackend',
    'allauth.account.auth_backends.AuthenticationBackend',
]

SITE_ID = 1

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ),
    # Módulo 6 — API pública documentada. drf-spectacular ya estaba en
    # requirements.txt pero no estaba wireado: no había ni el generador de
    # schema ni una URL de Swagger/Redoc en todo el proyecto.
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

SPECTACULAR_SETTINGS = {
    'TITLE': 'Nura Intelligence API',
    'DESCRIPTION': 'API pública de Nura Intelligence — plataforma de Business Intelligence conversacional.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

REST_AUTH = {
    'USE_JWT': True,
    'TOKEN_MODEL': None,
    'JWT_AUTH_COOKIE': None,
    'JWT_AUTH_REFRESH_COOKIE': None,
    'JWT_AUTH_HTTPONLY': False,
    'JWT_AUTH_RETURN_EXPIRATION': False,
    'REGISTER_SERIALIZER': 'dj_rest_auth.registration.serializers.RegisterSerializer',
    'PASSWORD_RESET_SERIALIZER': 'nura.serializers.CustomPasswordResetSerializer',
    'LOGIN_SERIALIZER': 'dj_rest_auth.serializers.LoginSerializer',
}

from datetime import timedelta
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=60),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

ACCOUNT_ADAPTER = 'nura.adapters.NuraAccountAdapter'
ACCOUNT_EMAIL_VERIFICATION = 'optional'
FRONTEND_URL = os.getenv('FRONTEND_URL', 'http://localhost:5173')
ACCOUNT_EMAIL_CONFIRMATION_EXPIRE_DAYS = 3
ACCOUNT_EMAIL_SUBJECT_PREFIX = ''
ACCOUNT_LOGIN_METHODS = {'email'}
ACCOUNT_LOGOUT_ON_GET = True
ACCOUNT_SIGNUP_FIELDS = ['email*', 'username*', 'password1*', 'password2*']
ACCOUNT_UNIQUE_EMAIL = True
ACCOUNT_USER_MODEL_USERNAME_FIELD = 'username'
LOGIN_ON_EMAIL_CONFIRMATION = True

EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
if os.getenv('MAILGUN_API_KEY') and os.getenv('MAILGUN_DOMAIN'):
    EMAIL_BACKEND = 'nura.mail_backend.MailgunAPIBackend'
    DEFAULT_FROM_EMAIL = os.getenv('DEFAULT_FROM_EMAIL', f'no-reply@{os.getenv("MAILGUN_DOMAIN")}')


MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'allauth.account.middleware.AccountMiddleware',
]


# FIXED: 2026-10-12 CORS_ALLOW_ALL_ORIGINS=True combinado con
# CORS_ALLOW_CREDENTIALS=True hacía que CUALQUIER sitio web pudiera hacerle
# peticiones autenticadas (con cookies de sesión) al backend de Nura desde
# el navegador de un usuario logueado — el patrón clásico que
# django-cors-headers advierte explícitamente como inseguro. Mismo patrón
# de fallback que el resto del archivo: si se define DJANGO_CORS_ALLOWED_ORIGINS
# (lista separada por comas) se usa esa lista explícita; si no, se cae a los
# orígenes de desarrollo local de siempre, nunca a "*".
_cors_env = os.getenv('DJANGO_CORS_ALLOWED_ORIGINS')
if _cors_env:
    CORS_ALLOWED_ORIGINS = [o.strip() for o in _cors_env.split(',') if o.strip()]
else:
    CORS_ALLOWED_ORIGINS = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
CORS_ALLOW_CREDENTIALS = True
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
] + CORS_ALLOWED_ORIGINS
ROOT_URLCONF = 'nura.urls'


TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'nura' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]


WSGI_APPLICATION = 'nura.wsgi.application'


# Database
# Antes: si no había DATABASE_URL en el entorno, Django ni siquiera arrancaba
# (raise ValueError), y el único motor soportado era Postgres — obligando a
# tener Postgres corriendo en local incluso fuera de Docker. Ahora, si no
# hay DATABASE_URL, se usa SQLite automáticamente para poder levantar el
# proyecto en local sin dependencias externas.
DATABASE_URL = os.getenv('DATABASE_URL')
if not DATABASE_URL:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    parsed = urlparse(DATABASE_URL)
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': parsed.path.lstrip('/'),
            'USER': unquote(parsed.username or ''),
            'PASSWORD': unquote(parsed.password or ''),
            'HOST': parsed.hostname or '',
            'PORT': parsed.port or '5432',
        }
    }


AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]


LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True


STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = []

# Media files (uploads) - Supabase Storage (producción) o disco local (desarrollo)
# ANTES: el backend de storage estaba forzado a S3Boto3Storage sin ningún
# fallback. Sin credenciales de Supabase (lo normal en un entorno local
# recién clonado), cualquier subida de archivo fallaba en tiempo de
# ejecución, aunque el servidor arrancara sin errores aparentes.
USE_S3_STORAGE = bool(os.getenv('SUPABASE_PROJECT_ID') and os.getenv('SUPABASE_ACCESS_KEY_ID'))

if USE_S3_STORAGE:
    # Supabase S3 Configuration
    S3_ACCESS_KEY_ID = os.getenv('SUPABASE_ACCESS_KEY_ID')
    S3_SECRET_ACCESS_KEY = os.getenv('SUPABASE_SECRET_ACCESS_KEY')
    S3_STORAGE_BUCKET_NAME = os.getenv('SUPABASE_BUCKET_NAME', 'nura-datasets')
    S3_ENDPOINT_URL = f"https://{os.getenv('SUPABASE_PROJECT_ID')}.supabase.co/storage/v1/s3"
    S3_REGION_NAME = 'us-east-1'  # Default for Supabase
    S3_FILE_OVERWRITE = False
    S3_DEFAULT_ACL = 'public-read'  # Or 'private' depending on your needs
    S3_OBJECT_PARAMETERS = {
        'CacheControl': 'max-age=86400',
    }

    STORAGES = {
        'default': {
            'BACKEND': 'storages.backends.s3boto3.S3Boto3Storage',
            'OPTIONS': {
                'access_key': S3_ACCESS_KEY_ID,
                'secret_key': S3_SECRET_ACCESS_KEY,
                'bucket_name': S3_STORAGE_BUCKET_NAME,
                'endpoint_url': S3_ENDPOINT_URL,
                'region_name': S3_REGION_NAME,
                'file_overwrite': S3_FILE_OVERWRITE,
                'default_acl': S3_DEFAULT_ACL,
                'object_parameters': S3_OBJECT_PARAMETERS,
                'querystring_auth': False,
            },
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage' if not DEBUG else 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    }
else:
    # Fallback de desarrollo: guarda los archivos subidos en disco, bajo
    # MEDIA_ROOT, y los sirve desde MEDIA_URL. No requiere ninguna cuenta
    # externa para levantar el proyecto localmente.
    MEDIA_URL = '/media/'
    MEDIA_ROOT = BASE_DIR / 'media'

    STORAGES = {
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'whitenoise.storage.CompressedStaticFilesStorage' if not DEBUG else 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    }


DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# --- Celery (Módulo 2: procesamiento asíncrono) ---
# Si no hay REDIS_URL configurado, las tareas corren en modo "eager"
# (síncronas, en el mismo proceso) — así el proyecto sigue funcionando en
# local sin necesitar Redis instalado, igual que el fallback a SQLite.
REDIS_URL = os.getenv('REDIS_URL', '')

# Módulo 6 — caché. Mismo patrón de fallback que la BD y Celery: si hay
# REDIS_URL configurado se usa Redis de verdad (clave requerida para que
# el caché sea compartido entre varios workers/procesos en producción);
# si no, cae a un caché en memoria del propio proceso, para que el
# proyecto siga corriendo en local sin pedir infraestructura extra. Un
# caché en memoria por proceso no es apto para producción con varios
# workers (cada uno tendría su propia copia), por eso es explícitamente
# un fallback de desarrollo, igual que el modo eager de Celery.
if REDIS_URL:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.redis.RedisCache',
            'LOCATION': REDIS_URL,
        }
    }
else:
    CACHES = {
        'default': {
            'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
            'LOCATION': 'nura-local-cache',
        }
    }

CELERY_BROKER_URL = REDIS_URL or 'memory://'
CELERY_RESULT_BACKEND = REDIS_URL or 'cache+memory://'
CELERY_TASK_ALWAYS_EAGER = not bool(REDIS_URL)
CELERY_TASK_EAGER_PROPAGATES = True
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE if 'TIME_ZONE' in dir() else 'UTC'


# --- Módulo 0: Logging estructurado ---
# Antes de esto no había ningún LOGGING configurado: Django usaba su
# configuración por defecto, que en producción (DEBUG=False) directamente
# no imprime nada a consola salvo errores 500 — en un contenedor eso
# significa que `docker logs` queda prácticamente vacío. Este bloque:
#   - define un formato con timestamp + módulo + nivel, legible en
#     `docker logs` o en el drain de un proveedor (Cloudwatch, Render, etc.)
#   - loguea siempre a consola (stdout), que es lo que cualquier
#     orquestador de contenedores captura sin configuración extra
#   - el logger raíz de la app ('chat', 'nura') va a INFO en producción y
#     DEBUG en desarrollo, para no inundar la consola local con SQL queries
#   - respeta DJANGO_LOG_LEVEL si se quiere overridear sin tocar código
LOG_LEVEL = os.getenv('DJANGO_LOG_LEVEL', 'DEBUG' if DEBUG else 'INFO')

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            'datefmt': '%Y-%m-%d %H:%M:%S',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': os.getenv('DJANGO_FRAMEWORK_LOG_LEVEL', 'WARNING'),
            'propagate': False,
        },
        'django.request': {
            # Los 500 de Django ya traen traceback completo por acá.
            'handlers': ['console'],
            'level': 'ERROR',
            'propagate': False,
        },
        # Loggers propios de la app: todo lo que viva bajo services/ usa
        # logging.getLogger(__name__), que con la estructura de paquetes
        # actual (services/chat/..., services/ai/..., services/analytics/...)
        # cae bajo estos tres nombres.
        'chat': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'ai': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'analytics': {
            'handlers': ['console'],
            'level': LOG_LEVEL,
            'propagate': False,
        },
        'celery': {
            'handlers': ['console'],
            # Celery es ruidoso incluso en DEBUG: su propio framework interno
            # (chord/chain/group, introspección de tareas) loguea a nivel
            # DEBUG cosas que no son del dominio de la app. Se fija a INFO
            # por defecto SIEMPRE (en dev y en producción), separado de
            # LOG_LEVEL, para no inundar la consola local con ruido interno
            # de Celery — las tareas propias (analyze_dataset_task, etc.) ya
            # loguean con logging.getLogger("chat"), así que esto no pierde
            # visibilidad real. Overrideable con DJANGO_CELERY_LOG_LEVEL si
            # alguna vez hace falta depurar Celery mismo.
            'level': os.getenv('DJANGO_CELERY_LOG_LEVEL', 'INFO'),
            'propagate': False,
        },
    },
}

# --- Módulo 0: Monitoring (Sentry opcional) ---
# Mismo patrón de fallback que Redis/Celery/Caché en todo este proyecto:
# si no hay SENTRY_DSN configurado, simplemente no se inicializa — el
# proyecto sigue funcionando igual en local sin pedir una cuenta de
# Sentry. Si se configura SENTRY_DSN (en producción, normalmente), cada
# excepción no capturada y cada log de nivel ERROR se reporta automática.
# `sentry-sdk` se importa de forma perezosa y tolerante: si el paquete no
# está instalado (p. ej. un entorno viejo que no corrió pip install de
# nuevo) no se rompe el arranque del proyecto, solo se omite el reporte.
SENTRY_DSN = os.getenv('SENTRY_DSN', '')
if SENTRY_DSN:
    try:
        import sentry_sdk
        from sentry_sdk.integrations.django import DjangoIntegration
        from sentry_sdk.integrations.celery import CeleryIntegration
        from sentry_sdk.integrations.logging import LoggingIntegration

        sentry_sdk.init(
            dsn=SENTRY_DSN,
            integrations=[
                DjangoIntegration(),
                CeleryIntegration(),
                LoggingIntegration(level=None, event_level='ERROR'),
            ],
            traces_sample_rate=float(os.getenv('SENTRY_TRACES_SAMPLE_RATE', '0.0')),
            environment=os.getenv('SENTRY_ENVIRONMENT', 'development' if DEBUG else 'production'),
            send_default_pii=False,
        )
    except ImportError:
        import logging as _logging
        _logging.getLogger(__name__).warning(
            "SENTRY_DSN está configurado pero 'sentry-sdk' no está instalado "
            "(pip install -r requirements.txt) — el reporte a Sentry queda desactivado."
        )
