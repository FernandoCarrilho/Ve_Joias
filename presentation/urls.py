# vejoias/presentation/urls.py

from django.urls import path
from . import views

urlpatterns = [
    # Página inicial (listagem de joias)
    path('', views.lista_joias, name='lista_joias'),
    
    # Detalhes de uma joia específica (ex: /joias/1/)
    path('joias/<int:joia_id>/', views.detalhe_joia, name='detalhe_joia'),
    
    # Módulo do Carrinho
    path('carrinho/', views.ver_carrinho, name='ver_carrinho'),
    path('carrinho/adicionar/', views.adicionar_ao_carrinho, name='adicionar_ao_carrinho'),
    path('carrinho/remover/', views.remover_do_carrinho, name='remover_do_carrinho'),
    
    # Módulo de Checkout
    path('checkout/', views.processar_checkout, name='processar_checkout'),
    
    # Módulo de Perfil do Usuário
    path('meu-perfil/', views.meu_perfil, name='meu_perfil'),
]
