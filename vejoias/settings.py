"""
Configurações para o projeto Vê Jóias.
"""

import os
import sys
from decouple import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

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

# Define o nosso modelo de usuário personalizado como o modelo de autenticação padrão.
AUTH_USER_MODEL = 'infrastructure.Usuario'


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
    
    # Aplicações de Terceiros (Primeiro)
    'rest_framework', 
    'drf_spectacular',
    'rest_framework_simplejwt', 
    
    # Nossas Aplicações (Por último)
    # A sintaxe de importação é a correta, o problema é a ordem.
    'vejoias.infrastructure.apps.InfrastructureConfig',
    'vejoias.presentation.apps.PresentationConfig', 
    'vejoias.core.apps.CoreConfig',
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
        'NAME': os.environ.get('POSTGRES_DB'),
        'USER': os.environ.get('POSTGRES_USER'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD'),
        'HOST': os.environ.get('POSTGRES_HOST'),
        'PORT': int(os.environ.get('POSTGRES_PORT')),
    }
}


# ====================================================================
# AUTENTICAÇÃO E VALIDAÇÃO DE SENHA
# ====================================================================



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
# CONFIGURAÇÕES DE SERVIÇOS EXTERNOS (Evolution-API/WhatsApp)
# ====================================================================
# Evolution-API (WhatsApp Gateway)
EVOLUTION_API_URL = os.environ.get('EVOLUTION_API_URL', 'http://evolution_api:8080/v1')
EVOLUTION_API_KEY = os.environ.get('EVOLUTION_API_KEY')
EVOLUTION_API_INSTANCE = os.environ.get('EVOLUTION_API_INSTANCE', 'default')
EVOLUTION_INSTANCE_NAME = config('EVOLUTION_INSTANCE_NAME', default='TEMP_INSTANCE_NAME')
# O Evolution-API geralmente usa a porta 8080, e 'evolution_api' é o nome do serviço Docker.

# ====================================================================
# CONFIGURAÇÕES DE E-MAIL
# ====================================================================
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Credenciais SMTP
EMAIL_HOST = os.environ.get('EMAIL_HOST') # Ex: smtp.gmail.com
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587))
# Lê 'True' ou 'False' (case insensitive) do .env
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true' 
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@vejoias.com')


# ====================================================================
# ARQUIVOS ESTÁTICOS (CSS, JavaScript, Imagens)
# ====================================================================

STATIC_URL = '/static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')


# Default primary key field type
# https://docs.djangoproject.com/en/5.0/ref/settings/#default-auto-field
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

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

# ====================================================================
# CONFIGURAÇÕES DE E-MAIL (PRODUÇÃO)
# ====================================================================
# Mude para SMTPBackend em produção para enviar e-mails reais
EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'django.core.mail.backends.smtp.EmailBackend') 
# Se você quiser o console backend em dev e SMTP em prod, use a linha acima e defina a variável no .env/.prod

EMAIL_HOST = os.environ.get('EMAIL_HOST') # Ex: smtp.gmail.com ou smtp.sendgrid.net
EMAIL_PORT = int(os.environ.get('EMAIL_PORT', 587)) # 587 para TLS/STARTTLS ou 465 para SSL
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'True').lower() == 'true'
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'noreply@vejoias.com')
# Define o caminho para a sua view de login personalizada.
# O Django agora saberá para onde redirecionar quando um login for necessário.
LOGIN_URL = '/login/'

# Adicionalmente, você pode definir para onde o usuário deve ir após um login bem-sucedido
# (Opcional: se não for definido, ele usará a página padrão /accounts/profile/)
LOGIN_REDIRECT_URL = '/'

# ====================================================================
# CONFIGURAÇÕES DE LOGGING (PRODUÇÃO)
# ====================================================================
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'WARNING',  # Registra a partir de WARNING
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': '/var/log/vejoias/django.log', # Mude este caminho para o seu ambiente
            'maxBytes': 1024 * 1024 * 5, # 5 MB
            'backupCount': 5,
            'formatter': 'verbose',
        },
    },
    'formatters': {
        'verbose': {
            'format': '{levelname} {asctime} {module} {process:d} {thread:d} {message}',
            'style': '{',
        },
    },
    'loggers': {
        'django': {
            'handlers': ['file'],
            'level': 'WARNING',
            'propagate': True,
        },
        'vejoias.core': { # Logs da sua lógica de negócio
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# Se estiver em DEBUG=False e o host for permitido, o Django usará este LOGGING.
