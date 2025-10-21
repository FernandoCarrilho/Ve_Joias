# vejoias/urls.py
"""
Configuração principal de URL do projeto Vejoias.

Este arquivo centraliza o roteamento, incluindo:
1. Rotas do Admin (Django Admin)
2. Rotas da Loja (vejoias.presentation)
3. Rotas de Autenticação (Recuperação de Senha)
4. Rotas da Documentação da API (Swagger/Redoc)
"""
from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView


urlpatterns = [
    # Inclui as URLs da sua aplicação de apresentação (o e-commerce)
    path('', include('vejoias.presentation.urls')),
    
    # URL para o painel de administração padrão do Django
    path('admin/', admin.site.urls),

    # ====================================================================
    # ROTAS DE DOCUMENTAÇÃO DA API (DRF SPECTACULAR)
    # ====================================================================
     # 1. Rota para o arquivo Schema YAML (gerado automaticamente)
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    
    # 2. Rota para a interface de usuário do Swagger (visualização interativa)
    path('api/docs/swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    
    # Opcional: Rota para a interface Redoc
    path('api/docs/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),


    # ====================================================================
    # ROTAS PADRÃO DO DJANGO PARA RECUPERAÇÃO DE SENHA
    # ====================================================================
    # NOTA: Os templates para estas views devem ser criados em vejoias/presentation/templates/password_reset/
    
    # 1. Solicita o e-mail para a redefinição de senha
    path('password_reset/',
         auth_views.PasswordResetView.as_view(template_name='password_reset/password_reset_form.html'),
         name='password_reset'),

    # 2. Mostra que o e-mail de redefinição foi enviado
    path('password_reset/done/',
         auth_views.PasswordResetDoneView.as_view(template_name='password_reset/password_reset_done.html'),
         name='password_reset_done'),

    # 3. Valida o token e o uid para redefinir a senha
    path('reset/<uidb64>/<token>/',
         auth_views.PasswordResetConfirmView.as_view(template_name='password_reset/password_reset_confirm.html'),
         name='password_reset_confirm'),

    # 4. Confirma que a senha foi redefinida com sucesso
    path('reset/done/',
         auth_views.PasswordResetCompleteView.as_view(template_name='password_reset/password_reset_complete.html'),
         name='password_reset_complete'),
         
]
