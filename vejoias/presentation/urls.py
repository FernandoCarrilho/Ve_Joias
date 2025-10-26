"""
Define as URLs para a camada de apresentação (o frontend da loja) e as rotas de API REST.
Inclui rotas de catálogo, carrinho, autenticação, perfil de cliente e painel administrativo,
utilizando Views baseadas em classes (CBVs) para o frontend.
"""
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views, views_auth, views_admin

# Configuração do Router para ViewSets (API REST)
router = DefaultRouter()
# Mantido o JoiaViewSet para a API de catálogo
router.register(r'joias', views.JoiaViewSet)


urlpatterns = [
    # ====================================================================
    # 1. ROTAS DE CATÁLOGO (LOJA)
    # ====================================================================
    path('', views.HomeView.as_view(), name='home'),  # Home Page
    path('catalogo/', views.ListaJoiasView.as_view(), name='lista_joias'),  # Lista de todas as Joias
    path('catalogo/<slug:slug>/', views.ListaJoiasPorCategoriaView.as_view(), name='lista_por_categoria'),  # Lista por Categoria
    path('joia/<int:pk>/', views.DetalheJoiaView.as_view(), name='detalhe_joia'),  # Detalhes da Joia (usando pk)

    # ====================================================================
    # 2. ROTAS DE COMPRA (CARRINHO E CHECKOUT)
    # ====================================================================
    path('carrinho/', views.CarrinhoView.as_view(), name='carrinho'),
    path('carrinho/adicionar/<int:joia_id>/', views.adicionar_ao_carrinho, name='adicionar_carrinho'),
    path('carrinho/remover/<int:joia_id>/', views.remover_do_carrinho, name='remover_carrinho'),
    path('checkout/', views.ProcessarCheckoutView.as_view(), name='checkout'),
    path('processar-checkout/', views.ProcessarCheckoutView.as_view(), name='processar_checkout'),
    path('pedido/<int:pk>/', views.DetalhePedidoView.as_view(), name='detalhe_pedido'),

    # ====================================================================
    # 3. ROTAS DE AUTENTICAÇÃO
    # ====================================================================
    path('login/', views_auth.LoginView.as_view(), name='login'),
    path('cadastro/', views_auth.CadastroUsuarioView.as_view(), name='cadastro'),
    path('logout/', views_auth.logout_usuario, name='logout'),

    # ====================================================================
    # 4. ROTAS DE PERFIL (ÁREA DO CLIENTE)
    # ====================================================================
    path('minha-conta/', views.UsuarioView.as_view(), name='perfil_usuario'),
    path('minha-conta/editar/', views.EditarPerfilView.as_view(), name='editar_perfil'),
    path('minha-conta/senha/', views.AlterarSenhaView.as_view(), name='alterar_senha'),
    path('meus-pedidos/', views.HistoricoPedidosView.as_view(), name='historico_pedidos'),

    # ====================================================================
    # 5. ROTAS ADMINISTRATIVAS
    # ====================================================================
    # CORREÇÃO CRÍTICA: Renomeado de 'dashboard_admin' para 'admin_dashboard'
    # para resolver o erro NoReverseMatch na interface administrativa.
    path('admin/dashboard/', views_admin.DashboardAdminView.as_view(), name='admin_dashboard'),
    
    # Gerenciamento de Pedidos (Admin)
    path('admin/pedidos/', views_admin.GerenciarPedidosView.as_view(), name='gerenciar_pedidos'),
    path('admin/pedido/<int:pk>/', views_admin.DetalhePedidoAdminView.as_view(), name='admin_detalhe_pedido'),
    path('admin/pedido/status/<int:pk>/', views_admin.AtualizarStatusPedidoView.as_view(), name='admin_atualizar_status'),
    
    # Gerenciamento de Joias (Admin)
    path('admin/joias/', views_admin.GerenciarJoiasView.as_view(), name='gerenciar_joias'),
    path('admin/joias/adicionar/', views_admin.AdicionarJoiaView.as_view(), name='admin_adicionar_joia'),
    path('admin/joias/editar/<int:pk>/', views_admin.EditarJoiaView.as_view(), name='admin_editar_joia'),
    path('admin/joias/deletar/<int:pk>/', views_admin.DeletarJoiaView.as_view(), name='admin_deletar_joia'),
    
    # Gerenciamento de Usuários (Admin)
    path('admin/usuarios/', views_admin.GerenciarUsuariosView.as_view(), name='gerenciar_usuarios'),

    # ====================================================================
    # 6. ROTAS DE API (Django REST Framework)
    # ====================================================================
    path('api/', include(router.urls)),  # Rotas do JoiaViewSet (/api/joias/)
    path('api/carrinho/', views.CarrinhoAPIView.as_view(), name='api_carrinho'),
    path('api/checkout/', views.CheckoutAPIView.as_view(), name='api_checkout'),
    
    # Webhook do Mercado Pago (Rota externa, não requer autenticação)
    path('api/webhook/mercadopago/', views.WebhookMercadoPago.as_view(), name='webhook_mercadopago'),
]
