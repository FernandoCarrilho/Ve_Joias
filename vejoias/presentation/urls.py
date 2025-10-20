# vejoias/presentation/urls.py

from django.urls import path
from .views import (
    # Vistas de Catálogo e Compra (Cliente)
    ListaJoiasView,
    DetalheJoiaView,
    CarrinhoView,
    CheckoutView,
    ProcessarCheckoutView, # Endpoint POST para finalizar compra
    DetalhePedidoClienteView,
    
    # Vistas de Autenticação
    LoginView,
    RegistroView,
    LogoutView,
    RecuperarSenhaView,
    
    # Vistas de Perfil do Cliente
    PerfilView,
    HistoricoPedidosView,
    EditarPerfilView,
    AlterarSenhaView,
    
    # Vistas Administrativas
    DashboardAdminView,
    GerenciarPedidosView,
    DetalhePedidoAdminView,
    GerenciarJoiasView,
    DetalheJoiaAdminView, # Usada para Adicionar e Editar
    DeletarJoiaView, # Para o endpoint de exclusão
    GerenciarUsuariosView,
)

urlpatterns = [
    # 1. Rotas de Catálogo e Home
    path('', ListaJoiasView.as_view(), name='lista_joias'),
    path('joia/<int:joia_id>/', DetalheJoiaView.as_view(), name='detalhe_joia'),

    # 2. Rotas de Compra
    path('carrinho/', CarrinhoView.as_view(), name='carrinho'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('processar-checkout/', ProcessarCheckoutView.as_view(), name='processar_checkout'), # Ação POST
    path('pedido/<int:pedido_id>/', DetalhePedidoClienteView.as_view(), name='detalhe_pedido'),

    # 3. Rotas de Autenticação
    path('login/', LoginView.as_view(), name='login'),
    path('registro/', RegistroView.as_view(), name='registro'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('recuperar-senha/', RecuperarSenhaView.as_view(), name='recuperar_senha'),

    # 4. Rotas de Perfil (Área do Cliente)
    path('perfil/', PerfilView.as_view(), name='perfil'),
    path('perfil/historico/', HistoricoPedidosView.as_view(), name='historico_pedidos'),
    path('perfil/editar/', EditarPerfilView.as_view(), name='editar_perfil'),
    path('perfil/alterar-senha/', AlterarSenhaView.as_view(), name='alterar_senha'),

    # 5. Rotas Administrativas
    path('admin/dashboard/', DashboardAdminView.as_view(), name='dashboard'),
    
    # Gerenciamento de Pedidos (Admin)
    path('admin/pedidos/', GerenciarPedidosView.as_view(), name='gerenciar_pedidos'),
    path('admin/pedido/<int:pedido_id>/', DetalhePedidoAdminView.as_view(), name='detalhe_pedido'),

    # Gerenciamento de Joias (Admin)
    path('admin/joias/', GerenciarJoiasView.as_view(), name='gerenciar_joias'),
    path('admin/joias/adicionar/', DetalheJoiaAdminView.as_view(), name='admin_adicionar_joia'),
    path('admin/joias/editar/<int:joia_id>/', DetalheJoiaAdminView.as_view(), name='admin_editar_joia'),
    path('admin/joias/deletar/<int:joia_id>/', DeletarJoiaView.as_view(), name='admin_deletar_joia'),
    
    # Gerenciamento de Usuários (Admin)
    path('admin/usuarios/', GerenciarUsuariosView.as_view(), name='gerenciar_usuarios'),
]
