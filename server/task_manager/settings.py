"""
Django settings for task_manager project.

Generated by 'django-admin startproject' using Django 2.2.2.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

import os
from datetime import timedelta

import environ

# Build paths inside the project like this: os.path.join(BASE_DIR, ...)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

env = environ.Env()

IN_PYTEST = env.bool('IN_PYTEST', default=False)

# print(f"{IN_PYTEST=}")

if IN_PYTEST:
    env.read_env(os.path.join(BASE_DIR, '.env.test'))

IN_DOCKER = env.bool('DJANGO_IN_DOCKER', default=False)

EXTERNAL_BASE_URL = env.str('EXTERNAL_BASE_URL',
        default='https://dash.cloudreactor.io/')

print(f"settings.py: {BASE_DIR=}, {IN_DOCKER=}, {EXTERNAL_BASE_URL=}")

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = env.str('DJANGO_SECRET_KEY',
        default='pi_fwib_-pn0z8($mb994z6(2%b@v2@k=laj90raanvj3!0(1i')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = env.bool('DJANGO_DEBUG', default=False)

ALLOWED_HOSTS = ['*']

ROOT_LOGGING_LEVEL = env.str('DJANGO_ROOT_LOGGING_LEVEL', default='INFO')
BOTO_LOGGING_LEVEL = env.str('DJANGO_BOTO_LOGGING_LEVEL', default='INFO')

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.humanize',
    'django.contrib.postgres',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django_extensions',
    'guardian',
    'django_middleware_global_request',
    'rest_framework',
    'djoser',
    'corsheaders',
    'rest_framework.authtoken',
    'django_filters',
    'drf_spectacular',
    'dynamic_fixtures',
    'processes.apps.ProcessesConfig',
]

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',  # this is default
    'guardian.backends.ObjectPermissionBackend',
)

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'csp.middleware.CSPMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    'django.middleware.http.ConditionalGetMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django_middleware_global_request.middleware.GlobalRequestMiddleware',
]

# enable_queryinspect = os.environ.get('DJANGO_ENABLE_QUERYINSPECT') == 'TRUE'
#
# if enable_queryinspect:
#     MIDDLEWARE.append('qinspect.middleware.QueryInspectMiddleware')

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOWED_ORIGINS = env.str('DJANGO_CORS_ALLOWED_ORIGINS',
        default='http://localhost:3000').split(',')

print(f"settings.py: {CORS_ALLOWED_ORIGINS=}")

# So that gunicorn will use the X-Forwarded headers (set by the AWS ALB) to
# determine if a request is secure.
USE_X_FORWARDED_HOST = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Enable HSTS with a default expiration of 1 hour (change this to 1 year later).
# Should be overridden in development and testing to 0 to disable HSTS.
SECURE_HSTS_SECONDS = env.int('DJANGO_SECURE_HSTS_SECONDS', 60 * 60 * 24 * 365)

# django-csf settings
CSP_DEFAULT_SRC = ["'none'"]
CSP_SCRIPT_SRC = ["'self'"]
CSP_STYLE_SRC = [
    "'self'",
    'https://*.fontawesome.com',
    'https://fonts.googleapis.com',
    "'unsafe-inline'", # temporary until Create React App stops injecting styles
]
CSP_FONT_SRC = [
    "'self'",
    'https://*.fontawesome.com',
    'https://fonts.gstatic.com',
]

# For now, we are allowing link icons to be loaded from external sites.
# https://stackoverflow.com/questions/35776011/content-security-policy-allowing-all-external-images
CSP_IMG_SRC = [ 'https:', 'data:']
CSP_CONNECT_SRC = [
    "'self'",
    # The default is used when building the static site, and doesn't affect it
    env.str('DJANGO_API_BASE_URL', default='https://api.cloudreactor.io')
]
CSP_MANIFEST_SRC = ["'self'"]

ROOT_URLCONF = 'task_manager.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
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

WSGI_APPLICATION = 'task_manager.wsgi.application'


# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases
default_db_host = 'db' if IN_DOCKER else 'localhost'
default_db_port = '5432' if IN_DOCKER else '9432'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql_psycopg2',
        'NAME': env.str('DATABASE_NAME', default='cloudreactor_task_manager'),
        'USER': env.str('DATABASE_USER', default='web'),
        'PASSWORD': env.str('DATABASE_PASSWORD', default='webpass'),
        'HOST': env.str('DATABASE_HOST', default=default_db_host),
        'PORT': env.str('DATABASE_PORT', default=default_db_port),
        'TEST': {
            'NAME': 'cloudreactor_task_manager_test'
        }
    },
    # 'test': {
    #     'ENGINE': 'django.db.backends.postgresql_psycopg2',
    #     'NAME': 'cloudreactor_task_manager_test',
    #     'USER': env.str('DATABASE_USER', default='web'),
    #     'PASSWORD': env.str('DATABASE_PASSWORD', default='webpass'),
    #     'HOST': env.str('DATABASE_HOST', default=default_db_host),
    #     'PORT': env.str('DATABASE_PORT', default=default_db_port),
    # }
}

# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

password_validators = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

AUTH_PASSWORD_VALIDATORS = [] if env.bool('DJANGO_ALLOW_WEAK_PASSWORDS', default=False) else password_validators

# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_ROOT = env.str('DJANGO_STATIC_ROOT', default=os.path.join(BASE_DIR, 'static'))

CRA_ROOT = env.str('CRA_ROOT',
        default=os.path.join(BASE_DIR, '..', 'client', 'build'))

STATICFILES_DIRS = [os.path.join(CRA_ROOT, 'static')] if CRA_ROOT else []

STATIC_URL = '/static/'

WHITENOISE_ROOT = env.str('WHITENOISE_ROOT', default=CRA_ROOT)

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'processes.authentication.SaasTokenAuthentication',
        'processes.authentication.AllowBadJwtTokenAuthentication',
        # Required for API Browser
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'processes.permissions.IsCreatedByGroup',
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.LimitOffsetPagination',
    'PAGE_SIZE': 50,
    'DEFAULT_FILTER_BACKENDS': ('django_filters.rest_framework.DjangoFilterBackend',
                                'rest_framework.filters.SearchFilter',
                                'rest_framework.filters.OrderingFilter',),
    'EXCEPTION_HANDLER': 'processes.exception.friendly_exception_handler',
    'DEFAULT_THROTTLE_CLASSES': [
        'processes.throttling.SubscriptionRateThrottle'
    ],
    'DEFAULT_THROTTLE_RATES': {
        'burst': '1000/min', # For both human and machine users
        'subscription': '240/min', # Rate is for human users
    },
    'TEST_REQUEST_DEFAULT_FORMAT': 'json',
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}

IN_SCHEMA_GENERATION = env.bool('DJANGO_IN_SCHEMA_GENERATION',
    default=False)

if IN_SCHEMA_GENERATION:
    print("In Schema Generation")

    # Remove SessionAuthentication, JWT might be documented later
    REST_FRAMEWORK['DEFAULT_AUTHENTICATION_CLASSES'] = (
        'processes.authentication.SaasTokenAuthentication',
    )

DJOSER = {
    'SERIALIZERS': {
        'current_user': 'processes.serializers.FullUserSerializer'
    },
    'SEND_ACTIVATION_EMAIL': True,
    'SEND_CONFIRMATION_EMAIL': True,
    'PASSWORD_CHANGED_EMAIL_CONFIRMATION': True,
    'USERNAME_CHANGED_EMAIL_CONFIRMATION': True,
    'PASSWORD_RESET_SHOW_EMAIL_NOT_FOUND': True,
    'ACTIVATION_URL': 'activate_user/?uid={uid}&token={token}',
    'PASSWORD_RESET_CONFIRM_URL': 'password_reset/?uid={uid}&token={token}',
}

SIMPLE_JWT = {
    # For debugging refresh
    #'ACCESS_TOKEN_LIFETIME': timedelta(seconds=10),
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=1),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUTH_HEADER_TYPES': ('JWT',),
}

if env.bool('DJANGO_USE_CONSOLE_EMAIL_BACKEND', False):
    EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
else:
    EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

    EMAIL_HOST = env.str('DJANGO_EMAIL_HOST', default='localhost')
    EMAIL_PORT = env.int('DJANGO_EMAIL_PORT', default=25)
    EMAIL_HOST_USER = env.str('DJANGO_EMAIL_HOST_USER', default='emailer')
    EMAIL_HOST_PASSWORD = env.str('DJANGO_EMAIL_HOST_PASSWORD', default='email_pw')
    EMAIL_USE_TLS = env.bool('DJANGO_EMAIL_USE_TLS', default=True)

#print(f"{EMAIL_BACKEND=}")

DEFAULT_FROM_EMAIL = env.str('DJANGO_DEFAULT_FROM_EMAIL', default='webmaster@cloudreactor.io')

LOGGING = {
    'disable_existing_loggers': False,
    'version': 1,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
        'simple': {
            'format': '{levelname} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            # logging handler that outputs log messages to terminal
            'class': 'logging.StreamHandler',
            'level': ROOT_LOGGING_LEVEL,  # message level to be written to console
            'formatter': 'verbose'
        },
    },
    'loggers': {
        '': {
            # this sets root level logger to log debug and higher level
            # logs to console. All other loggers inherit settings from
            # root level logger.
            'handlers': ['console'],
            'level': ROOT_LOGGING_LEVEL,
            'propagate': False,  # this tells logger to send logging message
            # to its parent (will send if set to True)
        },
        # 'django.db.backends': {
        #     'level': 'DEBUG',
        #     'handlers': ['console'],
        #     'propagate': False
        # },
        'botocore': {
            'level': 'DEBUG',
            'handlers': ['console'],
            'propagate': False
        },
        'faker': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False
        },
        'hooks': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False
        },
        'factory': {
            'level': 'INFO',
            'handlers': ['console'],
            'propagate': False
        },
        'boto3': {
            'level': BOTO_LOGGING_LEVEL,
            'handlers': ['console'],
            'propagate': False
        },
        'botocore': {
            'level': BOTO_LOGGING_LEVEL,
            'handlers': ['console'],
            'propagate': False
        },
        # 'qinspect': {
        #     'handlers': ['console'],
        #     'level': 'DEBUG',
        #     'propagate': True,
        # },
    },
}

CACHE_INVALIDATE_ON_CREATE = 'whole-model'

SPECTACULAR_SETTINGS = {
    'TITLE': 'CloudReactor API',
    'DESCRIPTION': 'CloudReactor API Documentation',
    'VERSION': '0.2.0',
    'SCHEMA_PATH_PREFIX': '/api/v1',
    # Remove matching SCHEMA_PATH_PREFIX from operation path. Usually used in
    # conjunction with appended prefixes in SERVERS.
    'SCHEMA_PATH_PREFIX_TRIM': True,
    'SERVERS': [
        {
            'url': 'https://api.cloudreactor.io/api/v1',
            'description': 'CloudReactor API server',
        }
    ],
    'CONTACT': {
        'name': 'Jeff Tsay',
        'email': 'jeff@cloudreactor.io',
        'url': 'https://cloudreactor.io/'
    },
    'EXTERNAL_DOCS': {
        'url': 'https://docs.cloudreactor.io/',
        'description': 'CloudReactor Documentation Home',
    },
    'AUTHENTICATION_WHITELIST': [
        'processes.authentication.SaasTokenAuthentication',
    ],
    # 'COMPONENT_SPLIT_REQUEST': True,
    # Aid client generator targets that have trouble with read-only properties.
    # 'COMPONENT_NO_READ_ONLY_REQUIRED': True,
    # Code generation has trouble with oneOf with BlankEnum choice
    'ENUM_ADD_EXPLICIT_BLANK_NULL_CHOICE': False,
    'ENUM_NAME_OVERRIDES': {
        # Duplicated from AwsEcsExecutionMethod.ALL_LAUNCH_TYPES
        'AwsEcsLaunchType': ['FARGATE', 'EC2'],
        # Duplicated from NOTIFICATION_SEVERITIES in notification.py
        'NotificationSeverity': ['critical', 'error', 'warning', 'info'],
    },
    'PREPROCESSING_HOOKS': [
        'spectacular.preprocessing_hook'
    ],
}


# Application-specific settings for export in django.conf.settings
ENVIRON = env
# End application-specific settings

# if enable_queryinspect:
#   QUERY_INSPECT_ENABLED = True
#   QUERY_INSPECT_LOG_QUERIES = True
#   QUERY_INSPECT_ABSOLUTE_LIMIT = 1000
#   QUERY_INSPECT_LOG_TRACEBACKS = True
