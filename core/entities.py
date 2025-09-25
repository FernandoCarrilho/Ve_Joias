from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Optional

# ====================================================================
# ENTIDADES: Representam os objetos de negócio do domínio.
# Não devem ter lógica de framework, como campos de banco de dados.
# ====================================================================

@dataclass
class Usuario:
    id: Optional[int] = None
    nome_completo: str = ""
    email: str = ""
    telefone: Optional[str] = None
    cpf: Optional[str] = None
    
@dataclass
class Joia:
    id: Optional[int] = None
    nome: str = ""
    descricao: str = ""
    categoria: str = ""  # Ouro, Prata, Bijuteria
    subcategoria: str = "" # Anel, Colar, etc.
    tamanho: Optional[str] = None
    genero: Optional[str] = None # Masculino, Feminino, Unissex
    tipo: Optional[str] = None # Adulto, Infantil
    preco: Decimal = Decimal('0.00')
    estoque: int = 0
    disponivel: bool = True

@dataclass
class ItemCarrinho:
    joia: Joia
    quantidade: int
    
@dataclass
class Carrinho:
    id: Optional[int] = None
    usuario: Optional[Usuario] = None
    itens: List[ItemCarrinho] = field(default_factory=list)
    
@dataclass
class Endereco:
    cep: str
    rua: str
    numero: str
    bairro: str
    cidade: str
    estado: str
    referencia: Optional[str] = None

@dataclass
class Pedido:
    id: Optional[int] = None
    usuario: Usuario
    endereco_entrega: Endereco
    status: str = "PENDENTE"
    transacao_id: Optional[str] = None
    total: Decimal = Decimal('0.00')
