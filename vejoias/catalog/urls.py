# vejoias/catalog/urls.py
from django.urls import path
from . import views

urlpatterns = [
    # ====================================================================
    # ROTAS PÚBLICAS DO CATÁLOGO
    # ====================================================================
    path('', views.CatalogoView.as_view(), name='catalogo'),
    path('joia/<int:pk>/', views.DetalheJoiaView.as_view(), name='detalhe_joia'),

    # ====================================================================
    # ROTAS DE ADMINISTRAÇÃO - JOIAS (CRUD)
    # ====================================================================
    # Listar Joias (Admin)
    path('admin/joias/', views.AdminJoiaListView.as_view(), name='admin_joia_list'),
    
    # Criar Nova Joia
    path('admin/joias/adicionar/', views.AdminJoiaCreateUpdateView.as_view(), name='admin_adicionar_joia'),
    
    # Editar Joia (PK é o ID da joia)
    path('admin/joias/editar/<int:pk>/', views.AdminJoiaCreateUpdateView.as_view(), name='admin_editar_joia'),
    
    # Deletar Joia
    path('admin/joias/deletar/<int:pk>/', views.AdminJoiaDeleteView.as_view(), name='admin_deletar_joia'),
    
    # ====================================================================
    # ROTAS DE ADMINISTRAÇÃO - CATEGORIAS (CRUD)
    # ====================================================================
    # Listar Categorias (Admin)
    path('admin/categorias/', views.AdminCategoriaListView.as_view(), name='admin_categoria_list'),
    
    # Criar Nova Categoria
    path('admin/categorias/adicionar/', views.AdminCategoriaCreateView.as_view(), name='admin_adicionar_categoria'),
    
    # Editar Categoria
    path('admin/categorias/editar/<int:pk>/', views.AdminCategoriaUpdateView.as_view(), name='admin_editar_categoria'),
    
    # Deletar Categoria
    path('admin/categorias/deletar/<int:pk>/', views.AdminCategoriaDeleteView.as_view(), name='admin_deletar_categoria'),
]
