from django.apps import AppConfig


class PresentationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'vejoias.presentation'
    label = 'presentation' # Define um label para evitar conflitos de nomes
