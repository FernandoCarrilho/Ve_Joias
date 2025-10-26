"""
Módulo de inicialização dos repositórios.
Deve ser importado somente depois que o Django estiver configurado.
"""

from .repositories import (
    JoiaRepositoryDjango as JoiaRepository,
    CarrinhoRepositoryDjango as CarrinhoRepository,
    PedidoRepositoryDjango as PedidoRepository,
    PagamentoGatewayMock as PagamentoGateway
)

# Instâncias globais dos repositórios
joia_repo = JoiaRepository()
carrinho_repo = CarrinhoRepository()
pedido_repo = PedidoRepository()
pagamento_gateway = PagamentoGateway()