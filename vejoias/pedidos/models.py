from django.db import models
from django.conf import settings

# A Joia é importada do app catalog
from vejoias.catalog.models import Joia 

class Pedido(models.Model):
    """
    Modelo para pedidos de compra.
    """
    STATUS_CHOICES = [
        ('Pendente', 'Pendente de Pagamento'),
        ('Pago', 'Pago - Processando'),
        ('Enviado', 'Enviado'),
        ('Entregue', 'Entregue'),
        ('Cancelado', 'Cancelado'),
    ]

    PAGAMENTO_CHOICES = [
        ('pix', 'Pix'),
        ('cartao', 'Cartão de Crédito'),
        ('boleto', 'Boleto Bancário'),
    ]

    # FK para o modelo de usuário
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.SET_NULL, 
        null=True, 
        related_name='pedidos',
        verbose_name="Cliente"
    )
    
    data_pedido = models.DateTimeField(auto_now_add=True, verbose_name="Data do Pedido")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pendente', verbose_name="Status")
    
    # Preços
    total_pedido = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Total do Pedido")
    frete = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Valor do Frete") # Adicionado Frete

    # Informações de Pagamento
    tipo_pagamento = models.CharField(max_length=20, choices=PAGAMENTO_CHOICES, default='pix', verbose_name="Método de Pagamento")
    transacao_id = models.CharField(max_length=255, blank=True, null=True, help_text="ID do gateway de pagamento", verbose_name="ID Transação")
    url_pagamento = models.URLField(max_length=500, blank=True, null=True, help_text="URL do Boleto ou QR Code Pix", verbose_name="URL de Pagamento")
    
    # Endereço (Snapshot/Cópia dos dados no momento da compra)
    # Armazena o endereço como JSON, conforme seu modelo original, para imutabilidade do pedido.
    endereco_entrega_json = models.JSONField(verbose_name="Endereço de Entrega (JSON)", help_text="Cópia do endereço no momento do pedido")
    
    # Contato (Snapshot)
    telefone_whatsapp = models.CharField(max_length=20, blank=True, null=True, verbose_name="WhatsApp de Contato")
    
    # Rastreamento
    codigo_rastreio = models.CharField(max_length=50, blank=True, null=True, verbose_name="Código de Rastreio") # Adicionado

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-data_pedido']
        db_table = 'pedido_compra' # Tabela renomeada

    def __str__(self):
        user_info = str(self.usuario) if self.usuario else 'Convidado'
        return f"Pedido {self.id} - {user_info} - {self.status}"
    
    @property
    def total_formatado(self):
        """Total do pedido + Frete, formatado."""
        total_com_frete = self.total_pedido + self.frete
        return f"R$ {total_com_frete:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class ItemPedido(models.Model):
    """
    Modelo para os itens contidos em um pedido.
    """
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens')
    
    # Referência fraca à Joia original
    joia = models.ForeignKey(
        Joia, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True,
        related_name='itens_pedido',
        verbose_name="Joia Original"
    )
    
    # Snapshots (Cópia dos dados da Joia no momento da compra, para histórico)
    nome_joia = models.CharField(max_length=255, verbose_name="Nome da Joia")
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço Unitário na Compra")
    
    quantidade = models.PositiveIntegerField(verbose_name="Quantidade")
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Subtotal")

    class Meta:
        verbose_name = 'Item do Pedido'
        verbose_name_plural = 'Itens do Pedido'
        db_table = 'pedido_item' # Tabela renomeada
        unique_together = ('pedido', 'nome_joia') # Evita itens duplicados no mesmo pedido

    def __str__(self):
        return f"{self.quantidade}x {self.nome_joia} (Pedido {self.pedido.id})"
    
    @property
    def subtotal_formatado(self):
        return f"R$ {self.subtotal:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    
    def save(self, *args, **kwargs):
        # Atualiza o subtotal automaticamente antes de salvar
        self.subtotal = self.quantidade * self.preco_unitario
        super().save(*args, **kwargs)

