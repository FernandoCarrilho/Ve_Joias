from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.translation import gettext_lazy as _
from django.conf import settings

class Usuario(AbstractUser):
    """
    Modelo de usuário personalizado que herda do AbstractUser do Django
    para gerenciar a autenticação. É o modelo de infraestrutura para a entidade 'Usuario'.
    """
    class TipoUsuario(models.TextChoices):
        CLIENTE = 'CLIENTE', _('Cliente')
        VENDEDOR = 'VENDEDOR', _('Vendedor')

    tipo_usuario = models.CharField(
        _("tipo de usuário"),
        max_length=10,
        choices=TipoUsuario.choices,
        default=TipoUsuario.CLIENTE,
        help_text=_("Define o tipo de acesso do usuário no sistema.")
    )
    telefone = models.CharField(_("telefone"), max_length=15, blank=True, null=True)

    # Campos de grupos e permissões com related_name únicos para evitar conflitos
    # com o modelo User padrão do Django.
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='vejoias_usuarios_groups',
        blank=True,
        help_text=_('Os grupos aos quais este usuário pertence.')
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='vejoias_usuarios_permissions',
        blank=True,
        help_text=_('Permissões específicas para este usuário.')
    )

    def __str__(self):
        return self.get_full_name() or self.username

    class Meta:
        verbose_name = _("usuário")
        verbose_name_plural = _("usuários")


class Joia(models.Model):
    """
    Modelo para representar uma joia no catálogo.
    Corresponde à entidade 'Joia' da camada de domínio.
    """
    class Categoria(models.TextChoices):
        OURO = 'OURO', _('Ouro')
        PRATA = 'PRATA', _('Prata')
        BIJUTERIA = 'BIJUTERIA', _('Bijuteria')
        
    class Subcategoria(models.TextChoices):
        ANEIS = 'ANEIS', _('Anéis')
        PULSEIRAS = 'PULSEIRAS', _('Pulseiras')
        COLARES = 'COLARES', _('Colares')
        BRINCOS = 'BRINCOS', _('Brincos')
        TORNOZELEIRAS = 'TORNOZELEIRAS', _('Tornozeleiras')

    nome = models.CharField(_("nome"), max_length=100)
    descricao = models.TextField(_("descrição"), blank=True, null=True)
    preco = models.DecimalField(_("preço"), max_digits=10, decimal_places=2)
    estoque = models.IntegerField(_("estoque"), default=0)
    imagem_url = models.URLField(_("URL da imagem"), max_length=500, blank=True, null=True)
    disponivel = models.BooleanField(_("disponível"), default=True)
    
    categoria = models.CharField(
        _("categoria"),
        max_length=10,
        choices=Categoria.choices
    )
    subcategoria = models.CharField(
        _("subcategoria"),
        max_length=15,
        choices=Subcategoria.choices
    )
    
    tamanho = models.CharField(_("tamanho"), max_length=20, blank=True, null=True)
    genero = models.CharField(_("gênero"), max_length=20, blank=True, null=True)
    tipo_publico = models.CharField(_("público"), max_length=20, blank=True, null=True,
                                  choices=[('ADULTO', 'Adulto'), ('INFANTIL', 'Infantil')])
    
    data_cadastro = models.DateTimeField(_("data de cadastro"), auto_now_add=True)

    def __str__(self):
        return self.nome

    class Meta:
        verbose_name = _("jóia")
        verbose_name_plural = _("jóias")
        ordering = ['nome']


class Endereco(models.Model):
    """
    Modelo para representar o endereço de entrega do cliente.
    Corresponde à entidade 'Endereco'.
    """
    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='enderecos',
        help_text=_("Usuário associado a este endereço.")
    )
    cep = models.CharField(_("CEP"), max_length=9)
    rua = models.CharField(_("rua"), max_length=255)
    numero = models.CharField(_("número"), max_length=10)
    bairro = models.CharField(_("bairro"), max_length=100)
    cidade = models.CharField(_("cidade"), max_length=100)
    estado = models.CharField(_("estado"), max_length=20)
    referencia = models.TextField(_("referência"), blank=True, null=True)

    def __str__(self):
        return f"{self.rua}, {self.numero} - {self.cidade}"

    class Meta:
        verbose_name = _("endereço")
        verbose_name_plural = _("endereços")
        

class Carrinho(models.Model):
    """
    Modelo para representar o carrinho de compras do usuário.
    Corresponde à entidade 'Carrinho'.
    """
    usuario = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='carrinho',
        verbose_name=_("usuário"),
        help_text=_("O carrinho pertence a um único usuário.")
    )

    def __str__(self):
        return f"Carrinho de {self.usuario.username}"

    class Meta:
        verbose_name = _("carrinho")
        verbose_name_plural = _("carrinhos")


class ItemCarrinho(models.Model):
    """
    Modelo para os itens dentro do carrinho, relacionando-o a uma joia.
    Corresponde à entidade 'ItemCarrinho'.
    """
    carrinho = models.ForeignKey(
        Carrinho,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name=_("carrinho")
    )
    joia = models.ForeignKey(
        Joia,
        on_delete=models.CASCADE,
        related_name='itens_carrinho',
        verbose_name=_("jóia")
    )
    quantidade = models.PositiveIntegerField(_("quantidade"))

    def __str__(self):
        return f"{self.quantidade} x {self.joia.nome} em {self.carrinho.usuario.username}'s carrinho"

    class Meta:
        verbose_name = _("item de carrinho")
        verbose_name_plural = _("itens de carrinho")
        unique_together = ('carrinho', 'jóia')


class Pedido(models.Model):
    """
    Modelo para representar um pedido realizado.
    Corresponde à entidade 'Pedido'.
    """
    class StatusPedido(models.TextChoices):
        PENDENTE = 'PENDENTE', _('Pendente')
        PAGO = 'PAGO', _('Pago')
        EM_ENVIO = 'EM_ENVIO', _('Em Envio')
        ENTREGUE = 'ENTREGUE', _('Entregue')
        CANCELADO = 'CANCELADO', _('Cancelado')

    usuario = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='pedidos',
        verbose_name=_("usuário")
    )
    endereco_entrega = models.ForeignKey(
        Endereco,
        on_delete=models.PROTECT,  # Mantém o endereço mesmo se o cliente o deletar
        related_name='pedidos',
        verbose_name=_("endereço de entrega")
    )
    data_criacao = models.DateTimeField(_("data de criação"), auto_now_add=True)
    status = models.CharField(
        _("status"),
        max_length=10,
        choices=StatusPedido.choices,
        default=StatusPedido.PENDENTE
    )
    total = models.DecimalField(_("total"), max_digits=10, decimal_places=2)
    transacao_id = models.CharField(_("ID da transação"), max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Pedido #{self.id} de {self.usuario.username}"

    class Meta:
        verbose_name = _("pedido")
        verbose_name_plural = _("pedidos")
        ordering = ['-data_criacao']


class ItemPedido(models.Model):
    """
    Modelo para os itens de um pedido.
    Funciona como uma tabela de junção entre Pedido e Joia.
    """
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name='itens',
        verbose_name=_("pedido")
    )
    joia = models.ForeignKey(
        Joia,
        on_delete=models.PROTECT,  # Não permite a exclusão de uma joia se estiver em um pedido
        related_name='itens_pedido',
        verbose_name=_("jóia")
    )
    quantidade = models.PositiveIntegerField(_("quantidade"))
    preco_unitario = models.DecimalField(_("preço unitário"), max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.quantidade} x {self.joia.nome}"

    class Meta:
        verbose_name = _("item de pedido")
        verbose_name_plural = _("itens de pedido")
        unique_together = ('pedido', 'jóia')
        ordering = ['pedido']
