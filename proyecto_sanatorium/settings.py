"""
Django settings for proyecto_sanatorium project.

Generated by 'django-admin startproject' using Django 5.1.4.

For more information on this file, see
https://docs.djangoproject.com/en/5.1/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.1/ref/settings/
"""

from pathlib import Path

import dj_database_url

from decouple import config

import os

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/5.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config("DEBUG", cast=bool)

ALLOWED_HOSTS = config("ALLOWED_HOSTS").split(",")  

"""

REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # Permitir acceso a todos los usuarios
    ]
}
"""

#Esto es para que sea opcional los / al final de los endpoints
APPEND_SLASH = True


#Estos 2 son para swagger
#1 Configura REST_FRAMEWORK
REST_FRAMEWORK = {
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',  # Permitir acceso a todos los usuarios REVISAR
    ]
}



#2 Configuración de Spectacular
SPECTACULAR_SETTINGS = {
    'TITLE': 'Sanatorium API',
    'DESCRIPTION': 'API para gestión de proyectos y tareas',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
    # Configuraciones adicionales para mejorar la documentación automática
    'COMPONENT_SPLIT_REQUEST': True,
    'SCHEMA_PATH_PREFIX': '/api/',
    'SCHEMA_COERCE_PATH_PK_SUFFIX': True,
}


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'gestion', 
    'rest_framework',
    'django_extensions',
    'drf_spectacular', # para swagger
    'corsheaders', # para cors

]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'corsheaders.middleware.CorsMiddleware',  # Para Cors
    'whitenoise.middleware.WhiteNoiseMiddleware',  # WhiteNoise middleware
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'proyecto_sanatorium.urls'

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

WSGI_APPLICATION = 'proyecto_sanatorium.wsgi.application'


# Database
# https://docs.djangoproject.com/en/5.1/ref/settings/#databases

#Data base sql lite
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

#Data base postgres
# pip install psycopg2
DATABASES["default"] = dj_database_url.parse(config("DATABASE_URL"))

# Password validation
# https://docs.djangoproject.com/en/5.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
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


# Internationalization
# https://docs.djangoproject.com/en/5.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/5.1/howto/static-files/

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles') # para white noise

# Configuración específica de WhiteNoise
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# Directorios adicionales donde Django buscará archivos estáticos white noise
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, 'static'),
]

# Default primary key field type
# https://docs.djangoproject.com/en/5.1/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'



#--------Configuración de CORS--------------- 

# Configuraciones adicionales de CORS
CORS_ALLOW_CREDENTIALS = True  # Si necesitas enviar cookies
CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]

CORS_ALLOW_HEADERS = [
    'accept',
    'accept-encoding',
    'authorization',
    'content-type',
    'dnt',
    'origin',
    'user-agent',
    'x-csrftoken',
    'x-requested-with',
]

# Verifica que los orígenes incluyan tu frontend de producción
"""  
CORS_ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://backend-sanatorium-business.onrender.com",
    "https://sanatorium-business.onrender.com"  # Agrega tu frontend de producción
]
"""
# También puedes agregar CSRF_TRUSTED_ORIGINS
CSRF_TRUSTED_ORIGINS = [
    "https://backend-sanatorium-business.onrender.com",
    "https://sanatorium-business.onrender.com",
    "http://localhost:3000",
    "http://localhost:5173"
]

CORS_ALLOW_ALL_ORIGINS = True