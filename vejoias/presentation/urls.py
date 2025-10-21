# vejoias/presentation/urls.py
"""
Define as URLs para a camada de apresentação (o frontend da loja).
Inclui rotas de catálogo, carrinho, autenticação, perfil de cliente e painel administrativo.
"""
from django.urls import path
from .views import (
    # Vistas de Catálogo e Home
    HomeView, # Adicionado HomeView
    ListaJoiasView,
    ListaJoiasPorCategoriaView, # Rota de listagem por Slug
    DetalheJoiaView,
    
    # Vistas de Carrinho e Checkout (Cliente)
    CarrinhoView,
    adicionar_ao_carrinho, # Função para adicionar
    remover_do_carrinho, # Função para remover
    CheckoutView,
    ProcessarCheckoutView, # Endpoint POST para finalizar compra
    
    # Vistas de Autenticação Customizadas
    LoginView,
    CadastroUsuarioView, # Renomeado para seguir o nome do arquivo apps.py
    # LogoutView é o padrão do Django, mas podemos usar o customizado se existir
    # RecuperarSenhaView (o fluxo já está no urls.py principal)
    
    # Vistas de Perfil do Cliente
    PerfilUsuarioView, # Renomeado para seguir o nome do arquivo apps.py
    MeusPedidosView,
    DetalhePedidoView,
    
    # Vistas Administrativas
    DashboardAdminView,
    GerenciarPedidosView,
    DetalhePedidoAdminView,
    AtualizarStatusPedidoView, # Rota para atualizar status de pedido (POST)
    GerenciarJoiasView,
    AdicionarJoiaView, # Para o endpoint de adicionar
    EditarJoiaView, # Para o endpoint de editar
    DeletarJoiaView, # Para o endpoint de exclusão
    GerenciarUsuariosView, # Novo para gestão de usuários
)

urlpatterns = [
    # ====================================================================
    # 1. ROTAS DE CATÁLOGO (LOJA)
    # ====================================================================
    path('', HomeView.as_view(), name='home'), # Home Page
    path('catalogo/', ListaJoiasView.as_view(), name='lista_joias'), # Lista de todas as Joias
    path('catalogo/<slug:slug>/', ListaJoiasPorCategoriaView.as_view(), name='lista_por_categoria'), # Lista por Categoria
    path('joia/<int:pk>/', DetalheJoiaView.as_view(), name='detalhe_joia'), # Detalhes da Joia (mudança de joia_id para pk)

    # ====================================================================
    # 2. ROTAS DE COMPRA (CARRINHO E CHECKOUT)
    # ====================================================================
    path('carrinho/', CarrinhoView.as_view(), name='carrinho'),
    path('carrinho/adicionar/<int:joia_id>/', adicionar_ao_carrinho, name='adicionar_carrinho'),
    path('carrinho/remover/<int:joia_id>/', remover_do_carrinho, name='remover_carrinho'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('processar-checkout/', ProcessarCheckoutView.as_view(), name='processar_checkout'), # Ação POST para finalizar compra

    # ====================================================================
    # 3. ROTAS DE AUTENTICAÇÃO
    # ====================================================================
    # Login e Cadastro/Registro
    path('login/', LoginView.as_view(), name='login'),
    path('cadastro/', CadastroUsuarioView.as_view(), name='cadastro'),
    # Logout utiliza o padrão do Django definido no urls.py principal
    # Recuperação de senha também é tratada no urls.py principal
    
    # ====================================================================
    # 4. ROTAS DE PERFIL (ÁREA DO CLIENTE)
    # ====================================================================
    path('minha-conta/', PerfilUsuarioView.as_view(), name='perfil_usuario'),
    path('meus-pedidos/', MeusPedidosView.as_view(), name='meus_pedidos'),
    path('pedido/<int:pk>/', DetalhePedidoView.as_view(), name='detalhe_pedido'), # Detalhe do Pedido do Cliente

    # ====================================================================
    # 5. ROTAS ADMINISTRATIVAS
    # ====================================================================
    path('admin/dashboard/', DashboardAdminView.as_view(), name='dashboard_admin'),
    
    # Gerenciamento de Pedidos (Admin)
    path('admin/pedidos/', GerenciarPedidosView.as_view(), name='gerenciar_pedidos'),
    path('admin/pedido/<int:pk>/', DetalhePedidoAdminView.as_view(), name='admin_detalhe_pedido'),
    path('admin/pedido/status/<int:pk>/', AtualizarStatusPedidoView.as_view(), name='admin_atualizar_status'),
    
    # Gerenciamento de Joias (Admin)
    path('admin/joias/', GerenciarJoiasView.as_view(), name='gerenciar_joias'),
    path('admin/joias/adicionar/', AdicionarJoiaView.as_view(), name='admin_adicionar_joia'),
    path('admin/joias/editar/<int:pk>/', EditarJoiaView.as_view(), name='admin_editar_joia'),
    path('admin/joias/deletar/<int:pk>/', DeletarJoiaView.as_view(), name='admin_deletar_joia'),
    
    # Gerenciamento de Usuários (Admin)
    path('admin/usuarios/', GerenciarUsuariosView.as_view(), name='gerenciar_usuarios'),
]
