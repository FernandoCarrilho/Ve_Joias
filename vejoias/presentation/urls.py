from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from . import views
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView


# Cria o roteador e registra o nosso ViewSet
router = DefaultRouter()
router.register(r'joias', views.JoiaViewSet)

urlpatterns = [
    # URLs do E-commerce
    path('', views.lista_joias, name='lista_joias'),
    path('joia/<str:joia_id>/', views.detalhe_joia, name='detalhe_joia'),
    path('adicionar-ao-carrinho/', views.adicionar_ao_carrinho, name='adicionar_ao_carrinho'),
    path('carrinho/', views.ver_carrinho, name='ver_carrinho'),
    path('checkout/', views.processar_checkout, name='processar_checkout'),
    path('perfil/', views.meu_perfil, name='meu_perfil'),

    # Rota para os detalhes do pedido
    path('pedido/<int:pedido_id>/', views.detalhe_pedido, name='detalhe_pedido'),

    
    # URLs de Autenticação
    path('registro/', views.registro, name='registro'),
    path('login/', views.login_usuario, name='login'),
    path('logout/', views.logout_usuario, name='logout'),

    # URLs para o Painel de Administração
    path('admin/dashboard/', views.dashboard_admin, name='dashboard_admin'),
    path('admin/produtos/', views.gerenciar_produtos, name='gerenciar_produtos'),
    path('admin/adicionar-joia/', views.adicionar_joia, name='adicionar_joia'),
    path('admin/editar-joia/<str:joia_id>/', views.editar_joia, name='editar_joia'),
    path('admin/excluir-joia/<str:joia_id>/', views.excluir_joia, name='excluir_joia'),

    # Rota de Detalhe do Pedido (Admin)
    path('admin/pedidos/<int:pedido_id>/', views.DetalhePedidoAdminView.as_view(), name='admin_detalhe_pedido'),

    # Rota Administrativa (Acessível apenas por usuários logados)
    path('admin/pedidos/', views.ListagemPedidosView.as_view(), name='admin_listagem_pedidos'),

    # URLs da API (geradas pelo roteador)
    path('api/', include(router.urls)),
    path('api/carrinho/', views.CarrinhoAPIView.as_view(), name='carrinho-api'),
    path('api/checkout/', views.CheckoutAPIView.as_view(), name='checkout-api'),

    # URLs da Documentação da API
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/schema/swagger-ui/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/schema/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),

    # URLs de Autenticação com JWT
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # Rota de Webhook do Mercado Pago (para receber notificações de status)
    path('api/webhooks/mercadopago/', views.WebhookMercadoPago.as_view(), name='webhook_mp'),

]
