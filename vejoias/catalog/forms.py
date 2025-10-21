# vejoias/catalog/forms.py
from django import forms
from django.core.exceptions import ValidationError
from decimal import Decimal

# Importações dos Models para ModelForms
from .models import Joia, Categoria

# ====================================================================
# Formulário para Joia (Administração)
# ====================================================================

class JoiaAdminForm(forms.ModelForm):
    """
    Formulário para criar e editar Joias no painel de administração.
    Implementa validações de negócio importantes.
    """
    class Meta:
        model = Joia
        fields = [
            'nome', 'descricao', 'preco', 'estoque', 
            'categoria', 'material', 'peso_gramas', 
            'dimensoes', 'imagem_url', 'is_destaque'
        ]
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 4}),
            'imagem_url': forms.URLInput(attrs={'placeholder': 'URL da imagem da joia'}),
        }

    def clean_preco(self):
        """Valida se o preço é um valor positivo e razoável."""
        preco = self.cleaned_data.get('preco')
        if preco is not None:
            if preco <= Decimal('0.00'):
                raise ValidationError("O preço deve ser um valor positivo.")
            if preco > Decimal('999999.99'):
                 raise ValidationError("Preço muito alto. Verifique o valor (Máx: 999999.99).")
        return preco

    def clean_estoque(self):
        """Valida se o estoque é não-negativo."""
        estoque = self.cleaned_data.get('estoque')
        if estoque is not None and estoque < 0:
            raise ValidationError("O estoque não pode ser negativo.")
        return estoque

    def clean_peso_gramas(self):
        """Valida se o peso é positivo."""
        peso = self.cleaned_data.get('peso_gramas')
        if peso is not None and peso <= Decimal('0.00'):
            # Permite peso zero se o campo não for obrigatório, mas evita negativos
            raise ValidationError("O peso em gramas deve ser um valor positivo.")
        return peso

# ====================================================================
# Formulário para Categoria (Administração)
# ====================================================================

class CategoriaAdminForm(forms.ModelForm):
    """
    Formulário para criar e editar Categorias no painel de administração.
    """
    class Meta:
        model = Categoria
        fields = ['nome', 'slug', 'descricao']
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 3}),
            'slug': forms.TextInput(attrs={'placeholder': 'ex: aneis-de-ouro'}),
        }

    def clean_slug(self):
        """Garante que o slug seja minúsculo e contenha apenas caracteres válidos."""
        slug = self.cleaned_data.get('slug')
        if slug:
            if any(char.isupper() for char in slug):
                raise ValidationError("O slug deve conter apenas letras minúsculas.")
            # Validação básica de formato. O Django já deve garantir unicidade.
        return slug.lower()
