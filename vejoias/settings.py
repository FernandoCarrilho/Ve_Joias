"""
Configurações para o projeto Vê Jóias.
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Carrega as variáveis de ambiente do arquivo .env
load_dotenv()

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ====================================================================
# CONFIGURAÇÕES BÁSICAS
# ====================================================================

# A SECRET_KEY deve ser lida de uma variável de ambiente por segurança.
SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-default-key-for-development')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', 'localhost').split(',')


# ====================================================================
# APLICAÇÕES INSTALADAS
# ====================================================================

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    
    'vejoias.infrastructure',
    'vejoias.presentation',
    'vejoias.core',
    'rest_framework', 
    'drf_spectacular',
    'rest_framework_simplejwt', # Adiciona o Django REST Framework

    
    # Nossas aplicações
    'vejoias.infrastructure.apps.InfrastructureConfig', # Adiciona nossa app
]


# ====================================================================
# MIDDLEWARE E TEMPLATES
# ====================================================================

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'vejoias.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'vejoias/presentation/templates')],
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

WSGI_APPLICATION = 'vejoias.wsgi.application'


# ====================================================================
# CONFIGURAÇÃO DO BANCO DE DADOS
# ====================================================================

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('DB_NAME'),
        'USER': os.environ.get('DB_USER'),
        'HOST': os.environ.get('DB_HOST', 'db'), # O host é 'db' para o Docker Compose
        'PORT': os.environ.get('DB_PORT', '5432'),
        'PASSWORD': os.environ.get('DB_PASSWORD'),
    }
}


# ====================================================================
# AUTENTICAÇÃO E VALIDAÇÃO DE SENHA
# ====================================================================

# Define o nosso modelo de usuário personalizado como o modelo de autenticação padrão.
AUTH_USER_MODEL = 'infrastructure.Usuario'

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


# ====================================================================
# INTERNACIONALIZAÇÃO
# ====================================================================

LANGUAGE_CODE = 'pt-br'

TIME_ZONE = 'America/Sao_Paulo'

USE_I18N = True

USE_TZ = True


# ====================================================================
# ARQUIVOS ESTÁTICOS (CSS, JavaScript, Imagens)
# ====================================================================

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ====================================================================
# CONFIGURAÇÕES DE E-MAIL
# ====================================================================
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

SPECTACULAR_SETTINGS = {
    'TITLE': 'API do Vê Joias',
    'DESCRIPTION': 'Documentação completa da API de e-commerce da Vê Joias.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    )
}

# Configurações de E-mail (Modo de Desenvolvimento)
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
