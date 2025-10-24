import uuid
from .entities import (
    Usuario, Joia, Carrinho, CarrinhoItem, Pedido, Endereco, TransacaoPagamento, ItemPedido
)
from .exceptions import (
    EstoqueInsuficienteError, 
    ItemNaoEncontradoError, 
    CarrinhoVazioError,
    PagamentoFalhouError,
    StatusInvalidoError,
    PedidoNaoEncontradoError
)
from typing import Protocol, List, Optional, Dict
from decimal import Decimal
from datetime import datetime

# ====================================================================
# 1. PROTOCOLOS (Portas para a Camada de Infraestrutura)
# ====================================================================

# 1.1 Repositórios (Persistência)

class IRepositorioJoias(Protocol):
    """Protocolo para a persistência de Joias."""
    def buscar_por_id(self, joia_id: str) -> Optional[Joia]: ...
    def buscar_por_criterios(
        self, 
        em_estoque: bool, 
        busca: Optional[str] = None, 
        categoria_slug: Optional[str] = None
    ) -> List[Joia]: ...
    def salvar(self, joia: Joia) -> Joia: ...
    def deletar(self, joia_id: str): ...
    # Método necessário para o Use Case de Checkout:
    def atualizar_estoque(self, joia_id: str, quantidade: int): ...

class IRepositorioCarrinhos(Protocol):
    """Protocolo para a persistência de Carrinhos."""
    def buscar_por_usuario(self, usuario: Usuario) -> Carrinho: ... 
    def salvar(self, carrinho: Carrinho) -> Carrinho: ...
    def limpar_carrinho(self, usuario: Usuario): ...

class IRepositorioPedidos(Protocol):
    """Protocolo para a persistência de Pedidos."""
    def salvar(self, pedido: Pedido) -> Pedido: ...
    def buscar_por_id(self, id: str) -> Optional[Pedido]: ...
    def listar(self, usuario: Optional[Usuario] = None) -> List[Pedido]: ...
    def buscar_por_transacao_id(self, transacao_id: str) -> Optional[Pedido]: ... 


# 1.2 Gateways (Serviços Externos)

class IGatewayPagamento(Protocol):
    """Protocolo para serviços externos de pagamento."""
    def processar_pagamento(self, pedido: Pedido, metodo: str, usuario: Usuario, dados: dict) -> TransacaoPagamento: ...
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
        
    def execute(self, usuario: Usuario, joia_id: str, quantidade: int) -> Carrinho:
        joia = self.repo_joias.buscar_por_id(joia_id)
        
        if not joia:
            raise ItemNaoEncontradoError(f"Jóia ID {joia_id} não encontrada.")

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
        
        # Atualiza ou adiciona o item. 
        # O snapshot de preço não é salvo aqui; ele é tirado apenas no checkout.
        if item_existente:
            item_existente.quantidade = quantidade_total_solicitada
        else:
            carrinho.itens.append(CarrinhoItem(joia_id=joia.id, quantidade=quantidade))
            
        return self.repo_carrinho.salvar(carrinho)


class RemoverItemDoCarrinho:
    """Remove um item do carrinho do usuário."""
    def __init__(self, repo_carrinho: IRepositorioCarrinhos):
        self.repo_carrinho = repo_carrinho

    def execute(self, usuario: Usuario, joia_id: str) -> Carrinho:
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
    Cria um pedido, processa o pagamento e garante o snapshot de preços.
    """
    def __init__(
        self, 
        carrinho_repo: IRepositorioCarrinhos, 
        pedido_repo: IRepositorioPedidos, 
        pagamento_gateway: IGatewayPagamento,
        whatsapp_gateway: IWhatsappGateway, 
        email_service: IEmailService,
        repo_joias: IRepositorioJoias # INJEÇÃO NECESSÁRIA PARA SNAPSHOT E ESTOQUE
    ):
        self.carrinho_repo = carrinho_repo
        self.pedido_repo = pedido_repo
        self.pagamento_gateway = pagamento_gateway
        self.whatsapp_gateway = whatsapp_gateway
        self.email_service = email_service
        self.repo_joias = repo_joias

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

        # Armazenamento temporário para joias e total
        joias_compradas: Dict[str, Joia] = {}
        itens_pedido: List[ItemPedido] = []
        total_calculado = Decimal('0.00')
        
        # 1. Realiza o Snapshot e a Checagem de Estoque Final
        for item_carrinho in carrinho.itens:
            joia = self.repo_joias.buscar_por_id(item_carrinho.joia_id)
            
            if not joia:
                raise ItemNaoEncontradoError(f"Jóia ID {item_carrinho.joia_id} não encontrada no catálogo.")
            
            if joia.estoque < item_carrinho.quantidade:
                raise EstoqueInsuficienteError(
                    joia_id=joia.id,
                    estoque_atual=joia.estoque,
                    quantidade_solicitada=item_carrinho.quantidade
                )
            
            # Cria o ItemPedido (Snapshot imutável)
            item_snapshot = ItemPedido(
                joia_id=joia.id,
                nome_joia=joia.nome,
                preco_unitario=joia.preco, # Preço atual no momento do checkout
                quantidade=item_carrinho.quantidade
            )
            
            itens_pedido.append(item_snapshot)
            total_calculado += item_snapshot.calcular_subtotal()
            joias_compradas[joia.id] = joia # Salva referência para redução de estoque

        # 2. Prepara a Entidade Pedido inicial
        pedido_inicial = Pedido(
            usuario_id=usuario.id,
            data_pedido=datetime.now(),
            status="AGUARDANDO_PAGAMENTO",
            total_pedido=total_calculado,
            tipo_pagamento=tipo_pagamento.upper(),
            endereco_entrega=endereco_entrega,
            telefone_whatsapp=numero_telefone,
            itens=itens_pedido # Lista de snapshots
        )
        
        # 3. Processa o Pagamento via Gateway
        try:
            # Passa o usuário e o pedido para o gateway (necessário para PIX/Boleto)
            transacao: TransacaoPagamento = self.pagamento_gateway.processar_pagamento(
                pedido=pedido_inicial, 
                metodo=tipo_pagamento.upper(), 
                usuario=usuario,
                dados=dados_pagamento
            )
        except PagamentoFalhouError as e:
            raise PagamentoFalhouError(f"Pagamento rejeitado: {str(e)}")

        # 4. Finaliza a Entidade Pedido
        # O status inicial é definido pela resposta do gateway
        pedido_inicial.status = transacao.status_pagamento 
        pedido_inicial.transacao_id = transacao.referencia_externa
        
        # 5. Salva o Pedido e reduz o estoque (A Infraestrutura deve garantir a transação)
        try:
            pedido_final = self.pedido_repo.salvar(pedido_inicial)
            
            # Reduz o estoque APENAS após o pedido ser salvo com status inicial
            for item in pedido_inicial.itens:
                self.repo_joias.atualizar_estoque(item.joia_id, item.quantidade)
                
            self.carrinho_repo.limpar_carrinho(usuario)
            
        except Exception as e:
             # Em um sistema real, aqui haveria um processo de reversão de transação/estoque
             raise Exception(f"Falha na persistência ou redução de estoque: {e}")
        
        # 6. Notificações
        try:
            # Se a transação exigir ação (PIX/Boleto), a notificação deve incluir os detalhes
            self.email_service.enviar_confirmacao_pedido(pedido_final)
            self.whatsapp_gateway.enviar_confirmacao_pedido(pedido_final, numero_telefone)
        except Exception as e:
            # Em produção, você logaria isso.
            print(f"Alerta: Falha ao enviar notificações para Pedido {pedido_final.id}: {e}")
        
        # Adiciona os detalhes da transação ao pedido final para retorno ao cliente
        setattr(pedido_final, 'transacao', transacao)
        
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
                    # O email e WhatsApp de confirmação de pagamento deve ser enviado APENAS quando
                    # o status muda de PENDENTE para PAGO via webhook.
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
        return self.pedido_repo.listar(usuario=usuario)
    

class BuscarPedidoPorId:
    """
    Use Case para buscar os detalhes completos de um pedido pelo seu ID.
    """
    def __init__(self, pedido_repo: IRepositorioPedidos):
        self.pedido_repo = pedido_repo

    def execute(self, pedido_id: str) -> Optional[Pedido]:
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

    def execute(self, pedido_id: str, novo_status: str) -> Pedido:
        
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
        
        # Lógica de Notificação Pós-Status (Implementação simplificada)
        if novo_status_upper in ["PROCESSANDO", "ENVIADO", "ENTREGUE", "CANCELADO"]:
            # Em um sistema real, aqui você chamaria métodos específicos nos gateways
            # Ex: self.whatsapp_gateway.enviar_status_mudanca(pedido_final, novo_status_upper)
            print(f"Notificação simulada de mudança de status para {novo_status_upper}")

        return pedido_final


class BuscarJoias:
    """
    Use Case para buscar e listar joias, permitindo filtros e busca textual.
    """
    def __init__(self, repo_joias: IRepositorioJoias):
        self.repo_joias = repo_joias

    def execute(
        self, 
        em_estoque: bool = True, 
        busca: Optional[str] = None, 
        categoria_slug: Optional[str] = None
    ) -> List[Joia]:
        """
        Retorna uma lista de Joias filtrada pelos critérios fornecidos.
        """
        return self.repo_joias.buscar_por_criterios(
            em_estoque=em_estoque,
            busca=busca,
            categoria_slug=categoria_slug
        )

class BuscarJoiaPorId:
    """
    Use Case para buscar uma joia específica pelo seu ID.
    """
    def __init__(self, repo_joias: IRepositorioJoias):
        self.repo_joias = repo_joias

    def execute(self, joia_id: str) -> Joia:
        """
        Retorna a Entidade Joia. Levanta exceção se não for encontrada.
        """
        joia = self.repo_joias.buscar_por_id(joia_id)
        if not joia:
            raise ItemNaoEncontradoError(f"Jóia ID {joia_id} não encontrada.")
        return joia
