class ApplicationError(Exception):
    """
    Exceção base para todos os erros de domínio (negócio) da aplicação Vê Joias.
    Permite que as Views capturem qualquer erro de negócio
    com um único 'except ApplicationError'.
    """
    pass



class EstoqueInsuficienteError(ApplicationError):
    """
    Exceção levantada quando um item não pode ser adicionado ao carrinho
    devido à falta de estoque.
    """
    def __init__(self, joia_id: str, estoque_atual: int, quantidade_solicitada: int, message="Estoque insuficiente."):
        self.joia_id = joia_id
        self.estoque_atual = estoque_atual
        self.quantidade_solicitada = quantidade_solicitada
        super().__init__(
            f"{message} Jóia ID: {joia_id}. Solicitado: {quantidade_solicitada}, Disponível: {estoque_atual}."
        )



class ItemNaoEncontradoError(ApplicationError):
    """
    Exceção levantada quando um item específico não é encontrado (catálogo, carrinho, etc.).
    """
    def __init__(self, item_id: str, tipo="Item", message="Não encontrado."):
        self.item_id = item_id
        self.tipo = tipo
        super().__init__(
            f"{tipo} com ID: {item_id} não foi encontrado."
        )



class CarrinhoVazioError(ApplicationError):
    """
    Exceção levantada quando uma operação de checkout é tentada com um carrinho vazio.
    """
    pass # A mensagem padrão é suficiente aqui.



class PagamentoFalhouError(ApplicationError):
    """
    Exceção levantada quando o processamento de pagamento via API externa
    não foi bem-sucedido.
    """
    def __init__(self, detalhes: str = "Motivo desconhecido", message="Falha ao processar o pagamento."):
        self.detalhes = detalhes
        super().__init__(
            f"{message} Detalhes da falha: {detalhes}"
        )


class DadosInvalidosError(ApplicationError):
    """
    Exceção para erros de validação que não são tratados pelo Serializer.
    """
    def __init__(self, campos_errados: list = [], message="Dados de entrada inválidos."):
        self.campos_errados = campos_errados
        super().__init__(
            f"{message} Campos afetados: {', '.join(campos_errados)}"
        )


class StatusInvalidoError(ApplicationError):
    """Exceção levantada quando o status fornecido é inválido."""
    pass

class PedidoNaoEncontradoError(ApplicationError):
    """Exceção levantada quando um pedido não é encontrado pelo ID ou transação."""
    pass