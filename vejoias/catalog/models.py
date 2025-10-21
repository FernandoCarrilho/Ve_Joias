# vejoias/catalog/models.py
from django.db import models
from django.utils.text import slugify

class Categoria(models.Model):
    """Modelo Django para a Entidade Categoria."""
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome da Categoria")
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    descricao = models.TextField(blank=True, verbose_name="Descrição")

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nome


class Joia(models.Model):
    """Modelo Django para a Entidade Joia (Produto)."""
    nome = models.CharField(max_length=255, verbose_name="Nome da Jóia")
    descricao = models.TextField(verbose_name="Descrição Detalhada")
    
    # Preço e Estoque
    preco = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço Unitário")
    estoque = models.IntegerField(default=0, verbose_name="Quantidade em Estoque")
    
    # Relação com Categoria
    categoria = models.ForeignKey(
        Categoria, 
        on_delete=models.SET_NULL, # Mantém a joia se a categoria for deletada
        null=True, 
        blank=True, 
        related_name='joias'
    )
    
    # Detalhes Físicos (Material, Peso, Dimensões)
    material = models.CharField(max_length=100, blank=True, verbose_name="Material Principal")
    peso_gramas = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True, verbose_name="Peso (g)")
    dimensoes = models.CharField(max_length=150, blank=True, verbose_name="Dimensões (cm)")
    
    # Imagem (simplificado para URL, conforme a Entidade)
    imagem_url = models.URLField(max_length=500, blank=True, verbose_name="URL da Imagem Principal")
    
    # Atributos de Loja
    is_destaque = models.BooleanField(default=False, verbose_name="Destaque na Home")
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Joia"
        verbose_name_plural = "Joias"
        ordering = ['nome']
        
    def __str__(self):
        return self.nome

    @property
    def em_estoque(self) -> bool:
        """Verifica se há estoque disponível."""
        return self.estoque > 0
