# vejoias/presentation/forms.py

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from decimal import Decimal
from core.entities import Endereco
from infrastructure.models import Joia as JoiaModel
from core.exceptions import EstoqueInsuficienteError
from core.entities import Carrinho
import re

# ====================================================================
# FORMULÁRIOS DO E-COMMERCE
# ====================================================================

class AdicionarItemCarrinhoForm(forms.Form):
    """
    Formulário para validar a adição de um item ao carrinho.
    """
    joia_id = forms.CharField(label='ID da Joia', max_length=100)
    quantidade = forms.IntegerField(label='Quantidade', min_value=1)

    def clean_quantidade(self):
        quantidade = self.cleaned_data.get('quantidade')
        if not isinstance(quantidade, int) or quantidade <= 0:
            raise ValidationError("A quantidade deve ser um número inteiro maior que zero.")
        return quantidade

class CheckoutForm(forms.Form):
    """
    Formulário completo para os dados do checkout.
    """
    # Campos de Endereço
    cep = forms.CharField(label='CEP', max_length=9)
    rua = forms.CharField(label='Endereço Completo', max_length=255)
    numero = forms.CharField(label='Número', max_length=10)
    bairro = forms.CharField(label='Bairro', max_length=100)
    cidade = forms.CharField(label='Cidade', max_length=100)
    estado = forms.CharField(label='Estado', max_length=50)
    referencia = forms.CharField(label='Ponto de Referência', max_length=255, required=False)

    # Campo de Pagamento
    TIPO_PAGAMENTO_CHOICES = [
        ('pix', 'Pix'),
        ('cartao', 'Cartão de Crédito')
    ]
    tipo_pagamento = forms.ChoiceField(
        label='Método de Pagamento', 
        choices=TIPO_PAGAMENTO_CHOICES, 
        widget=forms.RadioSelect
    )

    def clean_cep(self):
        cep = self.cleaned_data.get('cep')
        if not cep.isdigit() and len(cep) != 8:
            raise ValidationError("CEP inválido.")
        return cep

    def to_endereco_entity(self) -> Endereco:
        return Endereco(
            cep=self.cleaned_data.get('cep'),
            rua=self.cleaned_data.get('rua'),
            numero=self.cleaned_data.get('numero'),
            bairro=self.cleaned_data.get('bairro'),
            cidade=self.cleaned_data.get('cidade'),
            estado=self.cleaned_data.get('estado')
        )

# ====================================================================
# NOVOS FORMULÁRIOS DE AUTENTICAÇÃO
# ====================================================================

class RegistroForm(UserCreationForm):
    """
    Formulário de registro que usa a classe base do Django.
    """
    class Meta(UserCreationForm.Meta):
        # A classe Meta herda do UserCreationForm, mas podemos adicionar
        # campos extras aqui se precisarmos no futuro.
        # Por enquanto, apenas o nome do modelo de usuário é suficiente.
        model = 'infrastructure.Usuario'

class LoginForm(AuthenticationForm):
    """
    Formulário de login que usa a classe base do Django.
    """
    # Não precisamos adicionar campos, a classe base já tem 'username' e 'password'.
    pass


class JoiaForm(forms.ModelForm):
    """
    Formulário para criar ou editar joias.
    Utiliza o ModelForm do Django para simplificar a criação a partir do modelo Joia.
    """
    class Meta:
        model = JoiaModel
        fields = ['nome', 'descricao', 'preco', 'estoque', 'categoria', 'subcategoria']
