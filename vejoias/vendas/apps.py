from django.apps import AppConfig

class VendasConfig(AppConfig):
    # O nome da app_name deve ser o caminho Python completo para o seu módulo.
    # Se o nome do projeto principal for 'vejoias' e o app for 'vendas',
    # o caminho é 'vejoias.vendas'.
    name = 'vejoias.vendas'
    
    # O 'label' é um rótulo curto para a aplicação, se for omitido, o nome do diretório é usado.
    # Recomendado:
    label = 'vendas' 

    # Nome amigável que será exibido no admin (opcional)
    verbose_name = 'Vendas e Pedidos'

    # Se você está no Django 4.0+ é recomendável definir default_auto_field
    default_auto_field = 'django.db.models.BigAutoField'
