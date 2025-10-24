# vejoias/core/entities.py
# Define as Entidades de Domínio puras, que encapsulam as regras de negócio
# e são independentes de qualquer framework (como o Django ORM).

from dataclasses import dataclass
from typing import Optional, List
from datetime import datetime
from decimal import Decimal

# O uso de 'Decimal' é crucial para manter a precisão monetária.

@dataclass(frozen=True)
class Endereco:
    """Entidade que representa um endereço físico."""
    cep: str
    rua: str
    numero: str
    bairro: str
    cidade: str
    estado: str
    referencia: Optional[str] = None
    principal: bool = False
    id: Optional[int] = None

@dataclass(frozen=True)
class Usuario:
    """Entidade que representa um Usuário do sistema."""
    email: str
    first_name: str
    last_name: str
    id: Optional[int] = None
    telefone: Optional[str] = None
    cpf: Optional[str] = None
    is_active: bool = True
    is_staff: bool = False
    is_superuser: bool = False

@dataclass(frozen=True)
class Categoria:
    """Entidade que representa uma Categoria de produto."""
    nome: str
    slug: str
    id: Optional[int] = None

@dataclass(frozen=True)
class Subcategoria:
    """Entidade que representa uma Subcategoria de produto."""
    nome: str
    slug: str
    categoria_id: int
    id: Optional[int] = None

@dataclass(frozen=True)
class Joia:
    """Entidade que representa um produto (Joia) na loja."""
    nome: str
    preco: Decimal
    estoque: int
    id: Optional[int] = None
    descricao: Optional[str] = None
    disponivel: bool = True
    imagem: Optional[str] = None
    categoria_id: Optional[int] = None
    subcategoria_id: Optional[int] = None
    criado_em: Optional[datetime] = None
    atualizado_em: Optional[datetime] = None

@dataclass(frozen=True)
class ItemCarrinho:
    """Entidade que representa um item dentro do Carrinho."""
    joia_id: int
    quantidade: int
    id: Optional[int] = None
    preco_unitario: Optional[Decimal] = None
    subtotal: Optional[Decimal] = None

@dataclass(frozen=True)
class Carrinho:
    """Entidade que representa o Carrinho de Compras, contendo itens."""
    itens: List[ItemCarrinho]
    id: Optional[int] = None
    usuario_id: Optional[int] = None
    sessao_key: Optional[str] = None
    data_criacao: Optional[datetime] = None
    data_atualizacao: Optional[datetime] = None

    @property
    def total_carrinho(self) -> Decimal:
        """Calcula o total baseado nos subtotais dos itens."""
        return sum(item.subtotal for item in self.itens if item.subtotal is not None)

@dataclass(frozen=True)
class ItemPedido:
    """Entidade que representa um item dentro de um Pedido (snapshot de dados)."""
    joia_nome: str
    joia_preco: Decimal
    quantidade: int
    subtotal: Decimal
    id: Optional[int] = None
    pedido_id: Optional[int] = None

@dataclass(frozen=True)
class TransacaoPagamento:
    """Entidade que representa uma transação de pagamento."""
    pedido_id: int
    valor: Decimal
    data_transacao: datetime
    metodo_pagamento: str # Ex: 'PIX', 'Cartao', 'Boleto'
    status_pagamento: str # Ex: 'Pendente', 'Aprovado', 'Falhou'
    id: Optional[int] = None
    referencia_externa: Optional[str] = None # ID da transação no gateway

@dataclass(frozen=True)
class Pedido:
    """Entidade que representa um Pedido concluído."""
    data_pedido: datetime
    status: str
    total_pedido: Decimal
    tipo_pagamento: str
    cep_entrega: str
    rua_entrega: str
    numero_entrega: str
    bairro_entrega: str
    cidade_entrega: str
    estado_entrega: str
    telefone_whatsapp: str
    id: Optional[int] = None
    usuario_id: Optional[int] = None
    referencia_entrega: Optional[str] = None
    itens: Optional[List[ItemPedido]] = None
    transacao: Optional[TransacaoPagamento] = None
