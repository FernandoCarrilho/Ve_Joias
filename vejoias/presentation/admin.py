"""
Configuração do painel de administração para a camada de infraestrutura.

Registra todos os modelos de dados (Usuário, Joia, Pedido, etc.) e aplica
otimizações de visualização para o Django Admin.
"""
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import (
    Usuario, Endereco, Categoria, Subcategoria, Joia, 
    Carrinho, ItemCarrinho, Pedido, ItemPedido
)
from django.utils.translation import gettext_lazy as _

# ====================================================================
# 1. INLINES (Para visualização de modelos relacionados)
# ====================================================================

class EnderecoInline(admin.TabularInline):
    """Exibe endereços dentro do formulário de edição de Usuário."""
    model = Endereco
    extra = 1
    fields = ('cep', 'rua', 'numero', 'cidade', 'estado', 'principal')

class SubcategoriaInline(admin.TabularInline):
    """Exibe subcategorias dentro do formulário de edição de Categoria."""
    model = Subcategoria
    extra = 1
    prepopulated_fields = {'slug': ('nome',)}

class ItemCarrinhoInline(admin.TabularInline):
    """Exibe itens dentro do formulário de edição de Carrinho."""
    model = ItemCarrinho
    readonly_fields = ('subtotal',)
    fields = ('joia', 'quantidade', 'subtotal')
    extra = 0

class ItemPedidoInline(admin.TabularInline):
    """Exibe itens dentro do formulário de edição de Pedido."""
    model = ItemPedido
    readonly_fields = ('joia_nome', 'joia_preco', 'quantidade', 'subtotal')
    fields = ('joia_nome', 'joia_preco', 'quantidade', 'subtotal')
    extra = 0
    can_delete = False
    max_num = 0 # Não permite adicionar novos itens manualmente

# ====================================================================
# 2. ADMINS PERSONALIZADOS
# ====================================================================

@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    """
    Personalização do Admin para o modelo Usuario.
    Substitui o username por email e inclui campos de perfil.
    """
    inlines = (EnderecoInline,) # Adiciona Endereços in-line
    
    # Define os campos a serem exibidos na listagem
    list_display = (
        'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'is_admin', 'cpf', 'telefone'
    )
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'is_admin', 'date_joined')
    search_fields = ('email', 'first_name', 'last_name', 'cpf')
    ordering = ('email',)
    
    # Define os campos a serem exibidos no formulário de edição
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        (_('Personal info'), {'fields': ('first_name', 'last_name', 'telefone', 'cpf')}),
        (_('Permissions'), {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'is_admin', 'groups', 'user_permissions'),
        }),
        (_('Important dates'), {'fields': ('last_login', 'date_joined')}),
    )
    
    # Ajusta os add_fieldsets para inclusão dos campos customizados
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (_('Informações de Perfil'), {'fields': ('telefone', 'cpf', 'is_admin')}),
    )


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    """Admin para Categoria com subcategorias inline."""
    list_display = ('nome', 'slug')
    prepopulated_fields = {'slug': ('nome',)}
    inlines = (SubcategoriaInline,)


@admin.register(Joia)
class JoiaAdmin(admin.ModelAdmin):
    """Admin para Joias (Produtos)."""
    list_display = ('nome', 'preco_formatado', 'estoque', 'disponivel', 'categoria', 'subcategoria', 'criado_em')
    list_filter = ('disponivel', 'categoria', 'subcategoria', 'criado_em')
    search_fields = ('nome', 'descricao')
    
    # Campos que serão exibidos no formulário de edição
    fields = (
        ('nome', 'preco', 'estoque'),
        ('categoria', 'subcategoria', 'disponivel'),
        'descricao',
        'imagem', # Para upload
    )


@admin.register(Carrinho)
class CarrinhoAdmin(admin.ModelAdmin):
    """Admin para Carrinhos de Compras."""
    list_display = ('id', 'usuario', 'sessao_key', 'total_carrinho', 'data_atualizacao')
    list_display_links = ('id',)
    list_filter = ('data_criacao', 'data_atualizacao')
    search_fields = ('usuario__email', 'sessao_key')
    readonly_fields = ('total_carrinho',)
    inlines = (ItemCarrinhoInline,)
    
    # Garante que o campo total_carrinho seja exibido no topo do formulário
    fieldsets = (
        (None, {
            'fields': (('usuario', 'sessao_key'), 'total_carrinho', 'data_criacao', 'data_atualizacao')
        }),
    )


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    """Admin para Pedidos."""
    list_display = ('id', 'usuario', 'data_pedido', 'status', 'total_pedido', 'tipo_pagamento')
    list_filter = ('status', 'tipo_pagamento', 'data_pedido')
    search_fields = ('usuario__email', 'id')
    readonly_fields = ('total_pedido', 'data_pedido')
    inlines = (ItemPedidoInline,)

    fieldsets = (
        (None, {
            'fields': (('usuario', 'status'), 'data_pedido', 'total_pedido', 'tipo_pagamento')
        }),
        ('Endereço de Entrega (Snapshot)', {
            'fields': (
                ('cep_entrega', 'numero_entrega'),
                ('rua_entrega', 'bairro_entrega'),
                ('cidade_entrega', 'estado_entrega'),
                'referencia_entrega',
                'telefone_whatsapp'
            ),
            'description': 'Endereço e contato registrados no momento da compra.'
        }),
    )
    
    # Bloqueia a criação manual de pedidos
    def has_add_permission(self, request):
        return False

# 3. Registro dos modelos restantes (sem customização avançada)
@admin.register(Endereco)
class EnderecoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rua', 'cidade', 'estado', 'principal')
    list_filter = ('estado', 'principal')

@admin.register(Subcategoria)
class SubcategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria', 'slug')
    list_filter = ('categoria',)
    prepopulated_fields = {'slug': ('nome',)}
