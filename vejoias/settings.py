"""
Configurações para o projeto Vê Jóias.
"""

import os
import sys
from decouple import config, Csv
from pathlib import Path
from django.contrib.messages import constants as messages

# Garante que o diretório raiz do projeto esteja no path para imports relativos
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# ====================================================================
# CONFIGURAÇÕES BÁSICAS
# ====================================================================

# A SECRET_KEY deve ser lida de uma variável de ambiente por segurança.
SECRET_KEY = config('SECRET_KEY', default='django-insecure-default-key-for-development')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=False, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost', cast=Csv())

# Define o nosso modelo de usuário personalizado como o modelo de autenticação padrão.
# Isso requer que o 'infrastructure' app seja listado primeiro em INSTALLED_APPS.
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
    
    # Nossas Aplicações (Nessa ordem para referências de Models)
    'vejoias.core.apps.CoreConfig', # Entidades e Lógica Pura
    'vejoias.infrastructure.apps.InfrastructureConfig', # Models e Repositório
    'vejoias.presentation.apps.PresentationConfig', # Views, Forms, Templates
    'vejoias.catalog.apps.CatalogConfig', # Catálogo de Produtos
    'vejoias.carrinho.apps.CarrinhoConfig', # Carrinho de Compras
    'vejoias.pedidos.apps.PedidosConfig', # Pedidos
    'vejoias.vendas.apps.VendasConfig', # Vendas
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
        # Usando Path para compatibilidade com o resto do arquivo
        'DIRS': [BASE_DIR / 'vejoias' / 'presentation' / 'templates'], 
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                
                # ADICIONADO: Context Processor para o Carrinho
                'vejoias.presentation.context_processors.carrinho_context', 
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
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
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

# Configurações de Autenticação
LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/'


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

# Arquivos de mídia (uploads de usuário)
MEDIA_URL = '/media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')


# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'


# ====================================================================
# CONFIGURAÇÕES DO DJANGO REST FRAMEWORK (DRF) E DOCS (SPECTACULAR)
# ====================================================================

SPECTACULAR_SETTINGS = {
    'TITLE': 'API do Vê Jóias',
    'DESCRIPTION': 'Documentação completa da API de e-commerce da Vê Jóias.',
    'VERSION': '1.0.0',
    'SERVE_INCLUDE_SCHEMA': False,
}

REST_FRAMEWORK = {
    # JWT é a autenticação primária para API, SessionAuth para o Admin e Views tradicionais.
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}


# ====================================================================
# CONFIGURAÇÕES DE SERVIÇOS EXTERNOS (WhatsApp, E-mail e Logging)
# ====================================================================

# Evolution-API (WhatsApp Gateway)
EVOLUTION_API_URL = config('EVOLUTION_API_URL', default='http://evolution_api:8080/v1')
EVOLUTION_API_KEY = config('EVOLUTION_API_KEY')
EVOLUTION_API_INSTANCE = config('EVOLUTION_API_INSTANCE', default='default')
EVOLUTION_INSTANCE_NAME = config('EVOLUTION_INSTANCE_NAME', default='TEMP_INSTANCE_NAME')


# Configurações de E-mail
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.smtp.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = config('DEFAULT_FROM_EMAIL', default='noreply@vejoias.com')


# Configurações de Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': config('LOG_LEVEL', default='WARNING'),
            'class': 'logging.handlers.RotatingFileHandler',
            'filename': config('LOG_FILE', default=str(BASE_DIR / 'logs' / 'django.log')),
            'maxBytes': 1024 * 1024 * 5,  # 5 MB
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
        'vejoias.core': { 
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}

# --- Configurações de Mensagens (Estilo Tailwind) ---
MESSAGE_TAGS = {
    messages.DEBUG: 'bg-gray-800 text-white',
    messages.INFO: 'bg-blue-500 text-white',
    messages.SUCCESS: 'bg-green-500 text-white',
    messages.WARNING: 'bg-yellow-500 text-white',
    messages.ERROR: 'bg-red-500 text-white',
}
