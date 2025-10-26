# vejoias/presentation/views_auth.py
"""
Views para autenticação e registro de usuários.
"""

from django.views import View
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages

from .forms import LoginForm, RegistroForm

class CadastroUsuarioView(View):
    """
    View para a página de registro de usuário.
    """
    template_name = 'auth/user_register.html'

    def get(self, request):
        form = RegistroForm()
        context = {'form': form}
        return render(request, self.template_name, context)

    def post(self, request):
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, 'Cadastro realizado com sucesso! Faça login para continuar.')
            return redirect('login')

        context = {'form': form}
        return render(request, self.template_name, context)


class LoginView(View):
    """
    View para a página de login.
    """
    template_name = 'login.html'

    def get(self, request):
        form = LoginForm()
        context = {'form': form}
        return render(request, self.template_name, context)

    def post(self, request):
        form = LoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f'Bem-vindo(a), {user.first_name if user.first_name else user.username}!')
                return redirect('home')
            else:
                messages.error(request, 'Usuário ou senha inválidos.')

        context = {'form': form}
        return render(request, self.template_name, context)


@login_required
def logout_usuario(request):
    """
    View para a saída do usuário.
    """
    messages.info(request, "Você saiu do sistema.")
    logout(request)
    return redirect('home')