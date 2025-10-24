"""
Camada Core: Casos de Uso (Use Cases)

Contém toda a lógica de negócio principal do sistema e coordena 
as interações entre Entidades e Protocolos (Interfaces).
"""
from .entities import (
    Usuario, Joia, Carrinho, ItemCarrinho, Pedido, Endereco, TransacaoPagamento
)
from .exceptions import (
    EstoqueInsuficienteError, 
    ItemNaoEncontradoError, 
    CarrinhoVazioError,
    PagamentoFalhouError,
    StatusInvalidoError,
    PedidoNaoEncontradoError
)
from typing import Protocol, List, Optional
from decimal import Decimal
from datetime import datetime

# ====================================================================
# 1. PROTOCOLOS (Portas para a Camada de Infraestrutura)
# ====================================================================

# 1.1 Repositórios (Persistência)

class IRepositorioJoias(Protocol):
    """Protocolo para a persistência de Joias, alinhado com JoiaRepositoryInterface."""
    def buscar_por_id(self, joia_id: int) -> Optional[Joia]: ...
    def buscar_por_criterios(
        self, 
        em_estoque: bool, 
        busca: Optional[str] = None, 
        categoria_slug: Optional[str] = None
    ) -> List[Joia]: ...
    def salvar(self, joia: Joia) -> Joia: ...
    def deletar(self, joia_id: int): ...

class IRepositorioCarrinhos(Protocol):
    """Protocolo para a persistência de Carrinhos, alinhado com CarrinhoRepositoryInterface."""
    # O repositório DEVE criar um carrinho se não existir.
    def buscar_por_usuario(self, usuario: Usuario) -> Carrinho: ... 
    def salvar(self, carrinho: Carrinho) -> Carrinho: ...
    def limpar_carrinho(self, usuario: Usuario): ...

class IRepositorioPedidos(Protocol):
    """Protocolo para a persistência de Pedidos, alinhado com PedidoRepositoryInterface."""
    def salvar(self, pedido: Pedido) -> Pedido: ...
    def buscar_por_id(self, id: int) -> Optional[Pedido]: ...
    def listar(self, usuario: Optional[Usuario] = None) -> List[Pedido]: ...
    # Método necessário para o Use Case de atualização de status via Webhook
    def buscar_por_transacao_id(self, transacao_id: str) -> Optional[Pedido]: ... 


# 1.2 Gateways (Serviços Externos)

class IGatewayPagamento(Protocol):
    """Protocolo para serviços externos de pagamento, alinhado com PagamentoGatewayInterface."""
    def processar_pagamento(self, pedido: Pedido, metodo: str, dados: dict) -> TransacaoPagamento: ...
    def verificar_status(self, transacao_id: str) -> TransacaoPagamento: ...


class IEmailService(Protocol):
    """Protocolo para o serviço de envio de e-mails."""
    def enviar_confirmacao_pedido(self, pedido: Pedido): ...
    def enviar_aprovacao_pagamento(self, pedido: Pedido): ...

class IWhatsappGateway(Protocol):
    """Protocolo para o serviço de envio de mensagens via WhatsApp."""
    def enviar_confirmacao_pedido(self, pedido: Pedido, numero_telefone: str): ...
    def enviar_aprovacao_pagamento(self, pedido: Pedido, numero_telefone: str): ...


# ====================================================================
# 2. CASOS DE USO: Contêm a lógica de negócio principal.
# ====================================================================

class AdicionarItemAoCarrinho:
    """Adiciona uma joia ao carrinho do usuário, verificando o estoque."""
    def __init__(self, repo_carrinho: IRepositorioCarrinhos, repo_joias: IRepositorioJoias):
        self.repo_carrinho = repo_carrinho
        self.repo_joias = repo_joias
        
    def execute(self, usuario: Usuario, joia_id: int, quantidade: int) -> Carrinho:
        joia = self.repo_joias.buscar_por_id(joia_id)
        
        if not joia:
            raise ItemNaoEncontradoError(f"Jóia ID {joia_id} não encontrada.")

        # O carrinho é sempre retornado, o repositório garante a criação se não existir.
        carrinho = self.repo_carrinho.buscar_por_usuario(usuario)
        
        # Encontra o item, se existir
        item_existente = next((item for item in carrinho.itens if item.joia_id == joia_id), None)
        
        quantidade_total_solicitada = quantidade
        if item_existente:
            quantidade_total_solicitada += item_existente.quantidade

        # Verifica se o estoque suporta a nova quantidade total
        if joia.estoque < quantidade_total_solicitada:
            raise EstoqueInsuficienteError(
                joia_id=joia_id,
                estoque_atual=joia.estoque,
                quantidade_solicitada=quantidade_total_solicitada
            )
        
        # Atualiza ou adiciona o item
        if item_existente:
            item_existente.quantidade = quantidade_total_solicitada
        else:
            # Ao adicionar um novo item, usamos apenas o joia_id e a quantidade. 
            # O preço é derivado via método do Carrinho/ItemCarrinho ou no Repositório.
            carrinho.itens.append(ItemCarrinho(joia_id=joia.id, quantidade=quantidade))
            
        return self.repo_carrinho.salvar(carrinho)


class RemoverItemDoCarrinho:
    """Remove um item do carrinho do usuário."""
    def __init__(self, repo_carrinho: IRepositorioCarrinhos):
        self.repo_carrinho = repo_carrinho

    def execute(self, usuario: Usuario, joia_id: int) -> Carrinho:
        carrinho = self.repo_carrinho.buscar_por_usuario(usuario)
        
        if not carrinho.itens:
            raise CarrinhoVazioError("O carrinho está vazio.")

        item_para_remover = next((item for item in carrinho.itens if item.joia_id == joia_id), None)

        if not item_para_remover:
            raise ItemNaoEncontradoError("Item não encontrado no carrinho.")

        carrinho.itens.remove(item_para_remover)
        return self.repo_carrinho.salvar(carrinho)


class CriarPedido:
    """
    Cria um pedido, processa o pagamento e delega o gerenciamento de estoque 
    e a limpeza do carrinho à camada de Infraestrutura.
    """
    def __init__(
        self, 
        carrinho_repo: IRepositorioCarrinhos, 
        pedido_repo: IRepositorioPedidos, 
        pagamento_gateway: IGatewayPagamento,
        whatsapp_gateway: IWhatsappGateway, 
        email_service: IEmailService
    ):
        self.carrinho_repo = carrinho_repo
        self.pedido_repo = pedido_repo
        self.pagamento_gateway = pagamento_gateway
        self.whatsapp_gateway = whatsapp_gateway
        self.email_service = email_service

    def execute(
        self, 
        usuario: Usuario, 
        tipo_pagamento: str, 
        endereco_entrega: Endereco, 
        numero_telefone: str,
        dados_pagamento: dict
    ) -> Pedido:
        
        carrinho = self.carrinho_repo.buscar_por_usuario(usuario)
        
        if not carrinho.itens:
            raise CarrinhoVazioError("Não é possível criar um pedido com um carrinho vazio.")

        # 1. Monta a Entidade Pedido (snapshot dos dados)
        # NOTA: O cálculo do total deve ser feito aqui na Core, para validação.
        total = carrinho.calcular_total() 
        
        # Prepara a entidade Pedido inicial (status será atualizado após pagamento)
        pedido_inicial = Pedido(
            id=None,
            usuario_id=usuario.id,
            data_pedido=datetime.now(),
            status="AGUARDANDO_PAGAMENTO", # Status inicial antes de tentar o gateway
            total_pedido=total,
            tipo_pagamento=tipo_pagamento.upper(),
            endereco_entrega=endereco_entrega,
            telefone_whatsapp=numero_telefone,
            itens=carrinho.itens_para_pedido() # Cria ItemPedido com o snapshot de preço/nome
        )
        
        # 2. Processa o Pagamento via Gateway
        try:
            transacao: TransacaoPagamento = self.pagamento_gateway.processar_pagamento(
                pedido=pedido_inicial, 
                metodo=tipo_pagamento.upper(), 
                dados=dados_pagamento
            )
        except PagamentoFalhouError as e:
            # Não salva nada, apenas lança o erro para a camada de Aplicação
            raise PagamentoFalhouError(f"Pagamento rejeitado: {str(e)}")

        # 3. Finaliza a Entidade Pedido
        pedido_inicial.status = transacao.status_pagamento
        pedido_inicial.transacao_id = transacao.referencia_externa
        
        # 4. Salva o Pedido, reduz o estoque (Infraestrutura) e limpa o carrinho
        try:
            pedido_final = self.pedido_repo.salvar(pedido_inicial)
            self.carrinho_repo.limpar_carrinho(usuario)
        except EstoqueInsuficienteError as e:
             # Se a Infra falhar na redução de estoque, o Use Case reverte a transação se necessário
             # e lança o erro
             raise EstoqueInsuficienteError(str(e))
        
        # 5. Notificações (Pode falhar, mas o pedido já foi salvo)
        try:
            self.email_service.enviar_confirmacao_pedido(pedido_final)
            self.whatsapp_gateway.enviar_confirmacao_pedido(pedido_final, numero_telefone)
        except Exception as e:
            # Em produção, você logaria isso.
            print(f"Alerta: Falha ao enviar notificações para Pedido {pedido_final.id}: {e}")
        
        return pedido_final


class AtualizarStatusPedidoPorTransacao:
    """
    Use Case para atualizar o status de um pedido baseado na notificação 
    de pagamento (Webhook/IPN).
    """
    def __init__(
        self, 
        pedido_repo: IRepositorioPedidos, 
        pagamento_gateway: IGatewayPagamento, 
        whatsapp_gateway: IWhatsappGateway, 
        email_service: IEmailService
    ):
        self.pedido_repo = pedido_repo
        self.pagamento_gateway = pagamento_gateway
        self.whatsapp_gateway = whatsapp_gateway
        self.email_service = email_service
    
    # Mapeamento do Core para o status da Entidade Pedido
    _STATUS_MAP = {
        "APROVADO": "PAGO",
        "PENDENTE": "PENDENTE",
        "REJEITADO": "CANCELADO",
        "ESTORNADO": "CANCELADO",
        # Adicionar outros mapeamentos necessários
    }

    def execute(self, transacao_id: str):
        
        # 1. Buscar o status atual da transação no gateway
        try:
            transacao: TransacaoPagamento = self.pagamento_gateway.verificar_status(transacao_id)
        except Exception as e:
            print(f"Erro ao buscar status da transação {transacao_id}: {e}")
            return # Não prossegue

        # 2. Buscar o pedido correspondente no repositório
        pedido = self.pedido_repo.buscar_por_transacao_id(transacao_id)
        
        if not pedido:
            print(f"Aviso: Pedido não encontrado para a transação {transacao_id}.")
            return
            
        # 3. Mapear o status da Transação para o status do Pedido
        novo_status_pedido = self._STATUS_MAP.get(transacao.status_pagamento, pedido.status)

        # 4. Atualizar e salvar o status se ele realmente mudou
        if pedido.status != novo_status_pedido:
            status_antigo = pedido.status
            pedido.status = novo_status_pedido
            self.pedido_repo.salvar(pedido)
            print(f"Status do Pedido {pedido.id} atualizado de {status_antigo} para: {novo_status_pedido}")
            
            # 5. Notificações
            if novo_status_pedido == "PAGO":
                try:
                    self.whatsapp_gateway.enviar_aprovacao_pagamento(pedido, pedido.telefone_whatsapp)
                except Exception as e:
                    print(f"Alerta: Falha ao enviar WhatsApp de aprovação para Pedido {pedido.id}: {e}")
                
                try:
                    self.email_service.enviar_aprovacao_pagamento(pedido)
                except Exception as e:
                    print(f"Alerta: Falha ao enviar E-mail de aprovação para Pedido {pedido.id}: {e}")


class ListarPedidos:
    """
    Use Case para listar pedidos, permitindo filtragem por status ou por usuário.
    """
    def __init__(self, pedido_repo: IRepositorioPedidos):
        self.pedido_repo = pedido_repo

    def execute(self, usuario: Optional[Usuario] = None) -> List[Pedido]:
        """
        Retorna uma lista de pedidos. Se usuário for fornecido, lista apenas os dele.
        """
        # A complexidade de filtragem por status deve estar na query do repositório,
        # mas aqui delegamos a listagem genérica.
        return self.pedido_repo.listar(usuario=usuario)
    

class BuscarPedidoPorId:
    """
    Use Case para buscar os detalhes completos de um pedido pelo seu ID.
    """
    def __init__(self, pedido_repo: IRepositorioPedidos):
        self.pedido_repo = pedido_repo

    def execute(self, pedido_id: int) -> Optional[Pedido]:
        """
        Retorna a Entidade Pedido ou None se não for encontrado.
        """
        return self.pedido_repo.buscar_por_id(pedido_id)


class AtualizarStatusManual:
    """
    Use Case para atualizar o status de um pedido manualmente (ex: por um administrador).
    """
    
    STATUS_VALIDOS = ["PAGO", "PENDENTE", "PROCESSANDO", "ENVIADO", "ENTREGUE", "CANCELADO"]
    
    def __init__(self, pedido_repo: IRepositorioPedidos, email_service: IEmailService, whatsapp_gateway: IWhatsappGateway):
        self.pedido_repo = pedido_repo
        self.email_service = email_service
        self.whatsapp_gateway = whatsapp_gateway 

    def execute(self, pedido_id: int, novo_status: str) -> Pedido:
        
        novo_status_upper = novo_status.upper()
        
        if novo_status_upper not in self.STATUS_VALIDOS:
            raise StatusInvalidoError(f"O status '{novo_status}' não é um status de pedido válido.")

        pedido = self.pedido_repo.buscar_por_id(pedido_id)
        
        if not pedido:
            raise PedidoNaoEncontradoError(f"Pedido com ID {pedido_id} não encontrado.") 

        status_antigo = pedido.status
        
        if status_antigo == novo_status_upper:
            return pedido 

        pedido.status = novo_status_upper
        
        pedido_final = self.pedido_repo.salvar(pedido)
        
        # Lógica de Notificação Pós-Status
        if novo_status_upper in ["PROCESSANDO", "ENVIADO", "ENTREGUE", "CANCELADO"]:
            # Em um sistema real, aqui você chamaria métodos específicos nos gateways
            # Ex: self.whatsapp_gateway.enviar_status_mudanca(pedido_final, novo_status_upper)
            print(f"Notificação simulada de mudança de status para {novo_status_upper}")

        return pedido_final
