# vejoias/presentation/models.py
from django.db import models
from django.conf import settings
from django.utils import timezone

# Modelo de Extensão do Usuário (Perfil)
class PerfilUsuario(models.Model):
    """
    Extensão do modelo User padrão do Django para adicionar campos específicos da loja.
    """
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfilusuario')
    telefone = models.CharField(max_length=15, blank=True, null=True)
    endereco = models.TextField(blank=True, null=True, verbose_name="Endereço Completo")
    is_admin = models.BooleanField(default=False, verbose_name="É Administrador")

    def __str__(self):
        return f"Perfil de {self.usuario.username}"
    
    class Meta:
        verbose_name = "Perfil de Usuário"
        verbose_name_plural = "Perfis de Usuários"


# Modelo para Categorias de Joias (ex: Anéis, Colares, Brincos)
class Categoria(models.Model):
    """
    Define as categorias para organização do catálogo de joias.
    """
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome da Categoria")
    slug = models.SlugField(unique=True, help_text="Slug gerado automaticamente a partir do nome.")
    
    def __str__(self):
        return self.nome
        
    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"


# Modelo Principal para a Joia (Produto)
class Joia(models.Model):
    """
    Define os detalhes de cada joia disponível para venda.
    """
    nome = models.CharField(max_length=200, verbose_name="Nome da Joia")
    descricao = models.TextField(verbose_name="Descrição Detalhada")
    preco = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço de Venda")
    estoque = models.IntegerField(default=0, verbose_name="Estoque Disponível")
    
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, related_name='joias', verbose_name="Categoria")
    
    # Detalhes adicionais, conforme sugerido nos templates
    material = models.CharField(max_length=100, blank=True, null=True)
    peso_gramas = models.DecimalField(max_digits=6, decimal_places=2, blank=True, null=True)
    
    # Assumindo que você usará URLs para as imagens
    imagem_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="URL da Imagem Principal")
    
    data_criacao = models.DateTimeField(default=timezone.now, verbose_name="Data de Criação")
    ativa = models.BooleanField(default=True, verbose_name="Ativa no Catálogo")

    def __str__(self):
        return self.nome
        
    class Meta:
        verbose_name = "Joia"
        verbose_name_plural = "Joias"
        ordering = ['nome']


# Modelo para Pedidos de Clientes
class Pedido(models.Model):
    """
    Representa um pedido feito por um cliente.
    """
    STATUS_PROCESSANDO = 'PROCESSANDO'
    STATUS_ENVIADO = 'ENVIADO'
    STATUS_ENTREGUE = 'ENTREGUE'
    STATUS_CONCLUIDO = 'CONCLUIDO'
    STATUS_CANCELADO = 'CANCELADO'

    STATUS_CHOICES = [
        (STATUS_PROCESSANDO, 'Processando'),
        (STATUS_ENVIADO, 'Enviado'),
        (STATUS_ENTREGUE, 'Em Entrega'),
        (STATUS_CONCLUIDO, 'Concluído'),
        (STATUS_CANCELADO, 'Cancelado'),
    ]

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name='pedidos_usuario', verbose_name="Cliente")
    data_criacao = models.DateTimeField(default=timezone.now, verbose_name="Data do Pedido")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PROCESSANDO, verbose_name="Status do Pedido")
    
    endereco_entrega = models.TextField(verbose_name="Endereço de Entrega")
    total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Total (Incluindo Frete)")
    
    # Campo para armazenar o ID da transação de pagamento
    id_transacao = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Pedido #{self.id} - {self.get_status_display()}"

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ['-data_criacao']


# Modelo para os Itens dentro de um Pedido
class ItemPedido(models.Model):
    """
    Representa uma joia e sua quantidade dentro de um pedido específico.
    """
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens', verbose_name="Pedido")
    joia = models.ForeignKey(Joia, on_delete=models.CASCADE, verbose_name="Joia")
    
    quantidade = models.IntegerField(default=1, verbose_name="Quantidade")
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço na Data da Compra")

    def get_subtotal(self):
        return self.quantidade * self.preco_unitario

    def __str__(self):
        return f"{self.quantidade}x {self.joia.nome} em Pedido #{self.pedido.id}"
    
    class Meta:
        verbose_name = "Item de Pedido"
        verbose_name_plural = "Itens de Pedido"
