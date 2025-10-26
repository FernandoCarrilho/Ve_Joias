# vejoias/core/ports.py
"""
Definição das Portas (Interfaces/Protocolos) da Arquitetura Limpa.

Estes protocolos definem o contrato que a camada de Infraestrutura (Repositorios, Gateways) 
DEVE seguir para se conectar à camada Core (Casos de Uso).
"""

from typing import Protocol, List, Optional, Dict
from abc import abstractmethod
from decimal import Decimal

# Importa as Entidades que definem o Contrato de Dados
from vejoias.core.entities import (
    Joia, Carrinho, Categoria, Pedido, Usuario, TransacaoPagamento, Endereco, ItemCarrinho
)


# ====================================================================
# 1. REPOSITÓRIOS (Portas de Persistência)
# ====================================================================

class IJoiaRepository(Protocol):
    """Protocolo para a persistência e busca de Joias."""
    
    @abstractmethod
    def buscar_por_id(self, joia_id: str) -> Optional[Joia]: ...

    @abstractmethod
    def buscar_por_criterios(
        self, 
        em_estoque: bool, 
        busca: Optional[str] = None, 
        categoria_slug: Optional[str] = None
    ) -> List[Joia]: ...
    
    @abstractmethod
    def salvar(self, joia: Joia) -> Joia: ...
    
    @abstractmethod
    def atualizar_estoque(self, joia_id: str, quantidade: int): ...
    
    # Opcional para Admin
    @abstractmethod
    def deletar(self, joia_id: str): ...


class ICategoriaRepository(Protocol):
    """Protocolo para a persistência e busca de Categorias."""
    
    @abstractmethod
    def buscar_todas(self) -> List[Categoria]: ...

    @abstractmethod
    def buscar_por_slug(self, slug: str) -> Optional[Categoria]: ...
    
    @abstractmethod
    def salvar(self, categoria: Categoria) -> Categoria: ...


class ICarrinhoRepository(Protocol):
    """Protocolo para a persistência de Carrinhos, manipulando a lógica de sessão/usuário."""
    
    @abstractmethod
    def buscar_ou_criar(self, usuario: Optional[Usuario], sessao_key: Optional[str]) -> Carrinho: ...
    
    @abstractmethod
    def salvar_item(self, carrinho: Carrinho, joia_id: str, quantidade_adicionada: int) -> Carrinho: ...
    
    @abstractmethod
    def remover_item(self, carrinho: Carrinho, joia_id: str) -> Carrinho: ...

    @abstractmethod
    def limpar_carrinho(self, carrinho_id: str): ...


class IPedidoRepository(Protocol):
    """Protocolo para a persistência e gestão de Pedidos."""
    
    @abstractmethod
    def criar_pedido(self, pedido: Pedido, carrinho_id: str, estoque_updates: Dict[str, int]) -> Pedido:
        """
        Cria o pedido, reduz o estoque das joias e limpa o carrinho em uma única transação atômica.
        """
        ...
        
    @abstractmethod
    def buscar_por_id(self, pedido_id: str) -> Optional[Pedido]: ...

    @abstractmethod
    def buscar_por_transacao_id(self, transacao_id: str) -> Optional[Pedido]: ...
    
    @abstractmethod
    def listar_todos_pedidos(self, status: Optional[str] = None) -> List[Pedido]: ...
    
    @abstractmethod
    def listar_pedidos_por_usuario(self, usuario_id: str) -> List[Pedido]: ...

    @abstractmethod
    def atualizar_status(self, pedido_id: str, novo_status: str, id_externo_pagamento: Optional[str] = None) -> Pedido: ...


class IUsuarioRepository(Protocol):
    """Protocolo para a persistência de Usuários."""

    @abstractmethod
    def buscar_por_id(self, usuario_id: str) -> Optional[Usuario]: ...
    
    @abstractmethod
    def buscar_todos(self) -> List[Usuario]: ...


# ====================================================================
# 2. GATEWAYS (Portas de Serviços Externos)
# ====================================================================

class IGatewayPagamento(Protocol):
    """Protocolo para serviços externos de processamento de pagamento."""
    
    @abstractmethod
    def processar_pagamento(self, pedido: Pedido, metodo: str, usuario: Usuario, dados: dict) -> TransacaoPagamento: ...
    
    @abstractmethod
    def verificar_status(self, transacao_id: str) -> TransacaoPagamento: ...


class IEmailService(Protocol):
    """Protocolo para o serviço de envio de e-mails."""
    
    @abstractmethod
    def enviar_confirmacao_pedido(self, pedido: Pedido): ...
    
    @abstractmethod
    def enviar_aprovacao_pagamento(self, pedido: Pedido): ...
    
    # Opcional: Notificação de mudança de status
    @abstractmethod
    def enviar_status_mudanca(self, pedido: Pedido, novo_status: str): ...


class IWhatsappGateway(Protocol):
    """Protocolo para o serviço de envio de mensagens via WhatsApp."""
    
    @abstractmethod
    def enviar_confirmacao_pedido(self, pedido: Pedido, numero_telefone: str): ...
    
    @abstractmethod
    def enviar_aprovacao_pagamento(self, pedido: Pedido, numero_telefone: str): ...
    
    # Opcional: Notificação de mudança de status
    @abstractmethod
    def enviar_status_mudanca(self, pedido: Pedido, novo_status: str, numero_telefone: str): ...
