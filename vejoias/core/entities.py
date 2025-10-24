from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional
from datetime import datetime

# ====================================================================
# ENTIDADES - Objetos de Negócio com regras e dados
# ====================================================================

@dataclass
class Endereco:
    """Endereço de entrega ou cobrança."""
    rua: str
    numero: str
    bairro: str
    cidade: str
    estado: str
    cep: str
    complemento: Optional[str] = None

@dataclass
class Usuario:
    """Entidade de Usuário."""
    id: int # ID interno do sistema
    nome: str
    email: str
    # Adicionar outros dados de perfil conforme necessário

@dataclass
class Joia:
    """Entidade de Joia (Produto)."""
    id: int
    nome: str
    descricao: str
    preco: Decimal
    estoque: int
    categoria_slug: str
    data_criacao: datetime = field(default_factory=datetime.now)

@dataclass
class ItemCarrinho:
    """Item dentro do carrinho, referenciando a ID da Joia e a quantidade."""
    joia_id: int
    quantidade: int

@dataclass
class Carrinho:
    """Entidade Carrinho de Compras."""
    usuario_id: int
    itens: List[ItemCarrinho] = field(default_factory=list)

    def calcular_total(self) -> Decimal:
        """
        Método placeholder. O cálculo real deve ser feito no Use Case CriarPedido
        para buscar os preços atuais das Joias no Repositório.
        """
        return Decimal('0.00')

    def itens_para_pedido(self) -> List['ItemPedido']:
        """
        Método placeholder. A criação do snapshot ItemPedido será feita no 
        Use Case CriarPedido após buscar os preços.
        """
        return []

@dataclass
class TransacaoPagamento:
    """Resultado retornado pelo IGatewayPagamento após processar/verificar."""
    referencia_externa: str  # ID da transação no gateway
    valor: Decimal
    status_pagamento: str    # Ex: "APROVADO", "PENDENTE", "REJEITADO"
    data_transacao: datetime
    url_pagamento: Optional[str] = None # Para PIX/Boleto

@dataclass
class ItemPedido:
    """Snapshot de um item no momento em que o pedido foi criado (imutável)."""
    joia_id: int
    nome_joia: str
    preco_unitario: Decimal
    quantidade: int

    def calcular_subtotal(self) -> Decimal:
        return self.preco_unitario * self.quantidade

@dataclass
class Pedido:
    """Entidade de Pedido (Agregado Raiz)."""
    id: Optional[int]
    usuario_id: int
    data_pedido: datetime
    status: str
    total_pedido: Decimal
    tipo_pagamento: str
    endereco_entrega: Endereco
    telefone_whatsapp: str
    itens: List[ItemPedido] = field(default_factory=list)
    transacao_id: Optional[str] = None # ID externa do pagamento

    def calcular_total(self) -> Decimal:
        """Recalcula o total a partir dos itens do snapshot (ItemPedido)."""
        return sum(item.calcular_subtotal() for item in self.itens)
