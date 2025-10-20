from django.apps import AppConfig


class CoreConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'vejoias.core'
    label = 'core' # Define um label para evitar conflitos de nomes
