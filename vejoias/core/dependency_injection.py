# vejoias/core/dependency_injection.py
"""
Módulo de Injeção de Dependência (DI).
Responsável por instanciar os Use Cases com suas dependências de Repositórios/Gateways
concretos da camada de Infraestrutura.
"""
from vejoias.infrastructure.repositories import (
    JoiaRepositoryDjango, 
    CarrinhoRepositoryDjango, 
    PedidoRepositoryDjango, 
    PagamentoGatewayMock
)
from .use_cases import (
    CriarJoiaUseCase, 
    ListarJoiasUseCase, 
    AtualizarJoiaUseCase, 
    DeletarJoiaUseCase,
    AdicionarItemCarrinhoUseCase,
    RemoverItemCarrinhoUseCase,
    VisualizarCarrinhoUseCase,
    FinalizarPedidoUseCase
)

# Repositórios e Gateways Concretos
joia_repo = JoiaRepositoryDjango()
carrinho_repo = CarrinhoRepositoryDjango()
pedido_repo = PedidoRepositoryDjango()
pagamento_gateway = PagamentoGatewayMock()

# ====================================================================
# Use Cases de Catálogo/Administração
# ====================================================================

def get_criar_joia_use_case() -> CriarJoiaUseCase:
    return CriarJoiaUseCase(joia_repo)

def get_listar_joias_use_case() -> ListarJoiasUseCase:
    return ListarJoiasUseCase(joia_repo)

def get_atualizar_joia_use_case() -> AtualizarJoiaUseCase:
    return AtualizarJoiaUseCase(joia_repo)

def get_deletar_joia_use_case() -> DeletarJoiaUseCase:
    return DeletarJoiaUseCase(joia_repo)


# ====================================================================
# Use Cases de Vendas/Carrinho
# ====================================================================

def get_adicionar_item_carrinho_use_case() -> AdicionarItemCarrinhoUseCase:
    return AdicionarItemCarrinhoUseCase(carrinho_repo, joia_repo)

def get_remover_item_carrinho_use_case() -> RemoverItemCarrinhoUseCase:
    return RemoverItemCarrinhoUseCase(carrinho_repo)

def get_visualizar_carrinho_use_case() -> VisualizarCarrinhoUseCase:
    return VisualizarCarrinhoUseCase(carrinho_repo)

def get_finalizar_pedido_use_case() -> FinalizarPedidoUseCase:
    return FinalizarPedidoUseCase(
        carrinho_repo=carrinho_repo,
        pedido_repo=pedido_repo,
        pagamento_gateway=pagamento_gateway
    )
