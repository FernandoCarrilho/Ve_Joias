from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone

# Obtém o modelo de Usuário
User = get_user_model()

# ====================================================================
# 1. Endereco
# ====================================================================

class Endereco(models.Model):
    """Modelo para armazenar endereços de usuários (para faturamento e entrega)."""
    
    # Referência ao usuário, usando string para evitar importação circular
    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='enderecos')
    
    apelido = models.CharField(
        max_length=50, 
        verbose_name="Apelido do Endereço", 
        help_text="Ex: 'Casa', 'Trabalho'."
    )
    
    cep = models.CharField(max_length=9, verbose_name="CEP")
    rua = models.CharField(max_length=255, verbose_name="Rua")
    numero = models.CharField(max_length=10, verbose_name="Número")
    complemento = models.CharField(max_length=100, blank=True, null=True, verbose_name="Complemento")
    bairro = models.CharField(max_length=100, verbose_name="Bairro")
    cidade = models.CharField(max_length=100, verbose_name="Cidade")
    estado = models.CharField(max_length=2, verbose_name="Estado (UF)")
    
    is_principal = models.BooleanField(default=False, verbose_name="Endereço Principal")
    
    class Meta:
        verbose_name = "Endereço"
        verbose_name_plural = "Endereços"
        unique_together = ('usuario', 'apelido')

    def __str__(self):
        return f"{self.apelido} ({self.cidade}/{self.estado})"

# ====================================================================
# 2. Pedido
# ====================================================================

class Pedido(models.Model):
    """Modelo principal para registrar pedidos/compras."""

    STATUS_CHOICES = [
        ('PENDENTE', 'Pagamento Pendente'),
        ('APROVADO', 'Pagamento Aprovado'),
        ('EM_PREPARACAO', 'Em Preparação'),
        ('ENVIADO', 'Enviado'),
        ('ENTREGUE', 'Entregue'),
        ('CANCELADO', 'Cancelado'),
        ('REJEITADO', 'Pagamento Rejeitado'),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE, related_name='pedidos')
    data_pedido = models.DateTimeField(default=timezone.now, verbose_name="Data do Pedido")
    
    # Armazena o endereço como JSON, pois o endereço de entrega
    # é um "snapshot" do momento do pedido e não deve mudar se o Endereco do usuário mudar.
    endereco_entrega_json = models.JSONField(verbose_name="Snapshot do Endereço de Entrega")
    
    valor_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor Total")
    status = models.CharField(
        max_length=20, 
        choices=STATUS_CHOICES, 
        default='PENDENTE', 
        verbose_name="Status do Pedido"
    )

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ['-data_pedido']

    def __str__(self):
        return f"Pedido #{self.pk} - {self.get_status_display()} - Total: R$ {self.valor_total}"

# ====================================================================
# 3. ItemPedido
# ====================================================================

class ItemPedido(models.Model):
    """Modelo para armazenar os itens (joias) que fazem parte de um pedido."""

    # Referência ao Pedido
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens')
    
    # Referência à Joia (Joia deve estar no app 'catalogo')
    # Usando string 'catalogo.Joia' para referência.
    joia = models.ForeignKey('catalogo.Joia', on_delete=models.SET_NULL, null=True) 
    
    # Snapshot dos dados da joia no momento do pedido (importante para relatórios)
    nome_joia = models.CharField(max_length=255, verbose_name="Nome da Joia")
    preco_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço Unitário na Compra")
    
    quantidade = models.PositiveIntegerField(verbose_name="Quantidade")

    class Meta:
        verbose_name = "Item de Pedido"
        verbose_name_plural = "Itens de Pedido"
        unique_together = ('pedido', 'joia') # Uma joia única por pedido

    def __str__(self):
        return f"{self.quantidade}x {self.nome_joia} (Preço: R$ {self.preco_unitario})"
