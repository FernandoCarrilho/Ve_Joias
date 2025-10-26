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
import random 
import json 

# *** MUDANÇA CRÍTICA: Importação Lenta (Lazy Loading) para Modelos Django ***
from django.apps import apps
from django.contrib.auth import get_user_model

# Importações da Camada CORE (ENTIDADES e INTERFACES)
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

# Helper para Lazy Loading
def get_model(app_label, model_name):
    """Busca o modelo Django de forma segura (Lazy Loading)."""
    return apps.get_model(app_label, model_name)


class JoiaRepositoryDjango(IJoiaRepository):
    """Implementação do JoiaRepository usando o Django ORM."""

    # Propriedades para carregar modelos de forma LAZY
    @property
    def JoiaModel(self):
        return get_model('catalog', 'Joia')
    
    @property
    def CategoriaModel(self):
        return get_model('catalog', 'Categoria')
    
    @property
    def SubcategoriaModel(self):
        return get_model('catalog', 'Subcategoria')

    def buscar_por_id(self, id: int) -> Optional[Joia]:
        try:
            # Usa self.JoiaModel
            model = self.JoiaModel.objects.select_related('categoria', 'subcategoria').get(pk=id)
            return JoiaMapper.to_entity(model)
        except self.JoiaModel.DoesNotExist:
            return None

    def buscar_por_criterios(
        self, 
        em_estoque: bool, 
        busca: Optional[str] = None, 
        categoria_slug: Optional[str] = None
    ) -> List[Joia]:
        
        qs = self.JoiaModel.objects.all().select_related('categoria', 'subcategoria')
        
        if em_estoque:
            qs = qs.filter(estoque__gt=0)

        if busca:
            # Busca por nome ou descrição
            qs = qs.filter(Q(nome__icontains=busca) | Q(descricao__icontains=busca))
            
        if categoria_slug:
            # Acessa o modelo de categoria via propriedade
            qs = qs.filter(categoria__slug=categoria_slug)
            
        return [JoiaMapper.to_entity(model) for model in qs]
    
    def contar_total(self) -> int:
        """
        Conta o número total de joias no sistema.
        """
        return self.JoiaModel.objects.count()

    @transaction.atomic
    def salvar(self, joia: Joia) -> Joia:
        """Salva ou atualiza uma Joia, convertendo a entidade para o modelo."""
        
        model = None
        if joia.id:
            try:
                model = self.JoiaModel.objects.get(pk=joia.id)
            except self.JoiaModel.DoesNotExist:
                raise JoiaNaoEncontradaError(f"Joia ID {joia.id} não existe para atualização.")
                
        model = JoiaMapper.to_model(joia, model)
        model.save()
        return JoiaMapper.to_entity(model)

    def atualizar_estoque(self, joia_id: str, quantidade: int) -> None:
        """
        Atualiza o estoque de uma joia após uma venda/compra.
        """
        try:
            joia = self.JoiaModel.objects.get(pk=joia_id)
            if joia.estoque >= quantidade:
                joia.estoque -= quantidade
                joia.save()
            else:
                raise EstoqueInsuficienteError(f"Estoque insuficiente para a Joia ID {joia_id}.")
        except self.JoiaModel.DoesNotExist:
            raise JoiaNaoEncontradaError(f"Joia ID {joia_id} não encontrada para atualização de estoque.")


    def deletar(self, joia_id: int):
        try:
            self.JoiaModel.objects.get(pk=joia_id).delete()
        except self.JoiaModel.DoesNotExist:
            raise JoiaNaoEncontradaError(f"Joia ID {joia_id} não pode ser deletada, pois não existe.")
            
    def buscar_categorias_destaque(self) -> List[Categoria]:
        """Retorna as categorias em destaque, usando o Django ORM."""
        categorias = self.CategoriaModel.objects.filter(em_destaque=True)
        return [CategoriaMapper.to_entity(model) for model in categorias]


class CarrinhoRepositoryDjango(ICarrinhoRepository):
    """Implementação do CarrinhoRepository usando o Django ORM."""

    # Propriedades para carregar modelos de forma LAZY
    @property
    def CarrinhoModel(self):
        return get_model('carrinho', 'Carrinho')
    
    @property
    def ItemCarrinhoModel(self):
        return get_model('carrinho', 'ItemCarrinho')

    def buscar_por_usuario(self, usuario: Usuario) -> Carrinho:
        try:
            # Tenta encontrar o carrinho e pré-carrega os itens com as joias relacionadas
            carrinho_model = self.CarrinhoModel.objects.select_related('usuario').prefetch_related(
                # Usamos Prefetch para garantir que a joia e categoria/subcategoria sejam carregadas
                Prefetch(
                    'itens_carrinho', # Related name CORRIGIDO
                    queryset=self.ItemCarrinhoModel.objects.select_related('joia__categoria', 'joia__subcategoria'),
                    to_attr='itens_list_for_mapper' # Nome do atributo para o mapper
                )
            ).get(usuario__user_id=usuario.id) # Assumindo que o FK é 'usuario' que aponta para User
        except self.CarrinhoModel.DoesNotExist:
            # Se não houver carrinho, a regra é criar um novo
            try:
                user_model = User.objects.get(pk=usuario.id)
                # Cria um novo CarrinhoModel
                carrinho_model = self.CarrinhoModel.objects.create(usuario_id=user_model.id)
            except User.DoesNotExist:
                raise ValueError(f"Usuário ID {usuario.id} não encontrado para criar o carrinho.")

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
            carrinho_model = self.CarrinhoModel.objects.get(pk=carrinho.id)
        except self.CarrinhoModel.DoesNotExist:
            raise ItemNaoEncontradoError(f"Carrinho ID {carrinho.id} não existe.")
        
        # 1. Identifica os Joia IDs que devem estar no carrinho e suas quantidades
        joia_ids_atuais = {item.joia_id: item.quantidade for item in carrinho.itens}
        
        # 2. Sincroniza os itens:
        
        itens_existentes = self.ItemCarrinhoModel.objects.filter(carrinho=carrinho_model)
        
        itens_a_criar = []
        joia_ids_existentes_no_db = set()
        
        for item_entity in carrinho.itens:
            encontrado = False
            for item_model in itens_existentes:
                if str(item_model.joia_id) == str(item_entity.joia_id):
                    # Item existente: Atualiza
                    if item_model.quantidade != item_entity.quantidade:
                        item_model.quantidade = item_entity.quantidade
                        item_model.save()
                    joia_ids_existentes_no_db.add(item_entity.joia_id)
                    encontrado = True
                    break
            
            if not encontrado:
                # Item novo: Cria um novo ItemCarrinhoModel
                # O mapper deve ser adaptado para usar o CarrinhoModel
                item_model = self.ItemCarrinhoModel(
                    carrinho=carrinho_model, 
                    joia_id=item_entity.joia_id, 
                    quantidade=item_entity.quantidade,
                    preco_unitario=item_entity.preco_unitario
                )
                itens_a_criar.append(item_model)
                
        if itens_a_criar:
            self.ItemCarrinhoModel.objects.bulk_create(itens_a_criar)
            
        # 3. Deleta itens que foram removidos da entidade
        joias_para_excluir_ids = [
            item.joia_id for item in itens_existentes
            if item.joia_id not in joia_ids_atuais
        ]
        
        self.ItemCarrinhoModel.objects.filter(
            carrinho=carrinho_model, 
            joia_id__in=joias_para_excluir_ids
        ).delete()
        
        carrinho_model.save() 
        
        return carrinho

    @transaction.atomic
    def salvar_item(self, carrinho: Carrinho, item: ItemCarrinho) -> None:
        """
        Salva um item específico no carrinho.
        """
        try:
            carrinho_model = self.CarrinhoModel.objects.get(pk=carrinho.id)
            # Tenta encontrar o item existente
            item_model, created = self.ItemCarrinhoModel.objects.get_or_create(
                carrinho=carrinho_model,
                joia_id=item.joia_id,
                defaults={'quantidade': item.quantidade, 'preco_unitario': item.preco_unitario}
            )
            
            if not created:
                # Atualiza a quantidade se já existia
                item_model.quantidade = item.quantidade
                item_model.save()
                
        except self.CarrinhoModel.DoesNotExist:
            raise ItemNaoEncontradoError(f"Carrinho ID {carrinho.id} não existe.")

    @transaction.atomic
    def remover_item(self, carrinho: Carrinho, joia_id: str) -> None:
        """
        Remove um item específico do carrinho.
        """
        try:
            carrinho_model = self.CarrinhoModel.objects.get(pk=carrinho.id)
            self.ItemCarrinhoModel.objects.filter(
                carrinho=carrinho_model,
                joia_id=joia_id
            ).delete()
        except self.CarrinhoModel.DoesNotExist:
            # Se o carrinho não existe, podemos simplesmente ignorar ou levantar um erro
            raise ItemNaoEncontradoError(f"Carrinho ID {carrinho.id} não existe.")

    @transaction.atomic
    def limpar_carrinho(self, usuario: Usuario):
        """Remove todos os ItemCarrinhoModels do CarrinhoModel do usuário."""
        try:
            carrinho_model = self.CarrinhoModel.objects.get(usuario__user_id=usuario.id)
            self.ItemCarrinhoModel.objects.filter(carrinho=carrinho_model).delete()
        except self.CarrinhoModel.DoesNotExist:
            pass # Se o carrinho não existe, não há o que limpar


class PedidoRepositoryDjango(IPedidoRepository):
    """Implementação do PedidoRepository usando o Django ORM."""
    
    # Propriedades para carregar modelos de forma LAZY
    @property
    def PedidoModel(self):
        return get_model('vendas', 'Pedido')
    
    @property
    def ItemPedidoModel(self):
        return get_model('vendas', 'ItemPedido')
    
    @property
    def JoiaModel(self):
        return get_model('catalog', 'Joia')

    def buscar_por_id(self, pedido_id: int) -> Optional[Pedido]:
        try:
            # Pré-carrega itens e o usuário para o mapeamento completo
            model = self.PedidoModel.objects.select_related('usuario').prefetch_related(
                Prefetch(
                    'itens', 
                    queryset=self.ItemPedidoModel.objects.select_related('joia'), 
                    to_attr='itens_list_for_mapper'
                )
            ).get(pk=pedido_id)
            return PedidoMapper.to_entity(model)
        except self.PedidoModel.DoesNotExist:
            return None

    def listar(self, usuario: Optional[Usuario] = None) -> List[Pedido]:
        qs = self.PedidoModel.objects.all().select_related('usuario')
        if usuario:
            qs = qs.filter(usuario__user_id=usuario.id)
        qs = qs.order_by('-data_pedido')
        return [PedidoMapper.to_entity(model) for model in qs]
    
    def listar_recentes(self, limite=10) -> List[Pedido]:
        """
        Busca os pedidos mais recentes no banco de dados, usado principalmente 
        para a dashboard administrativa.
        """
        try:
            pedidos_recentes_models = self.PedidoModel.objects.all().order_by('-data_pedido')[:limite]
            return [PedidoMapper.to_entity(model) for model in pedidos_recentes_models]
        except Exception as e:
            print(f"Erro ao listar pedidos recentes no repositório: {e}")
            return []

    def contar_total(self, status: Optional[str] = None) -> int:
        """
        Conta o número total de pedidos no sistema, opcionalmente filtrados por status.
        """
        qs = self.PedidoModel.objects.all()
        if status:
            qs = qs.filter(status=status)
        
        return qs.count()

    @transaction.atomic
    def criar_pedido(self, pedido: Pedido) -> Pedido:
        """
        Cria um novo pedido no banco de dados.
        """
        model = PedidoMapper.to_model(pedido)
        
        # Garante que o usuário existe no DB e associa
        try:
            user_model = User.objects.get(pk=pedido.usuario_id)
            model.usuario_id = user_model.id
        except User.DoesNotExist:
            raise ValueError(f"Usuário ID {pedido.usuario_id} não encontrado.")
            
        model.save()
        
        pedido.id = model.id
        
        # Salva os itens do pedido
        item_models = [
            ItemPedidoMapper.to_model(item, pedido_id=model.id)
            for item in pedido.itens
        ]
        self.ItemPedidoModel.objects.bulk_create(item_models)
        
        # Baixa o estoque das joias
        
        joia_ids = [item.joia_id for item in pedido.itens]
        joias_com_estoque = self.JoiaModel.objects.filter(pk__in=joia_ids).in_bulk()
        
        for item in pedido.itens:
            joia_model = joias_com_estoque.get(item.joia_id)
            if not joia_model or joia_model.estoque < item.quantidade:
                raise EstoqueInsuficienteError(f"Estoque insuficiente para a Joia ID {item.joia_id}.")
            
            # Atualiza o estoque usando F expression (atomic update)
            self.JoiaModel.objects.filter(pk=item.joia_id).update(
                estoque=F('estoque') - item.quantidade
            )

        return PedidoMapper.to_entity(model)

    def atualizar_status(self, pedido_id: int, novo_status: str) -> None:
        """
        Atualiza o status de um pedido.
        """
        self.PedidoModel.objects.filter(pk=pedido_id).update(status=novo_status)

    @transaction.atomic
    def salvar(self, pedido: Pedido) -> Pedido:
        """Salva a Entidade Pedido, usada principalmente para criar/finalizar."""
        
        if not pedido.id:
            return self.criar_pedido(pedido) # Delega a lógica de criação e estoque

        # Lógica de atualização de um pedido existente (menos comum, mas possível)
        try:
            model = self.PedidoModel.objects.get(pk=pedido.id)
        except self.PedidoModel.DoesNotExist:
            raise PedidoNaoEncontradoError(f"Pedido ID {pedido.id} não existe para atualização.")
                
        model = PedidoMapper.to_model(pedido, model)
        model.save()
        
        return PedidoMapper.to_entity(model)

    def listar_pedidos_por_usuario(self, usuario_id: str) -> List[Pedido]:
        """Lista todos os pedidos de um usuário."""
        # Filtra pelo ID do Usuario, que é o ID da entidade Usuario
        qs = self.PedidoModel.objects.filter(usuario_id=usuario_id).order_by('-data_pedido') 
        return [PedidoMapper.to_entity(model) for model in qs]

    def listar_todos_pedidos(self, status: Optional[str] = None) -> List[Pedido]:
        """Lista todos os pedidos, opcionalmente filtrados por status."""
        qs = self.PedidoModel.objects.all()
        if status:
            qs = qs.filter(status=status)
        qs = qs.order_by('-data_pedido')
        return [PedidoMapper.to_entity(model) for model in qs]

    def buscar_por_transacao_id(self, transacao_id: str) -> Optional[Pedido]:
        """Busca um pedido pelo ID de transação do pagamento."""
        # Se você adicionou um campo 'transacao_id' ao modelo Pedido
        try:
            model = self.PedidoModel.objects.get(transacao_id=transacao_id)
            return PedidoMapper.to_entity(model)
        except self.PedidoModel.DoesNotExist:
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
            id=None, # ID é gerado pelo Core/Use Case
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
            # Em um cenário real, você faria uma chamada externa aqui.
            raise PagamentoFalhouError("Transação Mock não encontrada.")
        

# ====================================================================
# REPOSITÓRIOS (Implementações In-Memory para Teste - Mock)
# NOTA: Estes repositórios não usam o Django ORM e servem apenas para 
# testes unitários e simulações onde o DB não é necessário. 
# ====================================================================

# Dados em memória para simulação
USUARIO_TESTE = Usuario(
    id="user-4f8e-test", 
    nome="Maria da Silva", 
    email="maria@exemplo.com"
)

# Categorias em memória para simulação
CATEGORIAS_DB: Dict[str, Categoria] = {
    "cat-1": Categoria(id="cat-1", nome="Colares", slug="colares", em_destaque=True),
    "cat-2": Categoria(id="cat-2", nome="Anéis", slug="aneis", em_destaque=True),
    "cat-3": Categoria(id="cat-3", nome="Brincos", slug="brincos", em_destaque=False),
}

JOIAS_DB: Dict[str, Joia] = {
    "joia-101": Joia(
        id="joia-101",
        nome="Colar Diamante Solitário",
        slug="colar-diamante-solitario",
        descricao="Elegante colar de diamante solitário",
        preco=Decimal("1500.00"),
        estoque=5,
        categoria_id="cat-1",
        categoria=CATEGORIAS_DB["cat-1"]
    ),
    "joia-102": Joia(
        id="joia-102",
        nome="Anel Ouro Rosé Zircônia",
        slug="anel-ouro-rose-zirconia",
        descricao="Anel delicado em ouro rosé com zircônia",
        preco=Decimal("450.50"),
        estoque=12,
        categoria_id="cat-2",
        categoria=CATEGORIAS_DB["cat-2"]
    ),
    "joia-103": Joia(
        id="joia-103",
        nome="Brincos de Pérola Clássicos",
        slug="brincos-de-perola-classicos",
        descricao="Brincos clássicos com pérolas naturais",
        preco=Decimal("300.00"),
        estoque=20,
        categoria_id="cat-3",
        categoria=CATEGORIAS_DB["cat-3"]
    ),
}
CARINHOS_DB: Dict[str, Carrinho] = {}
PEDIDOS_DB: Dict[str, Pedido] = {}


class JoiaRepository(IJoiaRepository):
    """Implementação In-Memory para testes."""
    
    def buscar_por_id(self, id: int) -> Optional[Joia]:
        """Busca uma joia pelo seu ID."""
        return JOIAS_DB.get(str(id))

    def buscar_por_criterios(
        self, 
        em_estoque: bool = True, 
        busca: Optional[str] = None, 
        categoria_slug: Optional[str] = None,
        em_destaque: bool = False
    ) -> List[Joia]:
        """Busca joias filtrando por critérios (Simulado)."""
        
        # A lógica real de filtragem por slug e destaque não é simulada aqui,
        # retornando apenas todos os itens em estoque ou o que for encontrado
        # pelo ID.
        
        resultados = list(JOIAS_DB.values())
        
        if em_estoque:
            resultados = [j for j in resultados if j.estoque > 0]

        if busca:
             resultados = [
                 j for j in resultados 
                 if busca.lower() in j.nome.lower() or busca.lower() in j.descricao.lower()
             ]
            
        return resultados

    def contar_total(self) -> int:
        """Conta o número total de joias (in-memory)."""
        return len(JOIAS_DB)

    def buscar_categorias_destaque(self) -> List[Categoria]:
        """Mock de Categorias em Destaque."""
        return [
            Categoria(id=1, nome="Colares", slug="colares", em_destaque=True),
            Categoria(id=2, nome="Anéis", slug="aneis", em_destaque=True),
        ]

    def salvar(self, joia: Joia) -> Joia:
        """Salva ou atualiza uma joia (in-memory)."""
        if not joia.id:
            joia.id = str(uuid.uuid4())
        
        JOIAS_DB[str(joia.id)] = joia
        return joia

    def deletar(self, joia_id: int):
        """Remove uma joia (in-memory)."""
        if str(joia_id) in JOIAS_DB:
            del JOIAS_DB[str(joia_id)]

    def atualizar_estoque(self, joia_id: str, quantidade: int) -> None:
        """Diminui o estoque da joia (in-memory)."""
        joia = JOIAS_DB.get(joia_id)
        if joia and joia.estoque >= quantidade:
            joia.estoque -= quantidade
            JOIAS_DB[joia_id] = joia
        elif joia:
            raise EstoqueInsuficienteError(f"Estoque insuficiente para a Joia ID {joia_id} (Mock).")
        else:
            raise JoiaNaoEncontradaError(f"Joia ID {joia_id} não encontrada para atualização de estoque (Mock).")


class CarrinhoRepository(ICarrinhoRepository):
    """Implementação In-Memory para testes."""
    
    def buscar_por_usuario(self, usuario: Usuario) -> Carrinho:
        """Busca o carrinho de um usuário. Se não existir, retorna um novo carrinho."""
        usuario_id = usuario.id
        if usuario_id not in CARINHOS_DB:
            CARINHOS_DB[usuario_id] = Carrinho(id=str(uuid.uuid4()), usuario_id=usuario_id, itens=[])
            
        return CARINHOS_DB[usuario_id]

    def buscar_ou_criar(self, usuario: Usuario) -> Carrinho:
        """Busca um carrinho existente ou cria um novo se não existir."""
        return self.buscar_por_usuario(usuario)

    def salvar(self, carrinho: Carrinho) -> Carrinho:
        """Salva (ou atualiza) o estado do carrinho."""
        CARINHOS_DB[carrinho.usuario_id] = carrinho
        return carrinho

    def salvar_item(self, carrinho: Carrinho, item: ItemCarrinho) -> None:
        """Salva um item no carrinho."""
        current_carrinho = CARINHOS_DB.get(carrinho.usuario_id)
        if not current_carrinho:
            current_carrinho = Carrinho(id=str(uuid.uuid4()), usuario_id=carrinho.usuario_id, itens=[])
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
        """Remove o carrinho do usuário após o checkout."""
        usuario_id = usuario.id
        if usuario_id in CARINHOS_DB:
            del CARINHOS_DB[usuario_id]


class PedidoRepository(IPedidoRepository):
    """Implementação In-Memory para testes."""
    
    def buscar_por_id(self, pedido_id: str) -> Optional[Pedido]:
        """Busca um pedido pelo seu ID."""
        return PEDIDOS_DB.get(pedido_id)

    def salvar(self, pedido: Pedido) -> Pedido:
        """Salva um novo pedido."""
        if not pedido.id:
            pedido.id = str(uuid.uuid4())
            pedido.data_pedido = datetime.now()
            
        PEDIDOS_DB[pedido.id] = pedido
        return pedido

    def listar(self, usuario: Optional[Usuario] = None) -> List[Pedido]:
        """Retorna a lista de pedidos, filtrada por usuário se fornecido."""
        if usuario:
            return [
                pedido for pedido in PEDIDOS_DB.values() 
                if pedido.usuario_id == usuario.id
            ]
        return list(PEDIDOS_DB.values()) 

    def buscar_por_transacao_id(self, transacao_id: str) -> Optional[Pedido]:
        """Busca um pedido pelo ID de Transação."""
        return next(
            (pedido for pedido in PEDIDOS_DB.values() if pedido.transacao_id == transacao_id),
            None
        )
        
    def criar_pedido(self, pedido: Pedido) -> Pedido:
        """Cria um novo pedido no repositório."""
        return self.salvar(pedido)

    def atualizar_status(self, pedido_id: str, novo_status: str) -> None:
        """Atualiza o status de um pedido."""
        if pedido := PEDIDOS_DB.get(pedido_id):
            pedido.status = novo_status
            PEDIDOS_DB[pedido_id] = pedido

    def listar_pedidos_por_usuario(self, usuario_id: str) -> List[Pedido]:
        """Lista todos os pedidos de um usuário específico."""
        return self.listar(Usuario(id=usuario_id, nome="", email=""))

    def listar_todos_pedidos(self, status: Optional[str] = None) -> List[Pedido]:
        """Lista todos os pedidos, opcionalmente filtrados por status."""
        pedidos = list(PEDIDOS_DB.values())
        if status:
            pedidos = [pedido for pedido in pedidos if pedido.status == status]
        return pedidos

    def listar_recentes(self, limite=10) -> List[Pedido]:
        """Mock: Lista os pedidos mais recentes (in-memory)."""
        pedidos = sorted(
            list(PEDIDOS_DB.values()), 
            key=lambda p: p.data_pedido if p.data_pedido else datetime.min, 
            reverse=True
        )
        return pedidos[:limite]

    def contar_total(self, status: Optional[str] = None) -> int:
        """Conta o número total de pedidos (in-memory)."""
        pedidos = list(PEDIDOS_DB.values())
        if status:
            pedidos = [pedido for pedido in pedidos if pedido.status == status]
        return len(pedidos)
