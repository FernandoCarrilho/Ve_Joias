# Define os modelos para o domínio de Carrinho.

from django.db import models
from django.db.models import Sum, F
from decimal import Decimal
from django.core.exceptions import ValidationError

# Importação corrigida: Uso de models.Model e carregamento lazy de models
from vejoias.catalog.models import Joia

class Carrinho(models.Model):
    """Modelo de Carrinho de Compras."""
    # O ForeignKey usa lazy loading para evitar dependência circular
    usuario = models.ForeignKey(
        'infrastructure.Usuario',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='carrinhos_app'
    )
    sessao_key = models.CharField(max_length=40, null=True, blank=True)  # Para usuários não autenticados
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Carrinho"
        verbose_name_plural = "Carrinhos"
        db_table = 'carrinho_compras' # Nome de tabela específico
        
    def __str__(self):
        return f"Carrinho #{self.pk} ({'Usuário' if self.usuario else 'Sessão'})"
        
    @property
    def total(self) -> Decimal:
        """Calcula o total do carrinho somando os subtotais dos itens."""
        # Note: A lógica deve considerar Joia.preco (preço base) ou Joia.preco_com_desconto se implementado
        # Usando Joia.preco para manter a consistência com o código original:
        total = self.itens.aggregate(
            total=Sum(F('quantidade') * F('joia__preco'))
        )['total'] or Decimal('0')
        return Decimal(total)

    @property
    def quantidade_itens(self) -> int:
        """Retorna o número total de itens únicos no carrinho."""
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
        db_table = 'carrinho_item' # Nome de tabela específico
        
    def __str__(self):
        return f"{self.quantidade}x {self.joia.nome}"
    
    @property
    def subtotal(self) -> Decimal:
        """Calcula o subtotal do item (preço * quantidade)."""
        # Se você tiver lógica de desconto no Joia, você usaria o preço final aqui
        return self.joia.preco * self.quantidade

    def clean(self):
        """Validações do modelo antes de salvar."""
        if self.quantidade < 1:
            raise ValidationError("A quantidade deve ser maior que zero.")
        if self.quantidade > self.joia.estoque:
            raise ValidationError(f"Quantidade indisponível. Estoque atual: {self.joia.estoque}")
        
    def save(self, *args, **kwargs):
        # Validação extra antes de salvar
        self.full_clean()
        super().save(*args, **kwargs)
