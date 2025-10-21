# vejoias/core/apps.py

from django.apps import AppConfig

class CoreConfig(AppConfig):
    # O nome completo do path da aplicação
    name = 'vejoias.core'
    # Define o label curto para referência (ex: no shell ou migrações)
    label = 'core'
    # Nome amigável que pode ser exibido no Admin, se necessário
    verbose_name = 'Camada de Entidades e Lógica (Core)'
    
    # Define que as migrações não serão criadas nesta camada, 
    # pois ela não deve ter modelos de banco de dados (Infrastructure que cuida disso).
    # Esta é uma boa prática em arquitetura limpa.
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        # Aqui, poderíamos colocar lógica de inicialização, se necessário.
        pass
