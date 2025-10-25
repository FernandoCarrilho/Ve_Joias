"""
Camada de Infraestrutura: Implementação de Repositórios e Gateways.

Esta camada traduz as operações abstratas definidas nas Interfaces da Core
em chamadas concretas ao framework (Django ORM, APIs externas, etc.).
"""
from typing import List, Optional
from typing import Dict
import uuid
from datetime import datetime
from django.db.models import Q, F, Sum, Prefetch
from django.db import transaction
from django.db.utils import IntegrityError
from decimal import Decimal
import random # Para o Mock de Pagamento
import json # Para lidar com o campo JSON de endereço no Pedido (se for o caso)

# Importações da Camada CORE (ENTIDADES e INTERFACES)
from django.contrib.auth import get_user_model

# Importações dos Modelos Django
from vejoias.catalog.models import Joia as JoiaModel, Categoria as CategoriaModel, Subcategoria as SubcategoriaModel
from vejoias.vendas.models import ( 
    Pedido as PedidoModel, 
    ItemPedido as ItemPedidoModel, 
    Endereco as EnderecoModel
)
from vejoias.carrinho.models import Carrinho as CarrinhoModel, ItemCarrinho as ItemCarrinhoModel

from vejoias.core.entities import (
    Joia, Categoria, Carrinho, ItemCarrinho, Pedido, ItemPedido, 
    Usuario, Endereco, TransacaoPagamento
)
from vejoias.core.ports import (
    IJoiaRepository,
    ICarrinhoRepository,
    IPedidoRepository,
    IGatewayPagamento,
)
from vejoias.core.exceptions import (
    JoiaNaoEncontradaError, 
    EstoqueInsuficienteError, 
    ItemNaoEncontradoError, 
    PedidoNaoEncontradoError,
    PagamentoFalhouError
)

from .mappers import (
    JoiaMapper, EnderecoMapper, ItemCarrinhoMapper, CarrinhoMapper,
    ItemPedidoMapper, PedidoMapper, UsuarioMapper, CategoriaMapper, SubcategoriaMapper
)

User = get_user_model()


# ====================================================================
# 1. REPOSITÓRIOS (Implementação Django ORM)
# ====================================================================

class JoiaRepositoryDjango(IJoiaRepository):
    """Implementação do JoiaRepository usando o Django ORM."""

    def buscar_por_id(self, id: int) -> Optional[Joia]:
        try:
            # Inclui categoria e subcategoria para o mapeamento completo
            model = JoiaModel.objects.select_related('categoria', 'subcategoria').get(pk=id)
            return JoiaMapper.to_entity(model)
        except JoiaModel.DoesNotExist:
            return None

    def buscar_por_criterios(
        self, 
        em_estoque: bool, 
        busca: Optional[str] = None, 
        categoria_slug: Optional[str] = None
    ) -> List[Joia]:
        
        qs = JoiaModel.objects.all().select_related('categoria', 'subcategoria')
        
        if em_estoque:
            qs = qs.filter(estoque__gt=0)

        if busca:
            # Busca por nome ou descrição
            qs = qs.filter(Q(nome__icontains=busca) | Q(descricao__icontains=busca))
            
        if categoria_slug:
            qs = qs.filter(categoria__slug=categoria_slug)
            
        return [JoiaMapper.to_entity(model) for model in qs]
    
    @transaction.atomic
    def salvar(self, joia: Joia) -> Joia:
        """Salva ou atualiza uma Joia, convertendo a entidade para o modelo."""
        
        model = None
        if joia.id:
            try:
                model = JoiaModel.objects.get(pk=joia.id)
            except JoiaModel.DoesNotExist:
                raise JoiaNaoEncontradaError(f"Joia ID {joia.id} não existe para atualização.")
                
        # Converte a entidade para o modelo e preenche os campos
        model = JoiaMapper.to_model(joia, model)
        
        # O JoiaMapper.to_model preenche os IDs de FK (categoria_id, subcategoria_id).
        # Não precisamos carregar os modelos de Categoria/Subcategoria aqui se o ORM suportar.
        
        model.save()
        # Garante que a entidade retorne com o ID
        return JoiaMapper.to_entity(model)

    def atualizar_estoque(self, joia_id: str, quantidade: int) -> None:
        """
        Atualiza o estoque de uma joia após uma venda/compra.
        """
        joia = JoiaModel.objects.get(pk=joia_id)
        if joia.estoque >= quantidade:
            joia.estoque -= quantidade
            joia.save()
        else:
            raise EstoqueInsuficienteError(f"Estoque insuficiente para a Joia ID {joia_id}.")

    def deletar(self, joia_id: int):
        try:
            JoiaModel.objects.get(pk=joia_id).delete()
        except JoiaModel.DoesNotExist:
            raise JoiaNaoEncontradaError(f"Joia ID {joia_id} não pode ser deletada, pois não existe.")
            
    # Adicionando o método buscar_por_id que faltou na interface (embora a JoiaRepositoryInterface não o exija, a BaseRepositoryInterface sim)
    def buscar_por_id(self, id: int) -> Optional[Joia]:
        return self.buscar_por_id(id)


class CarrinhoRepositoryDjango(ICarrinhoRepository):
    """Implementação do CarrinhoRepository usando o Django ORM."""

    def buscar_por_usuario(self, usuario: Usuario) -> Carrinho:
        try:
            # Tenta encontrar o carrinho e pré-carrega os itens com as joias relacionadas
            carrinho_model = CarrinhoModel.objects.select_related('usuario').prefetch_related(
                # Usamos Prefetch para garantir que a joia e categoria/subcategoria sejam carregadas
                Prefetch(
                    'itemcarrinho_set', # Related name padrão ou definido no model
                    queryset=ItemCarrinhoModel.objects.select_related('joia__categoria', 'joia__subcategoria'),
                    to_attr='itens_list_for_mapper' # Nome do atributo para o mapper
                )
            ).get(usuario_id=usuario.id)
        except CarrinhoModel.DoesNotExist:
            # Se não houver carrinho, a regra é criar um novo
            try:
                user_model = User.objects.get(pk=usuario.id)
                carrinho_model = CarrinhoModel.objects.create(usuario=user_model)
            except User.DoesNotExist:
                raise ValueError(f"Usuário ID {usuario.id} não encontrado para criar o carrinho.")

        # O CarrinhoMapper precisa que os itens estejam carregados (o prefetch ajuda nisso)
        # O mapper irá converter os ItemCarrinhoModels em ItemCarrinhoEntities.
        return CarrinhoMapper.to_entity(carrinho_model)

    def buscar_ou_criar(self, usuario: Usuario) -> Carrinho:
        """Busca um carrinho existente ou cria um novo se não existir."""
        return self.buscar_por_usuario(usuario)

    @transaction.atomic
    def salvar(self, carrinho: Carrinho) -> Carrinho:
        """Salva a Entidade Carrinho, sincronizando os ItemCarrinhoModels."""
        
        if not carrinho.id:
            raise ValueError("Carrinho deve ter um ID para ser salvo (obtido via buscar_por_usuario).")
        
        try:
            carrinho_model = CarrinhoModel.objects.get(pk=carrinho.id)
        except CarrinhoModel.DoesNotExist:
            raise ItemNaoEncontradoError(f"Carrinho ID {carrinho.id} não existe.")
        
        # 1. Identifica os Joia IDs que devem estar no carrinho e suas quantidades
        joia_ids_atuais = {item.joia_id: item.quantidade for item in carrinho.itens}
        
        # 2. Sincroniza os itens:
        
        # Obtém IDs dos itens existentes para exclusão
        itens_existentes = ItemCarrinhoModel.objects.filter(carrinho=carrinho_model)
        
        # Lista para armazenar novos itens (para criação em massa se for o caso)
        itens_a_salvar = []
        
        for item_entity in carrinho.itens:
            # Tenta encontrar o ItemCarrinhoModel existente
            try:
                item_model = itens_existentes.get(joia_id=item_entity.joia_id)
                # Atualiza a quantidade
                if item_model.quantidade != item_entity.quantidade:
                    item_model.quantidade = item_entity.quantidade
                    item_model.save()
            except ItemCarrinhoModel.DoesNotExist:
                # Cria um novo ItemCarrinhoModel usando o Mapper (para setar joia_id e quantidade)
                item_model = ItemCarrinhoMapper.to_model(item_entity, carrinho_id=carrinho.id)
                itens_a_salvar.append(item_model)
                
        if itens_a_salvar:
            ItemCarrinhoModel.objects.bulk_create(itens_a_salvar)
            
        # 3. Deleta itens que foram removidos da entidade
        joias_para_excluir_ids = [
            item.joia_id for item in itens_existentes
            if item.joia_id not in joia_ids_atuais
        ]
        ItemCarrinhoModel.objects.filter(
            carrinho=carrinho_model, 
            joia_id__in=joias_para_excluir_ids
        ).delete()
        
        carrinho_model.save()
        # Retorna o carrinho atualizado (usamos o ID e os itens originais da entidade que foi salva)
        return carrinho

    @transaction.atomic
    def salvar_item(self, carrinho: Carrinho, item: ItemCarrinho) -> None:
        """
        Salva um item específico no carrinho.
        """
        try:
            carrinho_model = CarrinhoModel.objects.get(pk=carrinho.id)
            # Tenta encontrar o item existente
            try:
                item_model = ItemCarrinhoModel.objects.get(
                    carrinho=carrinho_model,
                    joia_id=item.joia_id
                )
                # Atualiza a quantidade
                item_model.quantidade = item.quantidade
                item_model.save()
            except ItemCarrinhoModel.DoesNotExist:
                # Cria um novo item
                item_model = ItemCarrinhoMapper.to_model(item, carrinho_id=carrinho.id)
                item_model.save()
        except CarrinhoModel.DoesNotExist:
            raise ItemNaoEncontradoError(f"Carrinho ID {carrinho.id} não existe.")

    @transaction.atomic
    def remover_item(self, carrinho: Carrinho, joia_id: str) -> None:
        """
        Remove um item específico do carrinho.
        """
        try:
            carrinho_model = CarrinhoModel.objects.get(pk=carrinho.id)
            ItemCarrinhoModel.objects.filter(
                carrinho=carrinho_model,
                joia_id=joia_id
            ).delete()
        except CarrinhoModel.DoesNotExist:
            raise ItemNaoEncontradoError(f"Carrinho ID {carrinho.id} não existe.")

    @transaction.atomic
    def limpar_carrinho(self, usuario: Usuario):
        """Remove todos os ItemCarrinhoModels do CarrinhoModel do usuário."""
        try:
            carrinho_model = CarrinhoModel.objects.get(usuario_id=usuario.id)
            ItemCarrinhoModel.objects.filter(carrinho=carrinho_model).delete()
            carrinho_model.save()
        except CarrinhoModel.DoesNotExist:
            pass # Se o carrinho não existe, não há o que limpar


class PedidoRepositoryDjango(IPedidoRepository):
    """Implementação do PedidoRepository usando o Django ORM."""

    def buscar_por_id(self, pedido_id: int) -> Optional[Pedido]:
        try:
            model = PedidoModel.objects.select_related('usuario').prefetch_related('itens').get(pk=pedido_id)
            return PedidoMapper.to_entity(model)
        except PedidoModel.DoesNotExist:
            return None

    def listar(self, usuario: Optional[Usuario] = None) -> List[Pedido]:
        qs = PedidoModel.objects.all().select_related('usuario')
        if usuario:
            qs = qs.filter(usuario_id=usuario.id)
        qs = qs.order_by('-data_pedido')
        return [PedidoMapper.to_entity(model) for model in qs]

    @transaction.atomic
    def criar_pedido(self, pedido: Pedido) -> Pedido:
        """
        Cria um novo pedido no banco de dados.
        """
        model = PedidoMapper.to_model(pedido)
        model.save()
        # Salva os itens do pedido
        for item in pedido.itens:
            item_model = ItemPedidoMapper.to_model(item, pedido_id=model.id)
            item_model.save()
        return PedidoMapper.to_entity(model)

    def atualizar_status(self, pedido_id: int, novo_status: str) -> None:
        """
        Atualiza o status de um pedido.
        """
        PedidoModel.objects.filter(pk=pedido_id).update(status=novo_status)

    @transaction.atomic
    def salvar(self, pedido: Pedido) -> Pedido:
        """Salva a Entidade Pedido, incluindo os itens."""
        model = None
        if pedido.id:
            try:
                model = PedidoModel.objects.get(pk=pedido.id)
            except PedidoModel.DoesNotExist:
                raise PedidoNaoEncontradoError(f"Pedido ID {pedido.id} não existe para atualização.")
                
        # Converte a Entidade Pedido para o Model
        model = PedidoMapper.to_model(pedido, model)
        
        # Garante que o usuário existe no DB e associa
        try:
            user_model = User.objects.get(pk=pedido.usuario_id)
            model.usuario = user_model
        except User.DoesNotExist:
            raise ValueError(f"Usuário ID {pedido.usuario_id} não encontrado.")
            
        model.save()
        
        if not pedido.id: # Se for um novo pedido
            pedido.id = model.id
            
            # 3. Cria os Itens do Pedido (apenas na criação)
            item_models = [
                ItemPedidoMapper.to_model(item, pedido_id=model.id)
                for item in pedido.itens
            ]
            ItemPedidoModel.objects.bulk_create(item_models)
            
            # 4. Baixa o estoque das joias (Regra crítica de negócio na Infraestrutura)
            for item in pedido.itens:
                # Checa o estoque antes de tentar atualizar
                joia = JoiaModel.objects.get(pk=item.joia_id)
                if joia.estoque < item.quantidade:
                     raise EstoqueInsuficienteError(f"Estoque insuficiente para a Joia ID {item.joia_id}.")

                JoiaModel.objects.filter(pk=item.joia_id).update(
                    estoque=F('estoque') - item.quantidade
                )
                
        return PedidoMapper.to_entity(model) # Retorna a entidade mapeada

    def listar_pedidos_por_usuario(self, usuario_id: str) -> List[Pedido]:
        """Lista todos os pedidos de um usuário."""
        qs = PedidoModel.objects.filter(usuario_id=usuario_id).order_by('-data_pedido')
        return [PedidoMapper.to_entity(model) for model in qs]

    def listar_todos_pedidos(self, status: Optional[str] = None) -> List[Pedido]:
        """Lista todos os pedidos, opcionalmente filtrados por status."""
        qs = PedidoModel.objects.all()
        if status:
            qs = qs.filter(status=status)
        qs = qs.order_by('-data_pedido')
        return [PedidoMapper.to_entity(model) for model in qs]

    def buscar_por_transacao_id(self, transacao_id: str) -> Optional[Pedido]:
        """Busca um pedido pelo ID de transação do pagamento."""
        try:
            model = PedidoModel.objects.get(transacao_id=transacao_id)
            return PedidoMapper.to_entity(model)
        except PedidoModel.DoesNotExist:
            return None


# ====================================================================
# 2. GATEWAYS (Mock - Simulação de Serviço Externo)
# ====================================================================

class PagamentoGatewayMock(IGatewayPagamento):
    """
    Gateway de Pagamento Mock (Simulado).
    Simula uma comunicação externa para teste e desenvolvimento.
    """
    
    def processar_pagamento(self, pedido: Pedido, metodo: str, dados: dict) -> TransacaoPagamento:
        """Simula o processamento do pagamento."""
        
        # Lógica de MOCK: 90% de chance de sucesso, 10% de falha
        if random.random() < 0.9:
            # Sucesso ou Pendente
            if pedido.total_pedido > Decimal(5000):
                # Valores altos ficam Pendentes no Mock
                status = "PENDENTE"
                mensagem = "Pagamento sob revisão de segurança (alto valor - MOCK)."
            else:
                status = "APROVADO"
                mensagem = "Pagamento processado com sucesso pelo Mock."
                
        else:
            # Falha
            status = "REJEITADO"
            mensagem = "Pagamento rejeitado: Cartão inválido ou limite excedido (MOCK)."
            # Lança a exceção de falha que a camada Core deve capturar
            raise PagamentoFalhouError(mensagem)
            
        return TransacaoPagamento(
            id=None,
            pedido_id=pedido.id,
            valor=pedido.total_pedido,
            data_transacao=datetime.now(),
            metodo_pagamento=metodo,
            status_pagamento=status,
            referencia_externa=f"MOCK-{random.randint(100000, 999999)}",
        )

    def verificar_status(self, transacao_id: str) -> TransacaoPagamento:
        """Simula a verificação de status (ex: para boleto/pix)."""
        # Simplificação: se a transação começa com MOCK, retorna PENDENTE
        if transacao_id.startswith("MOCK-"):
             return TransacaoPagamento(
                id=None,
                pedido_id=0, # ID Desconhecido no Mock de verificação
                valor=Decimal(0.0),
                data_transacao=datetime.now(),
                metodo_pagamento="MOCK",
                status_pagamento="PENDENTE",
                referencia_externa=transacao_id
            )
        else:
            raise PagamentoFalhouError("Transação Mock não encontrada.")
        

# Usuário de exemplo para fins de teste
USUARIO_TESTE = Usuario(
    id="user-4f8e-test", 
    nome="Maria da Silva", 
    email="maria@exemplo.com"
)

# Joias iniciais (estoque)
JOIAS_DB: Dict[str, Joia] = {
    "joia-101": Joia(id="joia-101", nome="Colar Diamante Solitário", slug="colar-diamante-solitario", descricao="Elegante colar de diamante solitário", preco=Decimal("1500.00"), estoque=5),
    "joia-102": Joia(id="joia-102", nome="Anel Ouro Rosé Zircônia", slug="anel-ouro-rose-zirconia", descricao="Anel delicado em ouro rosé com zircônia", preco=Decimal("450.50"), estoque=12),
    "joia-103": Joia(id="joia-103", nome="Brincos de Pérola Clássicos", slug="brincos-de-perola-classicos", descricao="Brincos clássicos com pérolas naturais", preco=Decimal("300.00"), estoque=20),
}

# Carrinhos ativos (vazio por padrão)
CARINHOS_DB: Dict[str, Carrinho] = {
    # Exemplo: "user-4f8e-test": Carrinho(usuario_id="user-4f8e-test", itens=[...])
}

# Pedidos realizados
PEDIDOS_DB: Dict[str, Pedido] = {}


# ====================================================================
# REPOSITÓRIOS (Implementações Concretas)
# ====================================================================

class JoiaRepository(IJoiaRepository):
    """
    Implementação do Repositório de Joias usando armazenamento in-memory (JOIAS_DB).
    Implementa IRepositorioJoias.
    """
    
    def buscar_por_id(self, joia_id: str) -> Optional[Joia]:
        """Busca uma joia pelo seu ID."""
        return JOIAS_DB.get(joia_id)

    def buscar_todos(self) -> List[Joia]:
        """Método auxiliar que lista todas as joias (não faz parte do protocolo, mas é útil)."""
        return list(JOIAS_DB.values())

    def buscar_por_criterios(
        self, 
        em_estoque: bool = True, 
        busca: Optional[str] = None, 
        categoria_slug: Optional[str] = None,
        em_destaque: bool = False
    ) -> List[Joia]:
        """Busca joias filtrando por critérios."""
        
        qs = JoiaModel.objects.all().select_related('categoria', 'subcategoria')
        
        if em_estoque:
            qs = qs.filter(estoque__gt=0)

        if em_destaque:
            qs = qs.filter(em_destaque=True)

        if busca:
            # Busca por nome, descrição ou categoria
            qs = qs.filter(
                Q(nome__icontains=busca) | 
                Q(descricao__icontains=busca) |
                Q(categoria__nome__icontains=busca)
            )
            
        if categoria_slug:
            qs = qs.filter(categoria__slug=categoria_slug)
            
        return [JoiaMapper.to_entity(model) for model in qs]

    def buscar_categorias_destaque(self) -> List[Categoria]:
        """Retorna as categorias em destaque."""
        categorias = CategoriaModel.objects.filter(em_destaque=True)
        return [CategoriaMapper.to_entity(model) for model in categorias]

    def salvar(self, joia: Joia) -> Joia:
        """Implementa IRepositorioJoias. Salva ou atualiza uma joia."""
        if not joia.id:
            joia.id = str(uuid.uuid4())
        
        JOIAS_DB[joia.id] = joia
        return joia

    def deletar(self, joia_id: str):
        """Implementa IRepositorioJoias. Remove uma joia."""
        if joia_id in JOIAS_DB:
            del JOIAS_DB[joia_id]

    # Método para simular a atualização do estoque após um pedido (necessário ao Use Case)
    def atualizar_estoque(self, joia_id: str, quantidade: int) -> None:
        """Diminui o estoque da joia após uma compra."""
        joia = JOIAS_DB.get(joia_id)
        # Assumindo que a verificação de estoque é feita no Use Case,
        # aqui apenas realizamos a atualização.
        if joia and joia.estoque >= quantidade:
            joia.estoque -= quantidade
            # Em um DB real, isto seria um 'UPDATE'


class CarrinhoRepository(ICarrinhoRepository):
    """
    Implementação do Repositório de Carrinho usando armazenamento in-memory (CARINHOS_DB).
    Implementa IRepositorioCarrinhos.
    """
    
    def buscar_por_usuario(self, usuario: Usuario) -> Carrinho:
        """
        Implementa IRepositorioCarrinhos. Busca o carrinho de um usuário. 
        Se não existir, retorna um novo carrinho.
        """
        usuario_id = usuario.id
        if usuario_id not in CARINHOS_DB:
            # Cria um carrinho vazio se não for encontrado (simula 'lazy loading')
            CARINHOS_DB[usuario_id] = Carrinho(usuario_id=usuario_id, itens=[])
            
        return CARINHOS_DB[usuario_id]

    def buscar_ou_criar(self, usuario: Usuario) -> Carrinho:
        """Busca um carrinho existente ou cria um novo se não existir."""
        return self.buscar_por_usuario(usuario)

    def salvar(self, carrinho: Carrinho) -> Carrinho:
        """Implementa IRepositorioCarrinhos. Salva (ou atualiza) o estado do carrinho."""
        CARINHOS_DB[carrinho.usuario_id] = carrinho
        return carrinho

    def salvar_item(self, carrinho: Carrinho, item: ItemCarrinho) -> None:
        """Salva um item no carrinho."""
        current_carrinho = CARINHOS_DB.get(carrinho.usuario_id)
        if not current_carrinho:
            current_carrinho = Carrinho(usuario_id=carrinho.usuario_id, itens=[])
            CARINHOS_DB[carrinho.usuario_id] = current_carrinho

        # Procura se o item já existe no carrinho
        for i, existing_item in enumerate(current_carrinho.itens):
            if existing_item.joia_id == item.joia_id:
                # Atualiza a quantidade do item existente
                current_carrinho.itens[i] = item
                break
        else:
            # Se não encontrou o item, adiciona ao carrinho
            current_carrinho.itens.append(item)

        CARINHOS_DB[carrinho.usuario_id] = current_carrinho

    def remover_item(self, carrinho: Carrinho, joia_id: str) -> None:
        """Remove um item do carrinho."""
        current_carrinho = CARINHOS_DB.get(carrinho.usuario_id)
        if current_carrinho:
            current_carrinho.itens = [
                item for item in current_carrinho.itens if item.joia_id != joia_id
            ]
            CARINHOS_DB[carrinho.usuario_id] = current_carrinho

    def limpar_carrinho(self, usuario: Usuario):
        """Implementa IRepositorioCarrinhos. Remove o carrinho do usuário após o checkout."""
        usuario_id = usuario.id
        if usuario_id in CARINHOS_DB:
            del CARINHOS_DB[usuario_id]


class PedidoRepository(IPedidoRepository):
    """
    Implementação do Repositório de Pedidos usando armazenamento in-memory (PEDIDOS_DB).
    Implementa IPedidoRepository.
    """
    
    def buscar_por_id(self, pedido_id: str) -> Optional[Pedido]:
        """Implementa IPedidoRepository. Busca um pedido pelo seu ID."""
        return PEDIDOS_DB.get(pedido_id)

    def salvar(self, pedido: Pedido) -> Pedido:
        """
        Implementa IPedidoRepository. Salva um novo pedido. 
        Em um DB real, o ID seria gerado pelo banco.
        """
        if not pedido.id:
            pedido.id = str(uuid.uuid4())
            pedido.data_pedido = datetime.now()
            
        PEDIDOS_DB[pedido.id] = pedido
        return pedido

    def listar(self, usuario: Optional[Usuario] = None) -> List[Pedido]:
        """Implementa IPedidoRepository. Retorna a lista de pedidos, filtrada por usuário se fornecido."""
        if usuario:
            return [
                pedido for pedido in PEDIDOS_DB.values() 
                if pedido.usuario_id == usuario.id
            ]
        # Lista todos os pedidos se nenhum usuário for fornecido (para Admin)
        return list(PEDIDOS_DB.values()) 

    def buscar_por_transacao_id(self, transacao_id: str) -> Optional[Pedido]:
        """
        Implementa IPedidoRepository. Busca um pedido pelo ID de Transação,
        crucial para o Use Case de Webhook/IPN.
        """
        return next(
            (pedido for pedido in PEDIDOS_DB.values() if pedido.transacao_id == transacao_id),
            None
        )
        
    def criar_pedido(self, pedido: Pedido) -> Pedido:
        """
        Cria um novo pedido no repositório.
        """
        if not pedido.id:
            pedido.id = str(uuid.uuid4())
            pedido.data_pedido = datetime.now()
            PEDIDOS_DB[pedido.id] = pedido
        return pedido

    def atualizar_status(self, pedido_id: str, novo_status: str) -> None:
        """
        Atualiza o status de um pedido.
        """
        if pedido := PEDIDOS_DB.get(pedido_id):
            pedido.status = novo_status
            PEDIDOS_DB[pedido_id] = pedido

    def listar_pedidos_por_usuario(self, usuario_id: str) -> List[Pedido]:
        """
        Lista todos os pedidos de um usuário específico.
        """
        return [
            pedido for pedido in PEDIDOS_DB.values()
            if pedido.usuario_id == usuario_id
        ]

    def listar_todos_pedidos(self, status: Optional[str] = None) -> List[Pedido]:
        """
        Lista todos os pedidos, opcionalmente filtrados por status.
        """
        pedidos = list(PEDIDOS_DB.values())
        if status:
            pedidos = [pedido for pedido in pedidos if pedido.status == status]
        return pedidos
