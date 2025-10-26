from django.db import models
from django.utils.text import slugify

# ====================================================================
# 1. Categoria
# ====================================================================

class Categoria(models.Model):
    """Modelo para agrupar joias (Ex: Colares, Anéis, Brincos)."""
    nome = models.CharField(max_length=100, unique=True, verbose_name="Nome da Categoria")
    slug = models.SlugField(max_length=100, unique=True, editable=False)
    
    # Campos Adicionados:
    imagem = models.ImageField(upload_to='categorias/', blank=True, null=True, verbose_name="Imagem da Categoria")
    descricao = models.TextField(blank=True, verbose_name="Descrição")
    em_destaque = models.BooleanField(default=False, verbose_name="Em Destaque na Home")

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"
        db_table = 'catalogo_categoria' # Nome de tabela específico
        ordering = ['nome']

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nome)
        super().save(*args, **kwargs)

# ====================================================================
# 2. Subcategoria
# ====================================================================

class Subcategoria(models.Model):
    """Modelo para subcategorias de joias (Ex: Anéis de Noivado, Correntes de Ouro)."""
    # FK para Categoria
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='subcategorias')
    
    nome = models.CharField(max_length=100, verbose_name="Nome da Subcategoria")
    slug = models.SlugField(max_length=100, unique=True, editable=False)
    descricao = models.TextField(blank=True, verbose_name="Descrição") # Mantido do seu código

    class Meta:
        verbose_name = "Subcategoria"
        verbose_name_plural = "Subcategorias"
        unique_together = ('categoria', 'nome')
        db_table = 'catalogo_subcategoria' # Nome de tabela específico

    def __str__(self):
        return f"{self.categoria.nome} - {self.nome}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(f"{self.categoria.nome}-{self.nome}")
        super().save(*args, **kwargs)

# ====================================================================
# 3. Joia (Produto)
# ====================================================================

class Joia(models.Model):
    """Modelo para representar um produto (Joia) no catálogo."""
    
    # Foreign Keys
    categoria = models.ForeignKey(Categoria, on_delete=models.SET_NULL, null=True, related_name='joias')
    
    # CORREÇÃO CRÍTICA: related_name deve ser único para Joia.subcategoria
    subcategoria = models.ForeignKey(
        Subcategoria, 
        on_delete=models.SET_NULL, 
        null=True, 
        blank=True, # Adicionado blank=True para flexibilidade
        related_name='joias_subcategoria' # Corrigido para evitar conflito
    )
    
    nome = models.CharField(max_length=255, verbose_name="Nome da Joia")
    slug = models.SlugField(max_length=255, unique=True, editable=False)
    descricao = models.TextField(verbose_name="Descrição Detalhada")
    
    # Preço, Estoque e Disponibilidade
    preco = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço de Venda")
    desconto = models.PositiveIntegerField(default=0, help_text='Desconto em porcentagem') # Adicionado
    estoque = models.PositiveIntegerField(default=0, verbose_name="Estoque Atual")
    disponivel = models.BooleanField(default=True) # Adicionado
    em_destaque = models.BooleanField(default=False) # Adicionado
    
    # Imagem
    # Substituído imagem_url por imagem_principal (ImageField)
    imagem_principal = models.ImageField(upload_to='joias/', blank=True, null=True, verbose_name="Imagem Principal")
    
    # Datas
    data_criacao = models.DateTimeField(auto_now_add=True)
    data_atualizacao = models.DateTimeField(auto_now=True, null=True)

    class Meta:
        verbose_name = "Joia"
        verbose_name_plural = "Joias"
        ordering = ['nome']
        # unique_together = ('categoria', 'nome') # Removido se for dificultar migrações iniciais, mas mantido se preferir

        db_table = 'catalogo_joia' # Nome de tabela específico

    def __str__(self):
        return self.nome

    def save(self, *args, **kwargs):
        if not self.slug:
            # Garante que o slug é gerado mesmo sem subcategoria
            slug_base = self.categoria.nome if self.categoria else 'sem-categoria'
            self.slug = slugify(f"{slug_base}-{self.nome}")
        super().save(*args, **kwargs)
        
    @property
    def preco_formatado(self):
        """Retorna o preço formatado em Real Brasileiro."""
        return f"R$ {self.preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
