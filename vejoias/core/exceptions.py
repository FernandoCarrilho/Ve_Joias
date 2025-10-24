# vejoias/core/exceptions.py
# Define exceções personalizadas para o domínio da aplicação.

class ApplicationError(Exception):
    """Exceção base para todos os erros da Aplicação (incluindo Core e Infra)."""
    pass

class CoreException(ApplicationError):
    """Exceção base para todos os erros de domínio (Core)."""
    pass

# --- Exceções de Entidades Não Encontradas ---

class UsuarioNaoEncontradoError(CoreException):
    """Levantada quando um Usuário específico não é encontrado."""
    pass

class JoiaNaoEncontradaError(CoreException):
    """Levantada quando uma Joia (Produto) específica não é encontrada."""
    pass

class CategoriaNaoEncontradaError(CoreException):
    """Levantada quando uma Categoria específica não é encontrada."""
    pass

class PedidoNaoEncontradoError(CoreException):
    """Levantada quando um Pedido específico não é encontrado."""
    pass

class ItemNaoEncontradoError(CoreException):
    """Levantada quando um Item de Carrinho ou Item de Pedido não é encontrado."""
    pass

# --- Exceções de Regras de Negócio ---

class EstoqueInsuficienteError(CoreException):
    """Levantada quando a quantidade solicitada de um item excede o estoque disponível."""
    pass

class CarrinhoVazioError(CoreException):
    """Levantada ao tentar finalizar um carrinho que está vazio."""
    pass

class DadosInvalidosError(CoreException):
    """Levantada quando dados de entrada não são válidos para uma operação de domínio."""
    pass

class StatusInvalidoError(CoreException):
    """Levantada quando é fornecido um status inválido para uma transição ou atualização."""
    pass

class PagamentoFalhouError(CoreException):
    """Levantada quando o processamento de pagamento falha."""
    pass
