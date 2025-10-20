# vejoias/presentation/forms.py

from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth import get_user_model
from decimal import Decimal
from vejoias.core.entities import Endereco
from vejoias.infrastructure.models import Joia as JoiaModel
from vejoias.core.exceptions import EstoqueInsuficienteError
from vejoias.core.entities import Carrinho
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
    cep = forms.CharField(label='CEP', max_length=10)
    rua = forms.CharField(label='Endereço Completo', max_length=255)
    numero = forms.CharField(label='Número', max_length=10)
    bairro = forms.CharField(label='Bairro', max_length=100)
    cidade = forms.CharField(label='Cidade', max_length=100)
    estado = forms.CharField(label='Estado', max_length=50)
    referencia = forms.CharField(label='Ponto de Referência', max_length=255, required=False)

    # Campo de Pagamento
    TIPO_PAGAMENTO_CHOICES = [
        ('pix', 'Pix'),
        ('cartao', 'Cartão de Crédito'),
        ('boleto', 'Boleto Bancário'),
    ]
    tipo_pagamento = forms.ChoiceField(
        label='Método de Pagamento', 
        choices=TIPO_PAGAMENTO_CHOICES, 
        widget=forms.RadioSelect
    )
    telefone_whatsapp = forms.CharField(
        max_length=15, 
        label='Telefone WhatsApp',
        help_text='Use o formato internacional (DDI + DDD + Número) para receber a confirmação.'
    )
    def clean_telefone_whatsapp(self):
        """
        Remove caracteres não numéricos e valida o formato do telefone para o WhatsApp.
        """
        telefone = self.cleaned_data['telefone_whatsapp']
        
        # 1. Limpeza: Remove todos os caracteres não numéricos (espaços, parênteses, traços, etc.)
        numero_limpo = re.sub(r'\D', '', telefone)
        
        # 2. Validação Mínima:
        # Padrão brasileiro (10 a 11 dígitos, mais o DDI 55). 
        # Ex: 55 + DDD (2 dígitos) + Número (8 ou 9 dígitos) = 12 ou 13 dígitos
        if not (12 <= len(numero_limpo) <= 13):
            raise forms.ValidationError(
                "O número de telefone deve ter entre 12 e 13 dígitos no formato DDI+DDD+Número (Ex: 5511987654321)."
            )

        # 3. Adiciona o DDI brasileiro (55) se o usuário não o incluiu (para DDD+Número, 10 ou 11 dígitos)
        # Se o número tiver 10 ou 11 dígitos, assumimos que é um telefone nacional (DD + Número)
        # e adicionamos o 55 no início.
        if len(numero_limpo) in [10, 11] and numero_limpo.startswith(('1', '2', '3', '4', '5', '6', '7', '8', '9')):
             numero_limpo = '55' + numero_limpo
             
        # 4. Revalidação final
        if not (numero_limpo.startswith('55') and 12 <= len(numero_limpo) <= 13):
             raise forms.ValidationError(
                "O número de telefone final não está no formato internacional válido (Ex: 5511987654321)."
            )

        # Retorna o número limpo e padronizado, pronto para o Evolution-API
        return numero_limpo

    def clean_cep(self):
        cep = self.cleaned_data.get('cep')
        if not cep.isdigit() and len(cep) != 8:
            raise ValidationError("CEP inválido.")
        return cep

    def to_endereco_entity(self) -> Endereco:
        return Endereco(
            telefone=self.cleaned_data['telefone_whatsapp'],
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
        model = get_user_model()
        fields = UserCreationForm.Meta.fields + ('email',) 

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
