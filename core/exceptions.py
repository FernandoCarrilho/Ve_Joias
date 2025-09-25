# vejoias/core/exceptions.py

class EstoqueInsuficienteError(Exception):
    """
    Exceção levantada quando um item não pode ser adicionado ao carrinho
    devido à falta de estoque.
    """
    pass

class ItemNaoEncontradoError(Exception):
    """
    Exceção levantada quando um item específico não é encontrado
    (por exemplo, no carrinho ou no catálogo).
    """
    pass

class CarrinhoVazioError(Exception):
    """
    Exceção levantada quando uma operação de checkout é tentada
    com um carrinho vazio.
    """
    pass

class PagamentoFalhouError(Exception):
    """
    Exceção levantada quando o processamento de pagamento via API externa
    não foi bem-sucedido.
    """
    pass
    
# Você pode adicionar outras exceções conforme o projeto cresce.
# Por exemplo, para dados inválidos, usuário não autenticado, etc.
