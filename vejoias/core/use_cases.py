# vejoias/core/use_cases.py
"""
Implementação dos Casos de Uso (Lógica de Negócio) da aplicação.
Esta camada depende apenas das Entidades e Portas (Interfaces) do Core, 
garantindo o isolamento da lógica de negócio.
"""
from typing import List, Optional, Dict
from decimal import Decimal
from datetime import datetime

# Entidades e Exceções
from vejoias.core.entities import (
    Joia, Carrinho, Categoria, Endereco, Pedido, ItemPedido, Usuario, TransacaoPagamento
)
from vejoias.core.exceptions import (
    ItemNaoEncontradoError, 
    EstoqueInsuficienteError, 
    CarrinhoVazioError,
    DadosInvalidosError,
    PagamentoFalhouError,
    PedidoNaoEncontradoError,
    StatusInvalidoError
)

# Portas (Interfaces) - Importadas do vejoias/core/ports.py
from vejoias.core.ports import (
    IJoiaRepository, 
    ICarrinhoRepository, 
    ICategoriaRepository,
    IPedidoRepository,
    IUsuarioRepository,
    IGatewayPagamento,
    IEmailService,
    IWhatsappGateway
)


# ====================================================================
# 1. CASOS DE USO DO CATÁLOGO
# ====================================================================

class ListarJoiasUseCase:
    """Caso de Uso responsável por listar joias com filtros e categorias."""
    def __init__(self, joia_repo: IJoiaRepository, categoria_repo: ICategoriaRepository):
        self.joia_repo = joia_repo
        self.categoria_repo = categoria_repo

    def listar_joias(
        self, 
        busca: Optional[str] = None, 
        categoria_slug: Optional[str] = None
    ) -> List[Joia]:
        """Retorna joias filtradas por busca textual e/ou categoria, excluindo itens sem estoque."""
        # A lógica de busca complexa é delegada à interface IJoiaRepository
        return self.joia_repo.buscar_por_criterios(
            em_estoque=True, # Sempre busca apenas itens em estoque para o catálogo principal
            busca=busca,
            categoria_slug=categoria_slug
        )
        
    def listar_categorias(self) -> List[Categoria]:
        """Retorna a lista de todas as categorias."""
        return self.categoria_repo.buscar_todas()


class DetalharJoiaUseCase:
    """Caso de Uso para obter os detalhes de uma joia específica."""
    def __init__(self, joia_repo: IJoiaRepository):
        self.joia_repo = joia_repo

    def executar(self, joia_id: str) -> Joia:
        """Busca e retorna uma joia pelo seu ID."""
        joia = self.joia_repo.buscar_por_id(joia_id)
        if not joia:
            raise ItemNaoEncontradoError(f"Jóia ID {joia_id} não encontrada.")
        return joia


# ====================================================================
# 2. CASOS DE USO DO CARRINHO
# ====================================================================

class GerenciarCarrinhoUseCase:
    """
    Caso de Uso que centraliza a lógica de gestão do carrinho (adicionar, remover, visualizar).
    """
    def __init__(self, carrinho_repo: ICarrinhoRepository, joia_repo: IJoiaRepository):
        self.carrinho_repo = carrinho_repo
        self.joia_repo = joia_repo

    def obter_carrinho(self, usuario: Optional[Usuario] = None, sessao_key: Optional[str] = None) -> Carrinho:
        """Busca o carrinho existente ou cria um novo para o usuário/sessão."""
        if not usuario and not sessao_key:
            raise DadosInvalidosError("É necessário um Usuário ou uma chave de Sessão.")
            
        # O repositório deve lidar com a lógica de preferência (Usuário logado > Sessão)
        return self.carrinho_repo.buscar_ou_criar(usuario, sessao_key)


    def adicionar_item(self, carrinho: Carrinho, joia_id: str, quantidade: int = 1) -> Carrinho:
        """Adiciona ou incrementa um item no carrinho, verificando estoque."""
        if quantidade <= 0:
            raise DadosInvalidosError("A quantidade a adicionar deve ser positiva.")
        
        joia = self.joia_repo.buscar_por_id(joia_id)
        if not joia:
            raise ItemNaoEncontradoError(f"Jóia ID {joia_id} não encontrada.")

        # Lógica de validação de estoque
        item_existente = next((item for item in carrinho.itens if item.joia_id == joia_id), None)
        quantidade_no_carrinho = item_existente.quantidade if item_existente else 0
        quantidade_total_solicitada = quantidade + quantidade_no_carrinho
        
        if joia.estoque < quantidade_total_solicitada:
            raise EstoqueInsuficienteError(
                f"Estoque insuficiente. Máximo disponível para {joia.nome}: {joia.estoque}. "
                f"Você já tem {quantidade_no_carrinho} no carrinho."
            )
            
        # O repositório é responsável por atualizar o item no banco de dados.
        return self.carrinho_repo.salvar_item(carrinho, joia_id, quantidade)


    def remover_item(self, carrinho: Carrinho, joia_id: str) -> Carrinho:
        """Remove um item do carrinho completamente."""
        
        item_para_remover = next((item for item in carrinho.itens if item.joia_id == joia_id), None)
        
        if not item_para_remover:
            raise ItemNaoEncontradoError("Item não encontrado no carrinho.")

        # O repositório deve ser responsável por persistir a remoção.
        return self.carrinho_repo.remover_item(carrinho, joia_id)


# ====================================================================
# 3. CASOS DE USO DE PEDIDO E CHECKOUT
# ====================================================================

class CriarPedidoUseCase:
    """
    Caso de Uso que coordena a finalização do checkout: 
    Snapshot, Redução de Estoque, Pagamento e Notificação.
    """
    def __init__(self, 
                 carrinho_repo: ICarrinhoRepository, 
                 pedido_repo: IPedidoRepository, 
                 joia_repo: IJoiaRepository,
                 pagamento_gateway: IGatewayPagamento,
                 email_service: IEmailService,
                 whatsapp_gateway: IWhatsappGateway):
        
        self.carrinho_repo = carrinho_repo
        self.pedido_repo = pedido_repo
        self.joia_repo = joia_repo
        self.pagamento_gateway = pagamento_gateway
        self.email_service = email_service
        self.whatsapp_gateway = whatsapp_gateway
    
    
    def executar(
        self, 
        carrinho: Carrinho, 
        usuario: Usuario,
        tipo_pagamento: str, 
        dados_entrega: dict, 
        numero_telefone: str,
        dados_pagamento: dict
    ) -> Pedido:
        """Processa o checkout."""
        
        if not carrinho.itens:
            raise CarrinhoVazioError("Não é possível finalizar o checkout com o carrinho vazio.")

        # Validações de Entidade Endereco (simplificadas aqui)
        endereco_entity = Endereco(
            cep=dados_entrega.get('cep'),
            rua=dados_entrega.get('rua'),
            numero=dados_entrega.get('numero'),
            bairro=dados_entrega.get('bairro'),
            cidade=dados_entrega.get('cidade'),
            estado=dados_entrega.get('estado'),
            referencia=dados_entrega.get('referencia')
        )

        itens_pedido = []
        total_calculado = Decimal('0.00')
        
        # 1. Snapshot e Checagem de Estoque Final
        for item_carrinho in carrinho.itens:
            joia = self.joia_repo.buscar_por_id(item_carrinho.joia_id)
            
            if not joia:
                raise ItemNaoEncontradoError(f"Jóia ID {item_carrinho.joia_id} não encontrada no catálogo.")
            
            if joia.estoque < item_carrinho.quantidade:
                raise EstoqueInsuficienteError(
                    joia_id=joia.id, estoque_atual=joia.estoque, quantidade_solicitada=item_carrinho.quantidade
                )
            
            # Cria o ItemPedido (Snapshot imutável)
            item_snapshot = ItemPedido(
                joia_id=joia.id,
                nome_joia=joia.nome,
                preco_unitario=joia.preco, # Preço atual no momento do checkout
                quantidade=item_carrinho.quantidade,
                subtotal=item_carrinho.quantidade * joia.preco
            )
            
            itens_pedido.append(item_snapshot)
            total_calculado += item_snapshot.subtotal

        # 2. Prepara a Entidade Pedido inicial
        pedido_inicial = Pedido(
            usuario=usuario, 
            data_pedido=datetime.now(),
            status="AGUARDANDO_PAGAMENTO",
            total=total_calculado,
            tipo_pagamento=tipo_pagamento.upper(),
            endereco_entrega=endereco_entity,
            telefone_whatsapp=numero_telefone,
            itens=itens_pedido 
        )
        
        # 3. Processa o Pagamento via Gateway
        try:
            transacao: TransacaoPagamento = self.pagamento_gateway.processar_pagamento(
                pedido=pedido_inicial, 
                metodo=tipo_pagamento.upper(), 
                usuario=usuario,
                dados=dados_pagamento
            )
        except PagamentoFalhouError as e:
            raise PagamentoFalhouError(f"Pagamento rejeitado: {str(e)}")

        # 4. Finaliza a Entidade Pedido e Persiste
        pedido_inicial.status = transacao.status_pagamento 
        pedido_inicial.transacao_id = transacao.referencia_externa
        
        # O PedidoRepository deve criar o pedido, reduzir o estoque e limpar o carrinho ATOMICAMENTE.
        pedido_final = self.pedido_repo.criar_pedido(
            pedido_inicial, 
            carrinho.id, 
            estoque_updates={item.joia_id: item.quantidade for item in itens_pedido}
        )
        
        # 5. Notificações
        try:
            self.email_service.enviar_confirmacao_pedido(pedido_final)
            self.whatsapp_gateway.enviar_confirmacao_pedido(pedido_final, numero_telefone)
        except Exception:
            # Em produção, você logaria isso. Por enquanto, só ignora a falha de notificação.
            pass
        
        return pedido_final


class AtualizarStatusPedidoPorTransacaoUseCase:
    """
    Use Case para atualizar o status de um pedido baseado na notificação 
    de pagamento (Webhook/IPN).
    """
    def __init__(
        self, 
        pedido_repo: IPedidoRepository, 
        pagamento_gateway: IGatewayPagamento, 
        email_service: IEmailService,
        whatsapp_gateway: IWhatsappGateway
    ):
        self.pedido_repo = pedido_repo
        self.pagamento_gateway = pagamento_gateway
        self.email_service = email_service
        self.whatsapp_gateway = whatsapp_gateway
    
    # Mapeamento de status internos
    _STATUS_MAP = {
        "APROVADO": "PAGO",
        "PENDENTE": "PENDENTE",
        "REJEITADO": "CANCELADO",
        "ESTORNADO": "CANCELADO",
        # Adicionar outros status relevantes
    }

    def executar(self, transacao_id: str):
        
        try:
            # 1. Buscar o status atual da transação no gateway
            transacao: TransacaoPagamento = self.pagamento_gateway.verificar_status(transacao_id)
        except Exception:
            # Em produção, logar a falha de comunicação com o gateway
            return 

        # 2. Buscar o pedido correspondente no repositório
        pedido = self.pedido_repo.buscar_por_transacao_id(transacao_id)
        
        if not pedido:
            # Logar que a transação não tem pedido correspondente (pode ser um erro do gateway)
            return
            
        # 3. Mapear e atualizar o status
        novo_status_pedido = self._STATUS_MAP.get(transacao.status_pagamento, pedido.status)

        if pedido.status != novo_status_pedido:
            pedido_final = self.pedido_repo.atualizar_status(
                pedido.id, 
                novo_status_pedido, 
                id_externo_pagamento=transacao.referencia_externa
            )
            
            # 4. Notificações
            if novo_status_pedido == "PAGO":
                try:
                    self.email_service.enviar_aprovacao_pagamento(pedido_final)
                except Exception:
                    pass
                
                try:
                    self.whatsapp_gateway.enviar_aprovacao_pagamento(pedido_final, pedido_final.telefone_whatsapp)
                except Exception:
                    pass


class ListarPedidosDoUsuarioUseCase:
    """Caso de Uso para listar os pedidos de um cliente específico."""
    def __init__(self, pedido_repo: IPedidoRepository):
        self.pedido_repo = pedido_repo
        
    def executar(self, usuario_id: str) -> List[Pedido]:
        """Retorna a lista de pedidos do usuário."""
        # A responsabilidade de listar por ID de usuário é do repositório
        return self.pedido_repo.listar_pedidos_por_usuario(usuario_id)


# ====================================================================
# 4. CASOS DE USO ADMINISTRATIVOS
# ====================================================================

class GerenciarPedidosAdminUseCase:
    """Caso de Uso para listagem e atualização de pedidos (acesso administrativo)."""
    
    STATUS_VALIDOS = ["PAGO", "PROCESSANDO", "ENVIADO", "ENTREGUE", "CANCELADO", "PENDENTE"]
    
    def __init__(
        self, 
        pedido_repo: IPedidoRepository,
        email_service: IEmailService,
        whatsapp_gateway: IWhatsappGateway
    ):
        self.pedido_repo = pedido_repo
        self.email_service = email_service
        self.whatsapp_gateway = whatsapp_gateway
        
    def listar_todos(self, status: Optional[str] = None) -> List[Pedido]:
        """Lista todos os pedidos no sistema, com filtro opcional por status."""
        return self.pedido_repo.listar_todos_pedidos(status)

    def detalhar_pedido(self, pedido_id: str) -> Pedido:
        """Busca os detalhes de um pedido específico."""
        pedido = self.pedido_repo.buscar_por_id(pedido_id)
        if not pedido:
            raise PedidoNaoEncontradoError(f"Pedido ID {pedido_id} não encontrado.")
        return pedido

    def atualizar_status_manual(self, pedido_id: str, novo_status: str) -> Pedido:
        """Atualiza o status de um pedido manualmente (ex: por um administrador)."""
        novo_status_upper = novo_status.upper()
        
        if novo_status_upper not in self.STATUS_VALIDOS:
            raise StatusInvalidoError(f"O status '{novo_status}' não é um status de pedido válido.")
        
        # 1. Atualiza o status no repositório
        pedido_final = self.pedido_repo.atualizar_status(pedido_id, novo_status_upper)
        
        # 2. Notificações específicas por mudança de status (Ex: Pedido Enviado)
        if novo_status_upper == "ENVIADO":
            # Aqui você chamaria o serviço para enviar o e-mail/WhatsApp de envio
            pass 
        
        return pedido_final


class GerenciarUsuariosAdminUseCase:
    """Caso de Uso para listagem de usuários no painel administrativo."""
    def __init__(self, usuario_repo: IUsuarioRepository):
        self.usuario_repo = usuario_repo
        
    def listar_todos(self) -> List[Usuario]:
        """Retorna a lista de todos os usuários cadastrados."""
        return self.usuario_repo.buscar_todos()
