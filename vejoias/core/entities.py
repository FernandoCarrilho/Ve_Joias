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
    desconto: int = 0
    em_destaque: bool = False
    imagem_principal: Optional[str] = None
    categoria: Optional[Categoria] = None
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    @property
    def preco_com_desconto(self) -> Decimal:
        """Calcula o preço com desconto."""
        if self.desconto:
            return self.preco * (Decimal('1') - Decimal(str(self.desconto)) / Decimal('100'))
        return self.preco

@dataclass
class ItemCarrinho:
    """Entidade que representa um item no carrinho."""
    joia: Optional[Joia]
    quantidade: int = 0
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def subtotal(self) -> Decimal:
        """Calcula o subtotal do item (preço * quantidade)."""
        return self.joia.preco * self.quantidade if self.joia else Decimal('0')

@dataclass
class Carrinho:
    """Entidade do Carrinho de Compras."""
    usuario: Optional[Usuario] = None
    itens: List[ItemCarrinho] = field(default_factory=list)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    @property
    def total(self) -> Decimal:
        """Calcula o total do carrinho."""
        return sum(item.subtotal for item in self.itens)
    
@dataclass
class CarrinhoItem:
    """Item dentro da Entidade Carrinho."""
    joia_id: str
    quantidade: int

@dataclass
class Carrinho:
    """Entidade Carrinho de Compras, vinculada a um usuário."""
    usuario_id: str
    itens: List[CarrinhoItem] = field(default_factory=list)

    @property
    def total_itens(self) -> int:
        return sum(item.quantidade for item in self.itens)

@dataclass
class ItemPedido:
    """Snapshot de um item no momento da compra (imutável)."""
    joia_id: str
    nome_joia: str
    preco_unitario: Decimal
    quantidade: int

    def calcular_subtotal(self) -> Decimal:
        return self.preco_unitario * self.quantidade

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
    usuario_id: str
    itens: List[ItemPedido]
    total_pedido: Decimal
    status: str
    endereco_entrega: Endereco # Snapshot do endereço no momento da compra
    tipo_pagamento: str
    id: Optional[str] = field(default_factory=lambda: str(uuid.uuid4()))
    telefone_whatsapp: Optional[str] = None
    data_pedido: datetime = field(default_factory=datetime.now)
    transacao_id: Optional[str] = None # Referência à TransacaoPagamento
