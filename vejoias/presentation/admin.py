# vejoias/presentation/admin.py

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.html import format_html
from django.db.models import Sum 

# Importa todos os Models da nossa camada de Infraestrutura
from vejoias.infrastructure import models 


# -----------------------------------------------------
# 1. Joia (Produto)
# -----------------------------------------------------

@admin.register(models.Joia)
class JoiaAdmin(admin.ModelAdmin):
    """Configuração de exibição da Joia no Django Admin."""
    
    # CORREÇÃO E122: 'preco' incluído em list_display para que list_editable funcione
    list_display = ('nome', 'categoria', 'subcategoria', 'preco_formatado', 'preco', 'estoque', 'disponivel', 'visualizar_no_site')
    list_filter = ('disponivel', 'categoria', 'subcategoria', 'genero')
    search_fields = ('nome', 'descricao', 'tamanho')
    list_editable = ('preco', 'estoque', 'disponivel')
    list_display_links = ('nome',)
    
    def preco_formatado(self, obj):
        return f"R$ {obj.preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    preco_formatado.short_description = 'Preço (R$)'

    def visualizar_no_site(self, obj):
        if obj.id:
            return format_html('<a href="/joia/{}/" target="_blank">Ver Produto</a>', obj.id)
        return "N/A"
    visualizar_no_site.short_description = 'Link'


# -----------------------------------------------------
# 2. Carrinho e Itens (Inlines)
# -----------------------------------------------------

class ItemCarrinhoInline(admin.TabularInline):
    """Permite editar ItemCarrinho dentro da página do Carrinho."""
    model = models.ItemCarrinho
    extra = 0
    fields = ('joia', 'quantidade') 
    readonly_fields = ()


@admin.register(models.Carrinho)
class CarrinhoAdmin(admin.ModelAdmin):
    """Configuração de exibição do Carrinho no Django Admin."""
    # CORRIGIDO E108/E116: 'data_criacao' agora existe no modelo Carrinho
    list_display = ('id', 'usuario', 'total_itens', 'data_criacao')
    list_filter = ('data_criacao',)
    search_fields = ('usuario__username', 'usuario__email')
    inlines = [ItemCarrinhoInline] 
    
    def total_itens(self, obj):
        return obj.itens.aggregate(total=Sum('quantidade'))['total'] or 0 
    total_itens.short_description = 'Total de Itens'


# -----------------------------------------------------
# 3. Pedido e Itens
# -----------------------------------------------------

class ItemPedidoInline(admin.TabularInline):
    """Permite ver os itens de um pedido dentro da página do Pedido."""
    model = models.ItemPedido
    extra = 0
    readonly_fields = ('joia', 'quantidade', 'preco_unitario_no_pedido') 
    fields = ('joia', 'quantidade', 'preco_unitario_no_pedido')
    can_delete = False 
    
    def preco_unitario_no_pedido(self, obj):
        return f"R$ {obj.preco_unitario:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    preco_unitario_no_pedido.short_description = 'Preço Unitário'


@admin.register(models.Pedido)
class PedidoAdmin(admin.ModelAdmin):
    """Configuração de exibição de Pedido no Django Admin."""
    # CORRIGIDO E035/E108/E116: Mudando 'data_pedido' para 'data_criacao' (nome real do campo)
    list_display = ('id', 'usuario', 'data_criacao', 'status', 'valor_total')
    list_filter = ('status', 'data_criacao')
    search_fields = ('usuario__username', 'id')
    # O valor_total precisa de um método get_valor_total() no modelo Pedido
    readonly_fields = ('data_criacao', 'total') 
    inlines = [ItemPedidoInline] 
    
    def valor_total(self, obj):
        # Usamos o campo 'total' do modelo Pedido
        return f"R$ {obj.total:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    valor_total.short_description = 'Valor Total'


@admin.register(models.Endereco)
class EnderecoAdmin(admin.ModelAdmin):
    """Configuração de exibição de Endereço no Django Admin."""
    # CORRIGIDO E108/E116: 'principal' agora existe no modelo Endereco
    list_display = ('usuario', 'cep', 'cidade', 'estado', 'principal')
    list_filter = ('estado', 'principal')
    search_fields = ('usuario__username', 'cep', 'cidade')

@admin.register(models.Usuario)
class UsuarioAdmin(BaseUserAdmin):
    """Configuração para o modelo de usuário (extende as funcionalidades padrão do Django)."""
    
    # CORREÇÃO E012: Removendo o campo 'email' do fieldsets
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            'Informações de Contato Adicionais', 
            {'fields': ('telefone', 'tipo_usuario')} # Adicionando campos customizados
        ),
    )

    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active', 'date_joined', 'telefone', 'tipo_usuario')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups', 'tipo_usuario')
    search_fields = ('username', 'first_name', 'last_name', 'email', 'telefone')
