# vejoias/core/interfaces.py
"""
Camada Core: Interfaces Abstratas (Contratos)

Define os contratos (Interfaces) que a camada de Infraestrutura
(Infrastructure) deve cumprir. O Core NÃO tem conhecimento de 
como essas operações são implementadas (se é com Django ORM, SQL puro, APIs externas, etc.).
"""
from abc import ABC, abstractmethod
from typing import List, Optional
# Importamos as Entidades para tipagem, pois elas são puras e não têm dependências
from .entities import Joia, Carrinho, Pedido, Usuario, TransacaoPagamento

# ====================================================================
# 1. REPOSITÓRIOS (Persistência de Dados)
# ====================================================================

class BaseRepositoryInterface(ABC):
    """Interface Base para todos os Repositórios."""
    
    @abstractmethod
    def salvar(self, entidade):
        """Salva ou atualiza uma Entidade no banco de dados."""
        pass
        
    @abstractmethod
    def buscar_por_id(self, id: int):
        """Busca uma Entidade pelo seu ID."""
        pass


class JoiaRepositoryInterface(BaseRepositoryInterface):
    """Contrato para persistência e recuperação de Entidades Joia."""
    
    @abstractmethod
    def salvar(self, joia: Joia) -> Joia:
        """Salva ou atualiza uma Joia."""
        pass

    @abstractmethod
    def buscar_por_id(self, id: int) -> Optional[Joia]:
        """Busca uma Joia pelo ID."""
        pass
        
    @abstractmethod
    def buscar_por_criterios(
        self, 
        em_estoque: bool, 
        busca: Optional[str] = None, 
        categoria_slug: Optional[str] = None
    ) -> List[Joia]:
        """Busca joias com filtros complexos (ex: estoque, nome/descrição, categoria)."""
        pass
        
    @abstractmethod
    def deletar(self, joia_id: int):
        """Remove uma Joia do banco de dados."""
        pass


class CarrinhoRepositoryInterface(BaseRepositoryInterface):
    """Contrato para persistência e recuperação de Entidades Carrinho e ItemCarrinho."""
    
    @abstractmethod
    def salvar(self, carrinho: Carrinho) -> Carrinho:
        """Salva ou atualiza o carrinho (e seus itens)."""
        pass
        
    @abstractmethod
    def buscar_por_usuario(self, usuario: Usuario) -> Carrinho:
        """Busca o carrinho ativo de um usuário."""
        # Se não houver carrinho, o Repositório DEVE retornar um novo Carrinho vazio.
        pass
        
    @abstractmethod
    def limpar_carrinho(self, usuario: Usuario):
        """Remove todos os itens do carrinho após um checkout bem-sucedido."""
        pass


class PedidoRepositoryInterface(BaseRepositoryInterface):
    """Contrato para persistência e recuperação de Entidades Pedido."""
    
    @abstractmethod
    def salvar(self, pedido: Pedido) -> Pedido:
        """Salva ou atualiza um Pedido."""
        pass
        
    @abstractmethod
    def buscar_por_id(self, id: int) -> Optional[Pedido]:
        """Busca um Pedido pelo ID."""
        pass

    @abstractmethod
    def listar(self, usuario: Optional[Usuario] = None) -> List[Pedido]:
        """Lista pedidos. Se usuário for fornecido, lista apenas os dele."""
        pass


# ====================================================================
# 2. GATEWAYS (Serviços Externos/Infraestrutura)
# ====================================================================

class PagamentoGatewayInterface(ABC):
    """Contrato para comunicação com serviços externos de pagamento (ex: PayPal, Stripe, etc.)."""
    
    @abstractmethod
    def processar_pagamento(self, pedido: Pedido, metodo: str, dados: dict) -> TransacaoPagamento:
        """
        Envia os dados de pagamento para o gateway externo.
        Retorna uma entidade TransacaoPagamento com o status e detalhes.
        """
        pass
        
    @abstractmethod
    def verificar_status(self, transacao_id: str) -> TransacaoPagamento:
        """Consulta o status de uma transação pendente."""
        pass
