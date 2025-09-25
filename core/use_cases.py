from .entities import Usuario, Joia, Carrinho, ItemCarrinho, Pedido, Endereco
from .exceptions import (
    EstoqueInsuficienteError, 
    ItemNaoEncontradoError, 
    CarrinhoVazioError,
    PagamentoFalhouError
)
from typing import Protocol, List, Optional
from decimal import Decimal

# ====================================================================
# PORTAS (Interfaces) para a Camada de Infraestrutura.
# ====================================================================

class IRepositorioJoias(Protocol):
    """Protocolo para a persistência de Joias."""
    def buscar_por_id(self, joia_id: int) -> Optional[Joia]: ...
    def buscar_por_categoria(self, categoria: str) -> List[Joia]: ...
    def salvar(self, joia: Joia): ...

class IRepositorioCarrinhos(Protocol):
    """Protocolo para a persistência de Carrinhos."""
    def buscar_por_usuario(self, usuario: Usuario) -> Optional[Carrinho]: ...
    def salvar(self, carrinho: Carrinho): ...
    def criar(self, usuario: Usuario) -> Carrinho: ...

class IRepositorioPedidos(Protocol):
    """Protocolo para a persistência de Pedidos."""
    def salvar(self, pedido: Pedido): ...

class IGatewayPagamento(Protocol):
    """Protocolo para a API de Pagamento externa."""
    def processar_pagamento_pix(self, valor: Decimal) -> str: ...
    def processar_pagamento_cartao(self, valor: Decimal) -> str: ...

# ====================================================================
# CASOS DE USO: Contêm a lógica de negócio principal.
# ====================================================================

class AdicionarItemAoCarrinho:
    """Adiciona uma joia ao carrinho do usuário, verificando o estoque."""
    def __init__(self, repo_carrinho: IRepositorioCarrinhos, repo_joias: IRepositorioJoias):
        self.repo_carrinho = repo_carrinho
        self.repo_joias = repo_joias
        
    def execute(self, usuario: Usuario, joia_id: int, quantidade: int):
        joia = self.repo_joias.buscar_por_id(joia_id)
        
        if not joia:
            raise ItemNaoEncontradoError("Jóia não encontrada.")

        if joia.estoque < quantidade:
            raise EstoqueInsuficienteError("Estoque insuficiente para esta jóia.")
        
        carrinho = self.repo_carrinho.buscar_por_usuario(usuario)
        if not carrinho:
            carrinho = self.repo_carrinho.criar(usuario)
        
        item_existente = next((item for item in carrinho.itens if item.joia.id == joia_id), None)
        
        if item_existente:
            item_existente.quantidade += quantidade
        else:
            carrinho.itens.append(ItemCarrinho(joia=joia, quantidade=quantidade))
            
        self.repo_carrinho.salvar(carrinho)
        return carrinho

class RemoverItemDoCarrinho:
    """Remove um item do carrinho do usuário."""
    def __init__(self, repo_carrinho: IRepositorioCarrinhos):
        self.repo_carrinho = repo_carrinho

    def execute(self, usuario: Usuario, joia_id: int):
        carrinho = self.repo_carrinho.buscar_por_usuario(usuario)
        if not carrinho or not carrinho.itens:
            raise CarrinhoVazioError("O carrinho está vazio.")

        item_para_remover = next((item for item in carrinho.itens if item.joia.id == joia_id), None)

        if not item_para_remover:
            raise ItemNaoEncontradoError("Item não encontrado no carrinho.")

        carrinho.itens.remove(item_para_remover)
        self.repo_carrinho.salvar(carrinho)
        return carrinho

class CriarPedido:
    """Cria um pedido e processa o pagamento, validando o estoque."""
    def __init__(self, 
                 repo_carrinho: IRepositorioCarrinhos,
                 repo_joias: IRepositorioJoias,
                 repo_pedidos: IRepositorioPedidos,
                 gateway_pagamento: IGatewayPagamento):
        
        self.repo_carrinho = repo_carrinho
        self.repo_joias = repo_joias
        self.repo_pedidos = repo_pedidos
        self.gateway_pagamento = gateway_pagamento

    def execute(self, usuario: Usuario, tipo_pagamento: str, endereco: Endereco) -> Pedido:
        carrinho = self.repo_carrinho.buscar_por_usuario(usuario)
        if not carrinho or not carrinho.itens:
            raise CarrinhoVazioError("O carrinho está vazio.")

        # Valida o estoque de todos os itens do carrinho antes de prosseguir
        for item in carrinho.itens:
            joia = self.repo_joias.buscar_por_id(item.joia.id)
            if not joia or joia.estoque < item.quantidade:
                raise EstoqueInsuficienteError(
                    f"Estoque insuficiente para a jóia: {item.joia.nome}. "
                    "Por favor, atualize seu carrinho."
                )
        
        total = sum(item.joia.preco * item.quantidade for item in carrinho.itens)
        transacao_id = ""

        try:
            if tipo_pagamento == "pix":
                transacao_id = self.gateway_pagamento.processar_pagamento_pix(total)
            elif tipo_pagamento == "cartao":
                transacao_id = self.gateway_pagamento.processar_pagamento_cartao(total)
            else:
                raise ValueError("Método de pagamento não suportado.")
        except Exception as e:
            raise PagamentoFalhouError(f"Falha ao processar o pagamento: {str(e)}")

        pedido = Pedido(
            usuario=usuario,
            endereco_entrega=endereco,
            total=total,
            transacao_id=transacao_id,
            status="PAGO"
        )
        
        self.repo_pedidos.salvar(pedido)

        # Decrementa o estoque das joias e esvazia o carrinho
        for item in carrinho.itens:
            joia = self.repo_joias.buscar_por_id(item.joia.id)
            joia.estoque -= item.quantidade
            self.repo_joias.salvar(joia)
        
        carrinho.itens = []
        self.repo_carrinho.salvar(carrinho)
        
        return pedido
