# vejoias/infrastructure/models.py
# Define os modelos do banco de dados para a camada de infraestrutura.

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from vejoias.core.entities import Endereco as EnderecoEntity

# ====================================================================
# GERENCIADOR DE USUÁRIOS PERSONALIZADO (Para usar email como login)
# ====================================================================

class CustomUserManager(BaseUserManager):
    """
    Gerenciador de modelos de usuário onde o email é o identificador único
    para autenticação, em vez dos nomes de usuário.
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('O e-mail deve ser definido')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Cria e salva um Superusuário com o e-mail e senha fornecidos.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


# ====================================================================
# MODELOS DE DADOS DA APLICAÇÃO
# ====================================================================

class Usuario(AbstractUser):
    """
    Modelo de Usuário Personalizado que utiliza o campo 'email' como identificador
    principal para login, em vez de 'username'.
    """
    # Remove o campo username padrão
    username = None 

    # Define o email como único e obrigatório
    email = models.EmailField('Endereço de E-mail', unique=True)
    
    # Campos adicionais do perfil
    telefone = models.CharField(max_length=15, blank=True, null=True)
    cpf = models.CharField('CPF', max_length=14, unique=True, blank=True, null=True)

    # Campos necessários para login/autenticação
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name'] # Campos que serão perguntados ao criar superuser

    # Utiliza o gerenciador de usuários personalizado
    objects = CustomUserManager()

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        # Define a tabela onde este modelo reside
        db_table = 'usuario'

    def __str__(self):
        return self.email

class Endereco(models.Model):
    """
    Modelo para armazenar endereços de entrega e faturamento.
    """
    usuario = models.ForeignKey(Usuario, on_delete=models.CASCADE, related_name='enderecos')
    cep = models.CharField(max_length=10)
    rua = models.CharField(max_length=255)
    numero = models.CharField(max_length=10)
    bairro = models.CharField(max_length=100)
    cidade = models.CharField(max_length=100)
    estado = models.CharField(max_length=50)
    referencia = models.CharField(max_length=255, blank=True, null=True)
    principal = models.BooleanField(default=False) # Define se é o endereço padrão

    class Meta:
        verbose_name = 'Endereço'
        verbose_name_plural = 'Endereços'
        db_table = 'endereco'

    def __str__(self):
        return f"{self.rua}, {self.numero} - {self.cidade}"
    
    def to_entity(self) -> EnderecoEntity:
        """Converte o Model Django para a Entidade de Domínio."""
        return EnderecoEntity(
            cep=self.cep,
            rua=self.rua,
            numero=self.numero,
            bairro=self.bairro,
            cidade=self.cidade,
            estado=self.estado,
            referencia=self.referencia
        )


class Categoria(models.Model):
    """
    Modelo para categorias das joias (Ex: Colares, Anéis).
    """
    nome = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=100, unique=True)

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'
        db_table = 'categoria'

    def __str__(self):
        return self.nome

class Subcategoria(models.Model):
    """
    Modelo para subcategorias das joias (Ex: Ouro 18K, Prata 925).
    """
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='subcategorias')
    nome = models.CharField(max_length=100)
    slug = models.SlugField(max_length=100)

    class Meta:
        verbose_name = 'Subcategoria'
        verbose_name_plural = 'Subcategorias'
        unique_together = ('categoria', 'slug')
        db_table = 'subcategoria'

    def __str__(self):
        return f"{self.categoria.nome} - {self.nome}"


class Joia(models.Model):
    """
    Modelo principal para os produtos da loja.
    """
    nome = models.CharField(max_length=255)
    descricao = models.TextField()
    preco = models.DecimalField(max_digits=10, decimal_places=2)
    estoque = models.IntegerField(default=0)
    disponivel = models.BooleanField(default=True)
    imagem = models.URLField(max_length=500, blank=True, null=True) # URL da imagem
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='joias')
    subcategoria = models.ForeignKey(Subcategoria, on_delete=models.SET_NULL, null=True, blank=True, related_name='joias')
    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Joia'
        verbose_name_plural = 'Joias'
        ordering = ['nome']
        db_table = 'joia'

    def __str__(self):
        return self.nome
    
    @property
    def preco_formatado(self):
        return f"R$ {self.preco:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


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

    usuario = models.ForeignKey(Usuario, on_delete=models.SET_NULL, null=True, related_name='pedidos')
    data_pedido = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Pendente')
    total_pedido = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Informações de Pagamento
    tipo_pagamento = models.CharField(max_length=20, choices=PAGAMENTO_CHOICES, default='pix')
    
    # Informações de Endereço (Snapshot)
    cep_entrega = models.CharField(max_length=10)
    rua_entrega = models.CharField(max_length=255)
    numero_entrega = models.CharField(max_length=10)
    bairro_entrega = models.CharField(max_length=100)
    cidade_entrega = models.CharField(max_length=100)
    estado_entrega = models.CharField(max_length=50)
    referencia_entrega = models.CharField(max_length=255, blank=True, null=True)
    
    # Contato para WhatsApp
    telefone_whatsapp = models.CharField(max_length=15)

    class Meta:
        verbose_name = 'Pedido'
        verbose_name_plural = 'Pedidos'
        ordering = ['-data_pedido']
        db_table = 'pedido'

    def __str__(self):
        return f"Pedido {self.id} - {self.usuario.email if self.usuario else 'Convidado'} - {self.status}"
    
    @property
    def total_formatado(self):
        return f"R$ {self.total_pedido:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


class ItemPedido(models.Model):
    """
    Modelo para os itens contidos em um pedido.
    """
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='itens')
    joia_nome = models.CharField(max_length=255) # Snapshot do nome
    joia_preco = models.DecimalField(max_digits=10, decimal_places=2) # Snapshot do preço
    quantidade = models.IntegerField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        verbose_name = 'Item do Pedido'
        verbose_name_plural = 'Itens do Pedido'
        db_table = 'item_pedido'

    def __str__(self):
        return f"{self.quantidade}x {self.joia_nome} (Pedido {self.pedido.id})"
    
    @property
    def subtotal_formatado(self):
        return f"R$ {self.subtotal:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

# O modelo ProfileUsuario foi integrado ao modelo Usuario usando o AbstractUser.
