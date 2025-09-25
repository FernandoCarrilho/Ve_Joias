from django.apps import AppConfig


class InfrastructureConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'vejoias.infrastructure'
    label = 'infrastructure' # Define um label para evitar conflitos de nomes
