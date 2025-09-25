# vejoias/urls.py

from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    # Inclui as URLs da sua aplicação de apresentação (o e-commerce)
    path('', include('vejoias.presentation.urls')),
    
    # URL para o painel de administração padrão do Django
    path('admin/', admin.site.urls),
]
