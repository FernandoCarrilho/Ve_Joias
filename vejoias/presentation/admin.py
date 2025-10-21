# vejoias/presentation/admin.py
# Configuração da interface administrativa do Django para os modelos do Ve_Joias.

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import User
from vejoias.infrastructure.models import (
    Joia, Categoria, Subcategoria, Pedido, ItemPedido, PerfilUsuario
)

# ====================================================================
# 1. ADMIN PERSONALIZADO PARA USUÁRIOS E PERFIL
# ====================================================================

class PerfilUsuarioInline(admin.StackedInline):
    """Permite editar o PerfilUsuario diretamente na página do User."""
    model = PerfilUsuario
    can_delete = False
    verbose_name_plural = 'Perfil'
    fields = ('telefone', 'endereco', 'is_admin')

class UserAdmin(BaseUserAdmin):
    """Customização do modelo User do Django para incluir o PerfilUsuario."""
    inlines = (PerfilUsuarioInline,)
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'get_is_admin')
    
    # Adiciona 'is_admin' nos campos de permissão
    def get_is_admin(self, obj):
        return obj.perfilusuario.is_admin
    get_is_admin.short_description = 'É Admin'
    get_is_admin.boolean = True

# Desregistra o User padrão e registra o customizado
admin.site.unregister(User)
admin.site.register(User, UserAdmin)

# ====================================================================
# 2. ADMIN PARA CATEGORIAS
# ====================================================================

class SubcategoriaInline(admin.TabularInline):
    """Permite editar Subcategorias diretamente na página da Categoria."""
    model = Subcategoria
    extra = 1
    prepopulated_fields = {'slug': ('nome',)}

@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'slug')
    inlines = [SubcategoriaInline]
    prepopulated_fields = {'slug': ('nome',)}
    search_fields = ('nome',)

@admin.register(Subcategoria)
class SubcategoriaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria_pai', 'slug')
    list_filter = ('categoria_pai',)
    prepopulated_fields = {'slug': ('nome',)}
    search_fields = ('nome',)


# ====================================================================
# 3. ADMIN PARA PRODUTOS (JOIAS)
# ====================================================================

@admin.register(Joia)
class JoiaAdmin(admin.ModelAdmin):
    list_display = ('nome', 'preco', 'estoque', 'categoria', 'subcategoria', 'ativa', 'data_criacao')
    list_filter = ('ativa', 'categoria', 'subcategoria', 'material')
    search_fields = ('nome', 'descricao', 'id')
    ordering = ('nome',)
    fieldsets = (
        ('Informações Básicas', {
            'fields': ('nome', 'descricao', 'preco', 'estoque', 'ativa', 'imagem_url')
        }),
        ('Classificação', {
            'fields': ('categoria', 'subcategoria', 'material', 'peso_gramas'),
        }),
    )


# ====================================================================
# 4. ADMIN PARA PEDIDOS
# ====================================================================

class ItemPedidoInline(admin.TabularInline):
    """Exibe os itens comprados dentro do detalhe do Pedido."""
    model = ItemPedido
    raw_id_fields = ('joia',)
    readonly_fields = ('nome_joia', 'preco_unitario', 'quantidade')
    extra = 0
    can_delete = False

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'usuario', 'data_criacao', 'total', 'status', 'tipo_pagamento')
    list_filter = ('status', 'tipo_pagamento', 'data_criacao')
    search_fields = ('id', 'usuario__username', 'endereco_entrega')
    date_hierarchy = 'data_criacao'
    inlines = [ItemPedidoInline]
    readonly_fields = ('usuario', 'data_criacao', 'total', 'endereco_entrega', 'tipo_pagamento', 'id_transacao')

    def save_model(self, request, obj, form, change):
        """Permite que o administrador altere apenas o status do pedido."""
        if not change:
            # Não permitir criação manual de pedidos (apenas por checkout)
            super().save_model(request, obj, form, change)
        
        # Obter o Pedido original para verificar se o status mudou
        if change:
            original_pedido = Pedido.objects.get(pk=obj.pk)
            # A única alteração permitida deve ser no status.
            if original_pedido.status != obj.status:
                # Lógica para notificar o cliente sobre a mudança de status, se necessário
                pass 
            super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        """Impedir a criação de pedidos pela interface do Admin."""
        return False
