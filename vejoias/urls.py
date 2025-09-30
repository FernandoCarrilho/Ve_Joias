# vejoias/urls.py

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views



urlpatterns = [
    # Inclui as URLs da sua aplicação de apresentação (o e-commerce)
    path('', include('vejoias.presentation.urls')),
    
    # URL para o painel de administração padrão do Django
    path('admin/', admin.site.urls),

    # ====================================================================
    # NOVAS URLS PARA RECUPERAÇÃO DE SENHA
    # ====================================================================
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
