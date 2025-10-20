from .entities import Usuario, Joia, Carrinho, ItemCarrinho, Pedido, Endereco
from .exceptions import (
    EstoqueInsuficienteError, 
    ItemNaoEncontradoError, 
    CarrinhoVazioError,
    PagamentoFalhouError,
    ApplicationError,
    StatusInvalidoError,
    PedidoNaoEncontradoError
    
)
from vejoias.infrastructure.email_service import email_service
from typing import Protocol, List, Optional
from decimal import Decimal
from vejoias.core.entities import Pedido


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
            raise EstoqueInsuficienteError(
                joia_id=joia_id,
                estoque_atual=joia.estoque,
                quantidade_solicitada=quantidade
            )
        
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
    def __init__(self, carrinho_repo, joia_repo, pedido_repo, pagamento_gateway, whatsapp_gateway):
        self.carrinho_repo = carrinho_repo
        self.joia_repo = joia_repo
        self.pedido_repo = pedido_repo
        self.pagamento_gateway = pagamento_gateway
        self.whatsapp_gateway = whatsapp_gateway
        self.email_service = email_service

    def execute(self, usuario: Usuario, tipo_pagamento: str, endereco: Endereco, numero_telefone: str) -> Pedido:
        
        # ... (código de validação e cálculo do total) ...
        carrinho = self.carrinho_repo.buscar_por_usuario(usuario)
        total = sum(item.joia.preco * item.quantidade for item in carrinho.itens)
        transacao_id = ""
        url_pagamento = ""
        
        # Variável para determinar o status inicial do pedido
        status_inicial = "PENDENTE" 

        try:
            tipo_pagamento_upper = tipo_pagamento.upper() # Padronizando para segurança
            
            if tipo_pagamento_upper == "PIX":
                transacao_id = self.pagamento_gateway.processar_pagamento_pix(total)
                status_inicial = "PENDENTE" # Mantido como PENDENTE (pode ser PAGO em fluxos síncronos)
                
            elif tipo_pagamento_upper == "CARTAO": # CORREÇÃO 1: Tipo CARTAO
                # CORREÇÃO 2: Chamando o método correto para cartão
                transacao_id = self.pagamento_gateway.processar_pagamento_cartao(total) 
                status_inicial = "PAGO" # Cartão é (quase sempre) síncrono
                
            elif tipo_pagamento_upper == "BOLETO":
                # CORREÇÃO 3: Passando usuário e endereço, conforme a nova assinatura do gateway
                transacao_id, url_pagamento = self.pagamento_gateway.processar_pagamento_boleto(total, usuario, endereco)
                status_inicial = "PENDENTE" # Boletos são sempre PENDENTES
            else:
                raise ValueError("Método de pagamento não suportado.")
        except Exception as e:
            raise PagamentoFalhouError(f"Falha ao processar o pagamento: {str(e)}")

        # CORREÇÃO 4: Usando o status dinâmico (status_inicial)
        pedido = Pedido(
            usuario=usuario,
            endereco_entrega=endereco,
            total=total,
            transacao_id=transacao_id,
            status=status_inicial,
            url_pagamento=url_pagamento, 
        )
        
        self.repo_pedidos.salvar(pedido)

        # Decrementa o estoque das joias e esvazia o carrinho
        for item in carrinho.itens:
            joia = self.repo_joias.buscar_por_id(item.joia.id)
            joia.estoque -= item.quantidade
            self.repo_joias.salvar(joia)
        
        carrinho.itens = []
        self.repo_carrinho.salvar(carrinho)
        try:
            self.email_service.enviar_confirmacao_pedido(pedido)
        except Exception as e:
            # Em produção, você logaria isso. Por enquanto, apenas ignora
            print(f"Erro ao enviar e-mail: {e}")
        try:
            self.whatsapp_gateway.enviar_confirmacao_pedido(pedido, numero_telefone)
        except Exception as e:
            # Em produção, você logaria isso. Por enquanto, apenas ignora
            print(f"Erro ao enviar WhatsApp: {e}")
        
        return pedido


class AtualizarStatusPedido:
    """
    Use Case para atualizar o status de um pedido baseado na notificação 
    de pagamento (Webhook/IPN do Mercado Pago).
    """
    def __init__(self, pedido_repo, pagamento_gateway, whatsapp_gateway, email_service):
        self.pedido_repo = pedido_repo
        self.pagamento_gateway = pagamento_gateway
        self.whatsapp_gateway = whatsapp_gateway
        self.email_service = email_service

    def execute(self, transacao_id: str):
        # 1. Buscar o status atual da transação no gateway
        try:
            # O gateway buscará o status (ex: 'approved', 'pending')
            novo_status_pagamento = self.pagamento_gateway.buscar_status_transacao(transacao_id)
        except Exception as e:
            # Falha ao comunicar com a API do Mercado Pago
            print(f"Erro ao buscar status da transação {transacao_id}: {e}")
            return # Não prossegue

        # 2. Buscar o pedido correspondente no repositório pela ID da transação
        # NOTA: Assumimos que PedidoRepository tem o método buscar_por_transacao_id
        pedido = self.pedido_repo.buscar_por_transacao_id(transacao_id)
        
        if not pedido:
            print(f"Aviso: Pedido não encontrado para a transação {transacao_id}.")
            return
            
        # 3. Mapear o status do pagamento (Mercado Pago) para o status do pedido (Seu Core)
        if novo_status_pagamento in ["approved", "accredited"]:
            novo_status_pedido = "PAGO"
        elif novo_status_pagamento in ["pending", "in_process"]:
            novo_status_pedido = "PENDENTE"
        elif novo_status_pagamento in ["rejected", "cancelled", "refunded", "charged_back"]:
            novo_status_pedido = "CANCELADO"
        else:
            # Ignorar status irrelevantes (ex: 'authorized')
            return

        # 4. Atualizar e salvar o status se ele realmente mudou
        if pedido.status != novo_status_pedido:
            pedido.status = novo_status_pedido
            self.pedido_repo.salvar(pedido)
            print(f"Status do Pedido {pedido.id} atualizado para: {novo_status_pedido}")
            
            # TODO: Adicione a lógica de notificação aqui (ex: enviar WhatsApp de "Pagamento Aprovado")
        if novo_status_pedido == "PAGO":
            
            try:
                    # Nota: Você deve ter um método 'enviar_aprovacao_pagamento' nos gateways
                    # Assumimos que o número de telefone está acessível via entidade Usuario ou Pedido
                self.whatsapp_gateway.enviar_aprovacao_pagamento(
                    pedido=pedido, 
                    numero_telefone=pedido.usuario.numero_telefone_contato # Assumindo o atributo
                )
            except Exception as e:
                print(f"Alerta: Falha ao enviar WhatsApp de aprovação para Pedido {pedido.id}: {e}")
                
            # Enviar E-mail de Pagamento Aprovado
            try:
                self.email_service.enviar_aprovacao_pagamento(pedido)
            except Exception as e:
                print(f"Alerta: Falha ao enviar E-mail de aprovação para Pedido {pedido.id}: {e}")


class ListarPedidos:
    """
    Use Case para listar pedidos, permitindo filtragem por status.
    """
    def __init__(self, pedido_repo):
        self.pedido_repo = pedido_repo

    def execute(self, status: Optional[str] = None):
        """
        Retorna uma lista de pedidos, opcionalmente filtrada por status.
        
        NOTA: Assumimos que o PedidoRepository tem um método 'buscar_todos_pedidos' 
        que pode aceitar um filtro de status.
        """
        
        # O repositório lida com a complexidade de buscar os dados no banco.
        return self.pedido_repo.buscar_todos_pedidos(status=status)
    

class BuscarPedidoPorId:
    """
    Use Case para buscar os detalhes completos de um pedido pelo seu ID.
    """
    def __init__(self, pedido_repo):
        self.pedido_repo = pedido_repo

    def execute(self, pedido_id: int) -> Optional[Pedido]:
        """
        Retorna a Entidade Pedido ou None se não for encontrado.
        
        NOTA: Assumimos que o PedidoRepository tem um método 'buscar_por_id'.
        """
        return self.pedido_repo.buscar_por_id(pedido_id)



class AtualizarStatusManual:
    """
    Use Case para atualizar o status de um pedido manualmente (ex: por um administrador).
    """
    
    STATUS_VALIDOS = ["PAGO", "PENDENTE", "PROCESSANDO", "ENVIADO", "ENTREGUE", "CANCELADO"]
    
    def __init__(self, pedido_repo, notificacao_service=None):
        self.pedido_repo = pedido_repo
        # A notificação_service (WhatsApp/Email) é opcional aqui, 
        # mas pode ser usada para enviar avisos.
        self.notificacao_service = notificacao_service 

    def execute(self, pedido_id: int, novo_status: str) -> Pedido:
        
        novo_status_upper = novo_status.upper()
        
        if novo_status_upper not in self.STATUS_VALIDOS:
            raise StatusInvalidoError(f"O status '{novo_status}' não é um status de pedido válido.")

        # 1. Buscar o pedido
        pedido = self.pedido_repo.buscar_por_id(pedido_id)
        
        if not pedido:
            # Assumimos que o repositório levanta uma exceção específica ou que a view lida com o 404
            raise PedidoNaoEncontradoError(f"Pedido com ID {pedido_id} não encontrado.") 

        # 2. Aplicar a lógica de negócio na mudança de status
        status_antigo = pedido.status
        
        if status_antigo == novo_status_upper:
            # Não faz nada se o status não mudou
            return pedido 

        # 3. Atualizar o status
        pedido.status = novo_status_upper
        
        # 4. Salvar no repositório
        self.pedido_repo.salvar(pedido)
        
        # 5. Lógica de Notificação Pós-Status (Se o Use Case tiver o Notificação Service injetado)
        if self.notificacao_service:
            if novo_status_upper == "PROCESSANDO" and status_antigo not in ["PROCESSANDO", "ENVIADO", "ENTREGUE"]:
                # Exemplo: Notificar o cliente que o pedido está sendo processado
                self.notificacao_service.enviar_status_processamento(pedido)
            
            elif novo_status_upper == "ENVIADO" and status_antigo != "ENVIADO":
                # Exemplo: Notificar o cliente com o código de rastreio
                self.notificacao_service.enviar_status_rastreamento(pedido)
                
            # ... (Outras lógicas de notificação para CANCELADO/ENTREGUE)

        return pedido