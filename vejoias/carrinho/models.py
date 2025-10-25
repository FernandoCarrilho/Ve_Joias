from django.db import models
from django.db.models import Sum, F
from decimal import Decimal
from vejoias.catalog.models import Joia

class Carrinho(models.Model):
    """Modelo de Carrinho de Compras."""
    usuario = models.ForeignKey('infrastructure.Usuario', on_delete=models.CASCADE, null=True, blank=True, related_name='carrinhos_app')
    sessao_key = models.CharField(max_length=40, null=True, blank=True)  # Para usuários não autenticados
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Carrinho"
        verbose_name_plural = "Carrinhos"
        
    def __str__(self):
        return f"Carrinho #{self.pk}"
        
    @property
    def total(self) -> Decimal:
        """Calcula o total do carrinho somando os subtotais dos itens."""
        total = self.itens.aggregate(
            total=Sum(F('quantidade') * F('joia__preco'))
        )['total'] or Decimal('0')
        return Decimal(total)

    @property
    def quantidade_itens(self) -> int:
        """Retorna o número total de itens no carrinho."""
        return self.itens.count()

    @property
    def quantidade_total(self) -> int:
        """Retorna a soma das quantidades de todos os itens."""
        total = self.itens.aggregate(total=Sum('quantidade'))['total']
        return total or 0

class ItemCarrinho(models.Model):
    """Modelo para os itens dentro do carrinho."""
    carrinho = models.ForeignKey(Carrinho, on_delete=models.CASCADE, related_name='itens')
    joia = models.ForeignKey(Joia, on_delete=models.CASCADE)
    quantidade = models.PositiveIntegerField(default=1)
    data_adicao = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = "Item do Carrinho"
        verbose_name_plural = "Itens do Carrinho"
        unique_together = ('carrinho', 'joia')  # Evita duplicatas
        ordering = ['data_adicao']
        
    def __str__(self):
        return f"{self.quantidade}x {self.joia.nome}"
    
    @property
    def subtotal(self) -> Decimal:
        """Calcula o subtotal do item (preço * quantidade)."""
        return self.joia.preco * self.quantidade

    def clean(self):
        """Validações do modelo antes de salvar."""
        from django.core.exceptions import ValidationError
        if self.quantidade < 1:
            raise ValidationError("A quantidade deve ser maior que zero.")
        if self.quantidade > self.joia.estoque:
            raise ValidationError(f"Quantidade indisponível. Estoque atual: {self.joia.estoque}")
