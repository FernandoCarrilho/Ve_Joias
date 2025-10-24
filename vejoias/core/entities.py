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
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nome: str
    email: str
    
@dataclass
class Endereco:
    """Entidade do Endereço de Entrega/Faturamento."""
    id: Optional[str] = field(default_factory=lambda: str(uuid.uuid4()))
    usuario_id: str
    rua: str
    numero: str
    cidade: str
    estado: str
    cep: str
    complemento: Optional[str] = None
    
@dataclass
class Joia:
    """Entidade da Joia (Produto) que está sendo vendida."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    nome: str
    descricao: str
    preco: Decimal
    estoque: int
    sku: str
    categoria_slug: str
    
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
    data_transacao: datetime = field(default_factory=datetime.now)
    valor: Decimal
    metodo: str             # Ex: 'CARTAO', 'PIX'
    
@dataclass
class Pedido:
    """Entidade do Pedido de Venda."""
    usuario_id: str
    itens: List[ItemPedido]
    total_pedido: Decimal
    status: str
    endereco_entrega: Endereco # Snapshot do endereço no momento da compra
    tipo_pagamento: str
    telefone_whatsapp: Optional[str] = None
    data_pedido: datetime = field(default_factory=datetime.now)
    transacao_id: Optional[str] = None # Referência à TransacaoPagamento
    id: Optional[str] = field(default_factory=lambda: str(uuid.uuid4()))
