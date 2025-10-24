# Configuração da interface administrativa do Django para os modelos do Ve_Joias.

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
# Importamos o modelo Usuario customizado (que contém os campos de Perfil)
from vejoias.infrastructure.models import (
    Joia, Categoria, Subcategoria, Pedido, ItemPedido, Usuario # <--- CORRIGIDO: Agora importa 'Usuario'
)

# ====================================================================
# 1. ADMIN PERSONALIZADO PARA USUÁRIOS (CUSTOMIZANDO O MODELO 'Usuario')
# ====================================================================

# Não precisamos mais de um Inline, pois os campos de perfil (telefone, cpf)
# foram movidos diretamente para o modelo Usuario.

@admin.register(Usuario)
class UsuarioAdmin(BaseUserAdmin):
    """Customização do modelo Usuario. Adiciona campos de perfil e usa email/senha."""
    
    # Define quais campos serão exibidos na listagem
    list_display = (
        'email', 
        'first_name', 
        'last_name', 
        'is_staff', 
        'is_active', 
        'telefone', 
        'cpf'
    )
    
    # Define os campos visíveis no formulário de edição/criação
    fieldsets = BaseUserAdmin.fieldsets + (
        ('Informações de Perfil', {'fields': ('telefone', 'cpf',)}),
    )
    
    # Define os campos visíveis no formulário de criação de usuário
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        ('Informações de Perfil', {'fields': ('telefone', 'cpf',)}),
    )
    
    # O campo 'username' não existe mais no modelo Usuario, então ajustamos
    # a pesquisa e ordenação para usar o 'email'.
    search_fields = ('email', 'first_name', 'last_name')
    ordering = ('email',)


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
    # O filtro foi ajustado para 'categoria', que é o nome do FK no modelo.
    list_display = ('nome', 'categoria', 'slug') 
    list_filter = ('categoria',)
    prepopulated_fields = {'slug': ('nome',)}
    search_fields = ('nome',)


# ====================================================================
# 3. ADMIN PARA PRODUTOS (JOIAS)
# ====================================================================

@admin.register(Joia)
class JoiaAdmin(admin.ModelAdmin):
    # Campos ajustados: 'data_criacao' -> 'criado_em', 'ativa' -> 'disponivel'
    list_display = ('nome', 'preco', 'estoque', 'categoria', 'subcategoria', 'disponivel', 'criado_em')
    list_filter = ('disponivel', 'categoria', 'subcategoria')
    search_fields = ('nome', 'descricao', 'id')
    ordering = ('nome',)
    fieldsets = (
        ('Informações Básicas', {
            # Campo ajustado: 'imagem_url' -> 'imagem'
            'fields': ('nome', 'descricao', 'preco', 'estoque', 'disponivel', 'imagem') 
        }),
        ('Classificação', {
            # Campos removidos: 'material' e 'peso_gramas' (não estão no modelo Joia)
            'fields': ('categoria', 'subcategoria'),
        }),
    )


# ====================================================================
# 4. ADMIN PARA PEDIDOS
# ====================================================================

class ItemPedidoInline(admin.TabularInline):
    """Exibe os itens comprados dentro do detalhe do Pedido."""
    model = ItemPedido
    # Ajustando readonly_fields para refletir o modelo ItemPedido
    readonly_fields = ('joia_nome', 'joia_preco', 'quantidade', 'subtotal')
    extra = 0
    can_delete = False

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    # Campos ajustados: 'data_criacao' -> 'data_pedido', 'total' -> 'total_pedido'
    list_display = ('id', 'usuario', 'data_pedido', 'total_pedido', 'status', 'tipo_pagamento')
    list_filter = ('status', 'tipo_pagamento', 'data_pedido')
    search_fields = ('id', 'usuario__email', 'rua_entrega', 'cidade_entrega') 
    date_hierarchy = 'data_pedido'
    inlines = [ItemPedidoInline]
    
    # Ajustando readonly_fields para refletir os campos de endereço desagregados
    readonly_fields = (
        'usuario', 
        'data_pedido', 
        'total_pedido', 
        'tipo_pagamento', 
        'cep_entrega', 
        'rua_entrega',
        'numero_entrega',
        'bairro_entrega',
        'cidade_entrega',
        'estado_entrega',
        'referencia_entrega',
        'telefone_whatsapp'
    )

    def save_model(self, request, obj, form, change):
        """Permite que o administrador altere apenas o status do pedido."""
        if not change:
            # Não permitir criação manual de pedidos (apenas por checkout)
            super().save_model(request, obj, form, change)
        
        if change:
            try:
                original_pedido = Pedido.objects.get(pk=obj.pk)
                if original_pedido.status != obj.status:
                    # Lógica para notificar o cliente sobre a mudança de status, se necessário
                    pass 
            except Pedido.DoesNotExist:
                pass
            
            super().save_model(request, obj, form, change)

    def has_add_permission(self, request):
        """Impedir a criação de pedidos pela interface do Admin."""
        return False
