from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'vejoias.catalog' # ESTE é o caminho que deve ser resolvível
    verbose_name = 'Catálogo de Jóias'
