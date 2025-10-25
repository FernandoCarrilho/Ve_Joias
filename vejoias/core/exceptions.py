class BaseErroCore(Exception):
    """Classe base para todas as exceções da Camada Core."""
    pass

class DadosInvalidosError(BaseErroCore):
    """Erro levantado quando dados inválidos são fornecidos."""
    def __init__(self, message="Os dados fornecidos são inválidos."):
        self.message = message
        super().__init__(self.message)

# ===============================================
# ERROS DE PERSISTÊNCIA E ENTIDADE
# ===============================================

class ItemNaoEncontradoError(BaseErroCore):
    """Erro levantado quando um item (genérico) não é encontrado."""
    def __init__(self, message="O item solicitado não foi encontrado."):
        self.message = message
        super().__init__(self.message)

class JoiaNaoEncontradaError(ItemNaoEncontradoError):
    """Erro levantado quando uma joia específica não é encontrada."""
    def __init__(self, message="A joia solicitada não foi encontrada."):
        self.message = message
        super().__init__(self.message)
        
class PedidoNaoEncontradoError(ItemNaoEncontradoError):
    """Erro específico para Pedidos não encontrados."""
    pass

class UsuarioNaoEncontradoError(ItemNaoEncontradoError):
    """Erro específico para Usuários não encontrados."""
    pass

class EnderecoInvalidoError(BaseErroCore):
    """Erro levantado quando um endereço de entrega é inválido ou não pertence ao usuário."""
    pass

class EstoqueInsuficienteError(BaseErroCore):
    """Erro levantado quando a quantidade solicitada excede o estoque."""
    def __init__(self, joia_id: str, estoque_atual: int, quantidade_solicitada: int, message=None):
        self.joia_id = joia_id
        self.estoque_atual = estoque_atual
        self.quantidade_solicitada = quantidade_solicitada
        if message is None:
            message = (f"Estoque insuficiente para a Joia {joia_id}. "
                       f"Disponível: {estoque_atual}, Solicitado: {quantidade_solicitada}.")
        super().__init__(message)

# ===============================================
# ERROS DE FLUXO DE COMPRA E PAGAMENTO
# ===============================================

class CarrinhoVazioError(BaseErroCore):
    """Erro levantado ao tentar fazer checkout com carrinho vazio."""
    def __init__(self, message="O carrinho de compras está vazio."):
        self.message = message
        super().__init__(self.message)

class PagamentoFalhouError(BaseErroCore):
    """Erro levantado quando o Gateway de Pagamento rejeita a transação."""
    def __init__(self, message="A transação de pagamento foi rejeitada ou falhou."):
        self.message = message
        super().__init__(self.message)

class StatusInvalidoError(BaseErroCore):
    """Erro levantado ao tentar definir um status de pedido inválido."""
    def __init__(self, message="O status fornecido não é válido para um pedido."):
        self.message = message
        super().__init__(self.message)
