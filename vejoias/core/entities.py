from dataclasses import dataclass, field
from decimal import Decimal
from datetime import datetime
from typing import List, Optional, Dict
import uuid

# ====================================================================
# ENTIDADES CORE
# Representam os objetos de negócio puros.
# ====================================================================

@dataclass
class Usuario:
    """Entidade do Usuário, usada como referência para pedidos/carrinhos."""
    nome: str
    email: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
@dataclass
class Endereco:
    """Entidade do Endereço de Entrega/Faturamento."""
    usuario_id: str
    rua: str
    numero: str
    cidade: str
    estado: str
    cep: str
    id: Optional[str] = field(default_factory=lambda: str(uuid.uuid4()))
    complemento: Optional[str] = None
    
@dataclass
class Categoria:
    """Entidade de Categoria de produtos."""
    nome: str
    slug: str
    imagem: Optional[str] = None
    descricao: Optional[str] = None
    em_destaque: bool = False
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class Subcategoria:
    """Entidade de Subcategoria de produtos."""
    nome: str
    slug: str
    categoria_id: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class Joia:
    """Entidade da Joia (Produto) que está sendo vendida."""
    nome: str
    slug: str
    descricao: str
    preco: Decimal
    estoque: int
    categoria_id: str
    subcategoria_id: Optional[str] = None
    desconto: int = 0
    disponivel: bool = True
    em_destaque: bool = False
    imagem_principal: Optional[str] = None
    categoria: Optional[Categoria] = None
    subcategoria: Optional[Subcategoria] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    data_criacao: datetime = field(default_factory=datetime.now)
    data_atualizacao: Optional[datetime] = None
    
    @property
    def preco_com_desconto(self) -> Decimal:
        """Calcula o preço com desconto."""
        if self.desconto:
            return self.preco * (Decimal('1') - Decimal(str(self.desconto)) / Decimal('100'))
        return self.preco

@dataclass
class ItemCarrinho:
    """Entidade que representa um item no carrinho."""
    joia_id: str
    quantidade: int
    preco_unitario: Decimal
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    joia: Optional[Joia] = None

    @property
    def subtotal(self) -> Decimal:
        """Calcula o subtotal do item."""
        return self.preco_unitario * self.quantidade

@dataclass
class Carrinho:
    """Entidade do Carrinho de Compras."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    usuario_id: Optional[str] = None
    sessao_key: Optional[str] = None
    data_criacao: datetime = field(default_factory=datetime.now)
    data_atualizacao: Optional[datetime] = None
    itens: List[ItemCarrinho] = field(default_factory=list)

    @property
    def total(self) -> Decimal:
        """Calcula o total do carrinho."""
        return sum(item.subtotal for item in self.itens)

@dataclass
class ItemPedido:
    """Snapshot de um item no momento da compra (imutável)."""
    pedido_id: str
    joia_id: str
    nome_produto: str
    preco_unitario: Decimal
    quantidade: int
    subtotal: Decimal = field(init=False)

    def __post_init__(self):
        """Calcula o subtotal após a inicialização."""
        self.subtotal = self.preco_unitario * self.quantidade

@dataclass
class TransacaoPagamento:
    """Entidade que registra a comunicação com o Gateway de Pagamento."""
    referencia_externa: str # ID da transação no Pagar.me/Stripe etc.
    status_pagamento: str   # Ex: 'APROVADO', 'REJEITADO', 'PENDENTE'
    valor: Decimal
    metodo: str             # Ex: 'CARTAO', 'PIX'
    data_transacao: datetime = field(default_factory=datetime.now)
    
@dataclass
class Pedido:
    """Entidade do Pedido de Venda."""
    # Campos obrigatórios
    usuario: Usuario
    itens: List[ItemPedido]
    status: str
    total: Decimal
    tipo_pagamento: str
    endereco_entrega: Endereco
    telefone_whatsapp: str
    # Campos opcionais/calculados
    transacao_id: Optional[str] = None
    data_pedido: datetime = field(default_factory=datetime.now)
    id: Optional[str] = field(default_factory=lambda: str(uuid.uuid4()))
    data_modificacao: Optional[datetime] = None
