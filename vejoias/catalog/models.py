from django.db import models
from django.utils.text import slugify

# ====================================================================
# 1. Categoria
# ====================================================================

class Categoria(models.Model):
    """Modelo para agrupar joias (Ex: Colares, Anéis, Brincos)."""
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome da Categoria")
    slug = models.SlugField(max_length=100, unique=True, editable=False)
    descricao = models.TextField(blank=True, verbose_name="Descrição")

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)

# ====================================================================
# 2. Joia (Produto)
# ====================================================================

class Joia(models.Model):
    """Modelo para representar um produto (Joia) no catálogo."""
    
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, related_name='joias')
    
    nome = models.CharField(max_length=255, verbose_name="Nome da Joia")
    slug = models.SlugField(max_length=255, unique=True, editable=False)
    
    descricao = models.TextField(verbose_name="Descrição Detalhada")
    
    # Preço e Estoque
    preco = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço de Venda")
    estoque = models.PositiveIntegerField(default=0, verbose_name="Estoque Atual")
    
    # Imagem (mock-up para a URL, você pode precisar de um campo FileField em produção)
    imagem_url = models.URLField(max_length=500, blank=True, null=True, verbose_name="URL da Imagem Principal")
    
    # Datas
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Joia"
        verbose_name_plural = "Joias"
        ordering = ['nome']
        unique_together = ('categoria', 'nome')

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.categoria.nome}-{self.nome}")
        super().save(*args, **kwargs)
