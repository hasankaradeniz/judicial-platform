import os
from pathlib import Path

# BASE_DIR tanımlaması (Django 3.1+)
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'your-secret-key'
DEBUG = False
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'testserver', 'lexatech.ai', 'www.lexatech.ai', '145.223.82.130']

# Site domain ayarı
SITE_DOMAIN = 'https://www.lexatech.ai'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'django.contrib.sites',
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'rest_framework',     # API kullanacaksanız
    'django_filters',
    'core',               # Oluşturduğumuz uygulama
    'faiss_query',

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'allauth.account.middleware.AccountMiddleware',  # Allauth middleware
    'core.trial_middleware.TrialMiddleware',  # Deneme süresi kontrolü
    'core.trial_middleware.TrialStatusMiddleware',  # Deneme bilgilerini context'e ekler
    'core.middleware.UserAccessControlMiddleware',  # User access control middleware
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

SITE_ID = 1

AUTHENTICATION_BACKENDS = (
    'django.contrib.auth.backends.ModelBackend',  # Django'nun varsayılan backend'i
    'allauth.account.auth_backends.AuthenticationBackend',  # Allauth backend'i
)

ROOT_URLCONF = 'judicial_platform.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],  # Global templates klasörü
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'core.context_processors.trial_status',  # Trial durumu
            ],
        },
    },
]

WSGI_APPLICATION = 'judicial_platform.wsgi.application'

# Yerel geliştirme için SQLite kullan, production için PostgreSQL
if DEBUG:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': BASE_DIR / 'db.sqlite3',
        }
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.postgresql',
            'NAME': 'yargi_veri_tabani',
            'USER': 'hasankaradeniz',
            'PASSWORD': 'judicial2024',
            'HOST': '145.223.82.130',
            'PORT': '5432',
        }
    }

# Şifre doğrulama vs. (varsayılan ayarlar)
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    # Diğer doğrulayıcılar...
]

# Cache ayarları
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
        'LOCATION': 'judicial-platform-cache',
        'TIMEOUT': 1800,  # 30 dakika
        'OPTIONS': {
            'MAX_ENTRIES': 1000,
        }
    }
}

LANGUAGE_CODE = 'tr' 
TIME_ZONE = 'Europe/Istanbul'
USE_I18N = True
USE_L10N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [
    BASE_DIR / "static",
]
STATIC_ROOT = BASE_DIR / "staticfiles"

# Medya dosyaları için ayarlar
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Google API için ayarlar (Google Custom Search API)
GOOGLE_API_KEY = 'AIzaSyCpozKuhViWV809M7AmQ7Hi7LKbiAjdtCk'
GOOGLE_CSE_ID = '347c206ed96464b79'
GEMINI_API_KEY = 'AIzaSyC68qVtPz658HoQEl0v5l-_AAtrbeEPDOE'


LOGIN_REDIRECT_URL = '/profile/'
LOGOUT_REDIRECT_URL = 'home'

LOGIN_URL = '/login/'

# Allauth ayarları
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_EMAIL_VERIFICATION = "none"
ACCOUNT_LOGIN_REDIRECT_URL = '/profile/'
ACCOUNT_LOGOUT_REDIRECT_URL = '/login/'
ACCOUNT_LOGOUT_ON_GET = True  # Doğrudan logout, confirmation sayfası yok

# Parola değişikliği ayarları - Django varsayılan davranışı
# Parola değiştirildikten sonra login sayfasına yönlendirme (güvenlik için logout)

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'lexatech.ai@gmail.com'
EMAIL_HOST_PASSWORD = 'rvxw asrp ulib pwdg'
DEFAULT_FROM_EMAIL = 'lexatech.ai@gmail.com'
SERVER_EMAIL = 'lexatech.ai@gmail.com'

# Logging ayarları
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {message}',
            'style': '{',
        },
    },
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'loggers': {
        'core': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'WARNING',
    },
}

# Param Sanal Pos Ayarları
PARAM_CLIENT_CODE = '145942'
PARAM_CLIENT_USERNAME = 'TP10173244'
PARAM_CLIENT_PASSWORD = 'E78A466F0083A439'
PARAM_GUID = 'E204D733-02BA-4312-B03F-84BFE184313C'
PARAM_TEST_URL = 'https://dev.param.com.tr'
PARAM_PRODUCTION_URL = 'https://pos.param.com.tr'

# Test ortamı için True, production için False
PARAM_TEST_MODE = False

# CELERY AYARLARI
CELERY_BROKER_URL = 'redis://localhost:6379/0'  # Redis broker
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = 'Europe/Istanbul'
CELERY_ENABLE_UTC = True

# Task routing
CELERY_TASK_ROUTES = {
    'core.tasks.update_faiss_index': {'queue': 'faiss'},
    'core.tasks.rebuild_faiss_index_full': {'queue': 'faiss'},
    'core.tasks.optimize_faiss_index': {'queue': 'faiss'},
    'core.tasks.check_index_health': {'queue': 'monitoring'},
    'core.tasks.warm_application_cache': {'queue': 'cache'},
}

# Task limits
CELERY_TASK_TIME_LIMIT = 30 * 60  # 30 dakika
CELERY_TASK_SOFT_TIME_LIMIT = 25 * 60  # 25 dakika
CELERY_WORKER_MAX_TASKS_PER_CHILD = 1000

# FAISS Index ayarları
FAISS_INDEX_PATH = os.path.join(BASE_DIR, 'faiss_dizinleri')
ADMIN_EMAIL = 'lexatech.ai@gmail.com'