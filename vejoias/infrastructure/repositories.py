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
from vejoias.core.entities import (
    Joia, Categoria, Carrinho, ItemCarrinho, Pedido, ItemPedido, 
    Usuario, Endereco, TransacaoPagamento
)
from vejoias.core.interfaces import (
    JoiaRepositoryInterface, 
    CarrinhoRepositoryInterface, 
    PedidoRepositoryInterface, 
    PagamentoGatewayInterface,
    BaseRepositoryInterface
)
from vejoias.core.exceptions import (
    JoiaNaoEncontradaError, 
    EstoqueInsuficienteError, 
    ItemNaoEncontradoError, 
    PedidoNaoEncontradoError,
    PagamentoFalhouError
)

# Importações dos Mapeadores (do próprio módulo de infraestrutura)
from .mappers import (
    JoiaMapper, EnderecoMapper, ItemCarrinhoMapper, CarrinhoMapper,
    ItemPedidoMapper, PedidoMapper, UsuarioMapper, CategoriaMapper, SubcategoriaMapper
)

from vejoias.core.use_cases import IRepositorioJoias, IRepositorioCarrinhos, IRepositorioPedidos

# Importações dos Modelos Django
# Assumimos a estrutura de módulos do repositório original para modelos
from vejoias.catalog.models import Joia as JoiaModel, Categoria as CategoriaModel, Subcategoria as SubcategoriaModel
from vejoias.vendas.models import ( 
    Pedido as PedidoModel, 
    ItemPedido as ItemPedidoModel, 
    Endereco as EnderecoModel
)
from vejoias.carrinho.models import Carrinho as CarrinhoModel, ItemCarrinho as ItemCarrinhoModel
from django.contrib.auth import get_user_model

User = get_user_model()


# ====================================================================
# 1. REPOSITÓRIOS (Implementação Django ORM)
# ====================================================================

class JoiaRepositoryDjango(JoiaRepositoryInterface):
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

    def deletar(self, joia_id: int):
        try:
            JoiaModel.objects.get(pk=joia_id).delete()
        except JoiaModel.DoesNotExist:
            raise JoiaNaoEncontradaError(f"Joia ID {joia_id} não pode ser deletada, pois não existe.")
            
    # Adicionando o método buscar_por_id que faltou na interface (embora a JoiaRepositoryInterface não o exija, a BaseRepositoryInterface sim)
    def buscar_por_id(self, id: int) -> Optional[Joia]:
        return self.buscar_por_id(id)


class CarrinhoRepositoryDjango(CarrinhoRepositoryInterface):
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
    def limpar_carrinho(self, usuario: Usuario):
        """Remove todos os ItemCarrinhoModels do CarrinhoModel do usuário."""
        try:
            carrinho_model = CarrinhoModel.objects.get(usuario_id=usuario.id)
            ItemCarrinhoModel.objects.filter(carrinho=carrinho_model).delete()
            carrinho_model.save()
        except CarrinhoModel.DoesNotExist:
            pass # Se o carrinho não existe, não há o que limpar


class PedidoRepositoryDjango(BaseRepositoryInterface): # Mudança da interface para a base, pois a PedidoRepositoryInterface tem métodos diferentes
    """Implementação do PedidoRepository usando o Django ORM."""

    def buscar_por_id(self, id: int) -> Optional[Pedido]:
        try:
            # Pré-carrega usuário e itens
            model = PedidoModel.objects.select_related('usuario').prefetch_related('itens').get(pk=id)
            return PedidoMapper.to_entity(model)
        except PedidoModel.DoesNotExist:
            return None

    def listar(self, usuario: Optional[Usuario] = None) -> List[Pedido]:
        qs = PedidoModel.objects.all().select_related('usuario')
        if usuario:
            qs = qs.filter(usuario_id=usuario.id)
            
        # Não pré-carrega itens na listagem para performance, apenas no buscar_por_id.
        qs = qs.order_by('-data_pedido')
        
        return [PedidoMapper.to_entity(model) for model in qs]

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


# ====================================================================
# 2. GATEWAYS (Mock - Simulação de Serviço Externo)
# ====================================================================

class PagamentoGatewayMock(PagamentoGatewayInterface):
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
    "joia-101": Joia(id="joia-101", nome="Colar Diamante Solitário", preco=Decimal("1500.00"), estoque=5),
    "joia-102": Joia(id="joia-102", nome="Anel Ouro Rosé Zircônia", preco=Decimal("450.50"), estoque=12),
    "joia-103": Joia(id="joia-103", nome="Brincos de Pérola Clássicos", preco=Decimal("300.00"), estoque=20),
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

class JoiaRepository(IRepositorioJoias):
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
        categoria_slug: Optional[str] = None
    ) -> List[Joia]:
        """Implementa IRepositorioJoias. Busca joias filtrando por critérios."""
        
        resultados = []
        for joia in JOIAS_DB.values():
            if em_estoque and joia.estoque <= 0:
                continue
            
            # Simulação básica de busca
            if busca and busca.lower() not in joia.nome.lower():
                continue
                
            # Simulação básica de categoria (não implementada na entidade Joia, mas mantida para o contrato)
            if categoria_slug and categoria_slug not in joia.nome:
                 continue

            resultados.append(joia)
            
        return resultados

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


class CarrinhoRepository(IRepositorioCarrinhos):
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
            CARINHOS_DB[usuario_id] = Carrinho(usuario_id=usuario_id)
            
        return CARINHOS_DB[usuario_id]

    def salvar(self, carrinho: Carrinho) -> Carrinho:
        """Implementa IRepositorioCarrinhos. Salva (ou atualiza) o estado do carrinho."""
        CARINHOS_DB[carrinho.usuario_id] = carrinho
        return carrinho

    def limpar_carrinho(self, usuario: Usuario):
        """Implementa IRepositorioCarrinhos. Remove o carrinho do usuário após o checkout."""
        usuario_id = usuario.id
        if usuario_id in CARINHOS_DB:
            del CARINHOS_DB[usuario_id]


class PedidoRepository(IRepositorioPedidos):
    """
    Implementação do Repositório de Pedidos usando armazenamento in-memory (PEDIDOS_DB).
    Implementa IRepositorioPedidos.
    """
    
    def buscar_por_id(self, pedido_id: str) -> Optional[Pedido]:
        """Implementa IRepositorioPedidos. Busca um pedido pelo seu ID."""
        return PEDIDOS_DB.get(pedido_id)

    def salvar(self, pedido: Pedido) -> Pedido:
        """
        Implementa IRepositorioPedidos. Salva um novo pedido. 
        Em um DB real, o ID seria gerado pelo banco.
        """
        if not pedido.id:
            pedido.id = str(uuid.uuid4())
            pedido.data_pedido = datetime.now()
            
        PEDIDOS_DB[pedido.id] = pedido
        return pedido

    def listar(self, usuario: Optional[Usuario] = None) -> List[Pedido]:
        """Implementa IRepositorioPedidos. Retorna a lista de pedidos, filtrada por usuário se fornecido."""
        if usuario:
            return [
                pedido for pedido in PEDIDOS_DB.values() 
                if pedido.usuario_id == usuario.id
            ]
        # Lista todos os pedidos se nenhum usuário for fornecido (para Admin)
        return list(PEDIDOS_DB.values()) 

    def buscar_por_transacao_id(self, transacao_id: str) -> Optional[Pedido]:
        """
        Implementa IRepositorioPedidos. Busca um pedido pelo ID de Transação,
        crucial para o Use Case de Webhook/IPN.
        """
        return next(
            (pedido for pedido in PEDIDOS_DB.values() if pedido.transacao_id == transacao_id),
            None
        )
