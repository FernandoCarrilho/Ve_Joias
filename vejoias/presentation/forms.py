# vejoias/presentation/forms.py

from datetime import datetime
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import PasswordChangeForm
from vejoias.infrastructure.models import Usuario
from vejoias.catalog.models import Joia, Categoria
from vejoias.catalog.models import Subcategoria
from vejoias.vendas.models import Pedido
from decimal import Decimal

# --- 1. FORMULÁRIOS DE AUTENTICAÇÃO ---

class LoginForm(forms.Form):
    """
    Formulário simples para login.
    """
    username = forms.CharField(
        label="E-mail ou Nome de Usuário",
        max_length=150,
        widget=forms.TextInput(attrs={'placeholder': 'Seu e-mail ou usuário'})
    )
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={'placeholder': 'Sua senha secreta'})
    )
    # Lógica de validação de autenticação deve ser implementada na View (e.g., usando authenticate)


class RegistroForm(forms.ModelForm):
    """
    Formulário para registro de novos usuários.
    Cria um User e um PerfilUsuario.
    """
    email = forms.EmailField(
        label="E-mail",
        max_length=254,
        required=True,
        widget=forms.EmailInput(attrs={'placeholder': 'Seu melhor e-mail'})
    )
    password = forms.CharField(
        label="Senha",
        widget=forms.PasswordInput(attrs={'placeholder': 'Crie uma senha forte'})
    )
    password_confirm = forms.CharField(
        label="Confirme a Senha",
        widget=forms.PasswordInput(attrs={'placeholder': 'Digite a senha novamente'})
    )

    class Meta:
        model = User
        fields = ('username', 'email') # Usaremos apenas username e email da model User

    def clean_username(self):
        username = self.cleaned_data['username']
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("Este nome de usuário já está em uso.")
        return username

    def clean(self):
        # Validação para garantir que as senhas são iguais
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")

        if password and password_confirm and password != password_confirm:
            self.add_error('password_confirm', "As senhas não coincidem.")
            
        return cleaned_data
    
    # Lógica de save para criar User e PerfilUsuario deve ser implementada na View.

# --- 2. FORMULÁRIOS DE PERFIL E SENHA ---

class PerfilForm(forms.ModelForm):
    """
    Formulário para edição dos dados do Usuario.
    """
    class Meta:
        model = Usuario
        fields = ('first_name', 'last_name', 'telefone')

    # Já não precisamos sobrescrever __init__ ou save pois agora
    # estamos editando diretamente o modelo Usuario que herda de AbstractUser
    # e já tem os campos first_name e last_name


class SenhaForm(PasswordChangeForm):
    """
    Formulário de alteração de senha padrão do Django.
    """
    # Os campos old_password, new_password1 e new_password2 já são definidos.
    # A lógica de save (mudar a senha) é herdada do PasswordChangeForm.
    pass

# --- 3. FORMULÁRIOS ADMINISTRATIVOS ---

class AdicionarItemCarrinhoForm(forms.Form):
    """
    Formulário para adicionar item ao carrinho.
    """
    joia_id = forms.IntegerField(widget=forms.HiddenInput())
    quantidade = forms.IntegerField(
        min_value=1,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': '1',
            'step': '1'
        })
    )

    def clean_quantidade(self):
        quantidade = self.cleaned_data['quantidade']
        if quantidade < 1:
            raise forms.ValidationError("A quantidade deve ser pelo menos 1.")
        return quantidade


class JoiaForm(forms.ModelForm):
    """
    Formulário para adicionar ou editar Joias no Admin.
    """
    # Sobrescrevemos o campo categoria para usar um Select simples com as Categorias
    categoria = forms.ModelChoiceField(
        queryset=Categoria.objects.all(),
        label="Categoria da Joia",
        empty_label="Selecione uma Categoria"
    )

    class Meta:
        model = Joia
        # Todos os campos necessários para o template detalhe_joia_admin.html
        fields = ['nome', 'descricao', 'preco', 'estoque', 'categoria', 'subcategoria', 'imagem_principal', 'disponivel', 'em_destaque']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 4}),
            'preco': forms.NumberInput(attrs={'step': '0.01'}),
            'imagem_principal': forms.FileInput(attrs={'class': 'w-full'}),
        }


# --- 4. FORMULÁRIOS DE CHECKOUT ---

class CheckoutForm(forms.Form):
    """
    Formulário para finalização do pedido no checkout.
    """
    # Dados de Endereço (pode ser pré-preenchido do PerfilUsuario)
    endereco = forms.CharField(
        label="Endereço de Entrega Completo",
        widget=forms.Textarea(attrs={'rows': 3})
    )
    
    # Simulação de dados de pagamento (em um ambiente real, seriam tokens ou integração)
    cartao_numero = forms.CharField(label="Número do Cartão", max_length=16, min_length=16)
    validade_mes = forms.IntegerField(label="Mês de Validade", min_value=1, max_value=12)
    validade_ano = forms.IntegerField(label="Ano de Validade", min_value=datetime.now().year)
    cvv = forms.CharField(label="CVV", max_length=4, min_length=3)
    
    # Lógica de validação real do pagamento deve ser implementada na View/Serviço.
    def clean_cartao_numero(self):
        numero = self.cleaned_data['cartao_numero']
        if not numero.isdigit():
            raise forms.ValidationError("O número do cartão deve conter apenas dígitos.")
        return numero
