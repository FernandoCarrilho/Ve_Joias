from django.apps import AppConfig

class PedidosConfig(AppConfig):
    # O caminho completo para o módulo
    name = 'vejoias.pedidos'
    label = 'pedidos' 
    verbose_name = 'Gerenciamento de Pedidos'
    default_auto_field = 'django.db.models.BigAutoField'
