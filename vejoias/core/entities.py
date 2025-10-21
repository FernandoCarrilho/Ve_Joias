# vejoias/core/entities.py
# Define as entidades de domínio (Core Entities) que representam os conceitos de negócio
# e são independentes da infraestrutura (Django Models).

from dataclasses import dataclass, field
from decimal import Decimal
from typing import List

# --- EXCEÇÕES DE DOMÍNIO ---

class EstoqueInsuficienteError(Exception):
    """Exceção levantada quando a quantidade de um item excede o estoque disponível."""
    def __init__(self, joia_id: int, solicitada: int, disponivel: int):
        self.joia_id = joia_id
        self.solicitada = solicitada
        self.disponivel = disponivel
        super().__init__(f"Estoque insuficiente para a jóia {joia_id}. Solicitado: {solicitada}, Disponível: {disponivel}.")

# --- ENTIDADES DE DOMÍNIO ---

@dataclass
class Endereco:
    """
    Representa o endereço de entrega ou faturamento do cliente.
    Usado para desacoplar a lógica de negócio do modelo de banco de dados.
    """
    rua: str
    numero: str
    bairro: str
    cidade: str
    estado: str
    cep: str
    referencia: str = field(default="")
    telefone: str = field(default="") # Telefone WhatsApp usado no CheckoutForm

    def formatar(self) -> str:
        """Retorna o endereço formatado para exibição."""
        return f"{self.rua}, {self.numero}, {self.bairro} - {self.cidade}/{self.estado} (CEP: {self.cep})"


@dataclass
class ItemCarrinho:
    """Representa um único item dentro do carrinho de compras."""
    joia_id: int
    nome: str
    preco_unitario: Decimal
    quantidade: int

    @property
    def subtotal(self) -> Decimal:
        """Calcula o subtotal deste item."""
        return self.preco_unitario * self.quantidade


@dataclass
class Carrinho:
    """
    Representa o carrinho de compras de um usuário.
    Contém a lógica de cálculo e manipulação de itens.
    """
    usuario_id: int
    itens: List[ItemCarrinho] = field(default_factory=list)

    def adicionar_item(self, item: ItemCarrinho):
        """Adiciona ou atualiza um item no carrinho."""
        # Lógica de agrupamento/atualização (simplificada)
        for i in self.itens:
            if i.joia_id == item.joia_id:
                i.quantidade += item.quantidade
                return

        self.itens.append(item)

    def remover_item(self, joia_id: int):
        """Remove um item do carrinho."""
        self.itens = [item for item in self.itens if item.joia_id != joia_id]

    @property
    def subtotal(self) -> Decimal:
        """Calcula o subtotal de todos os itens no carrinho."""
        return sum(item.subtotal for item in self.itens)

    @property
    def total_itens(self) -> int:
        """Retorna o número total de itens (unidades) no carrinho."""
        return sum(item.quantidade for item in self.itens)

    def calcular_frete(self) -> Decimal:
        """Lógica placeholder para cálculo de frete."""
        # Pode ser substituído por uma chamada a um serviço externo
        return Decimal('30.00')

    @property
    def total_geral(self) -> Decimal:
        """Calcula o valor total do pedido (subtotal + frete)."""
        return self.subtotal + self.calcular_frete()
