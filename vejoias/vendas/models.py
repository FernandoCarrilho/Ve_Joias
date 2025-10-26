from django.db import models
from django.utils.translation import gettext_lazy as _
from decimal import Decimal

class Pedido(models.Model):
    """
    Modelo que representa um pedido/venda no sistema.
    """
    # Relacionamentos
    usuario = models.ForeignKey('infrastructure.Usuario', on_delete=models.PROTECT)

    # Status e Data
    STATUS_CHOICES = [
        ('aguardando_pagamento', 'Aguardando Pagamento'),
        ('pago', 'Pago'),
        ('em_preparacao', 'Em Preparação'),
        ('enviado', 'Enviado'),
        ('entregue', 'Entregue'),
        ('cancelado', 'Cancelado'),
    ]
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='aguardando_pagamento')
    data_pedido = models.DateTimeField(auto_now_add=True)
    data_modificacao = models.DateTimeField(auto_now=True)

    # Valores
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    desconto = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    frete = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    # Dados de Pagamento
    FORMA_PAGAMENTO_CHOICES = [
        ('cartao', 'Cartão de Crédito'),
        ('boleto', 'Boleto'),
        ('pix', 'PIX'),
    ]
    forma_pagamento = models.CharField(max_length=10, choices=FORMA_PAGAMENTO_CHOICES)
    codigo_transacao = models.CharField(max_length=100, blank=True, null=True)

    # Dados de Entrega (snapshot do endereço no momento do pedido)
    nome_entrega = models.CharField(max_length=255)
    cep_entrega = models.CharField(max_length=9)
    rua_entrega = models.CharField(max_length=255)
    numero_entrega = models.CharField(max_length=10)
    complemento_entrega = models.CharField(max_length=100, blank=True, null=True)
    bairro_entrega = models.CharField(max_length=100)
    cidade_entrega = models.CharField(max_length=100)
    estado_entrega = models.CharField(max_length=2)
    
    # Contato
    telefone_contato = models.CharField(max_length=15)
    email_contato = models.EmailField()
    observacoes = models.TextField(blank=True)

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        db_table = 'vendas_pedido'
        ordering = ['-data_pedido']

    def __str__(self):
        return f"Pedido #{self.id} - {self.usuario.email}"

    def get_status_display_custom(self):
        """Retorna o status formatado para exibição."""
        return dict(self.STATUS_CHOICES)[self.status]

    def calcular_total(self):
        """Calcula o total do pedido."""
        self.subtotal = sum(item.subtotal for item in self.itens.all())
        self.total = self.subtotal + self.frete - self.desconto
        return self.total

class ItemPedido(models.Model):
    """
    Modelo que representa um item dentro de um pedido.
    Mantém um snapshot dos dados do produto no momento da compra.
    """
    pedido = models.ForeignKey(Pedido, related_name='itens', on_delete=models.CASCADE)
    joia = models.ForeignKey('catalog.Joia', on_delete=models.PROTECT, related_name='itens_venda')
    
    # Snapshot dos dados do produto
    nome_produto = models.CharField(max_length=255)
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2)
    quantidade = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Item do Pedido'
        verbose_name_plural = 'Itens do Pedido'
        db_table = 'vendas_item_pedido'

    def __str__(self):
        return f"{self.quantidade}x {self.nome_produto} em Pedido #{self.pedido.id}"

    def save(self, *args, **kwargs):
        """Calcula o subtotal antes de salvar."""
        self.subtotal = self.preco_unitario * self.quantidade
        super().save(*args, **kwargs)
