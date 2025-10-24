from django.apps import AppConfig

class CarrinhoConfig(AppConfig):
    # O caminho completo para o módulo
    name = 'vejoias.carrinho'
    label = 'carrinho' 
    verbose_name = 'Carrinho de Compras'
    default_auto_field = 'django.db.models.BigAutoField'
