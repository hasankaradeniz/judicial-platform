import os
from pathlib import Path

# BASE_DIR tanımlaması (Django 3.1+)
BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'your-secret-key'
DEBUG = True
ALLOWED_HOSTS = ['127.0.0.1', 'localhost', 'testserver']

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
    'allauth.account.middleware.AccountMiddleware',  # Bunu ekleyin!
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
            ],
        },
    },
]

WSGI_APPLICATION = 'judicial_platform.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'yargi_veri_tabani',         # Oluşturduğunuz veritabanı adı
        'USER': 'hasankaradeniz',             # Oluşturduğunuz kullanıcı adı
        'PASSWORD': '07072010Dd*',     # Belirlediğiniz şifre
        'HOST': '145.223.82.130',          # veya 'localhost'
        'PORT': '5432',               # PostgreSQL'in varsayılan portu
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

# Medya dosyaları için ayarlar
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Google API için ayarlar (Google Custom Search API)
GOOGLE_API_KEY = 'AIzaSyCpozKuhViWV809M7AmQ7Hi7LKbiAjdtCk'
GOOGLE_CSE_ID = '347c206ed96464b79'
GEMINI_API_KEY = 'AIzaSyAypqssQUAjg5fYeXskdZqJtPEktEHoSco'


LOGIN_REDIRECT_URL = 'home'

LOGIN_URL = '/login/'

EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.gmail.com'  # Kendi SMTP sağlayıcını buraya gir
EMAIL_PORT = 587
EMAIL_USE_TLS = True
EMAIL_HOST_USER = 'hasankaradeniz@gmail.com'  # Kendi e-mail adresin
EMAIL_HOST_PASSWORD = 'odvp dvtc eskx ikgl'  # E-posta şifren

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