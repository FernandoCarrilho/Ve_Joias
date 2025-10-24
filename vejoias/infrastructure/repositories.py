"""
Camada de Infraestrutura: Implementação de Repositórios e Gateways.

Esta camada traduz as operações abstratas definidas nas Interfaces da Core
em chamadas concretas ao framework (Django ORM, APIs externas, etc.).
"""
from typing import List, Optional
from django.db.models import Q, F, Sum
from django.db import transaction
from decimal import Decimal
import random # Para o Mock de Pagamento

# Importações da Camada CORE (ENTIDADES e INTERFACES)
from vejoias.core.entities import (
    Joia, Categoria, Carrinho, ItemCarrinho, Pedido, ItemPedido, 
    Usuario, Endereco, TransacaoPagamento
)
from vejoias.core.interfaces import (
    JoiaRepositoryInterface, 
    CarrinhoRepositoryInterface, 
    PedidoRepositoryInterface, 
    PagamentoGatewayInterface
)
from vejoias.core.exceptions import (
    JoiaNaoEncontradaError, 
    EstoqueInsuficienteError, 
    ItemNaoEncontradoError, 
    PedidoNaoEncontradoError,
    PagamentoFalhouError
)

# Importações dos Modelos Django
from vejoias.catalog.models import Joia as JoiaModel, Categoria as CategoriaModel

# Modelos do app Vendas - Removido ItemCarrinhoModel daqui
from vejoias.vendas.models import ( 
    Pedido as PedidoModel, 
    ItemPedido as ItemPedidoModel, 
    Endereco as EnderecoModel
)

# Modelos do app Carrinho - Adicionado ItemCarrinhoModel aqui
from vejoias.carrinho.models import Carrinho as CarrinhoModel, ItemCarrinho as ItemCarrinhoModel

from django.contrib.auth import get_user_model

User = get_user_model()


# ====================================================================
# MAPERS (Conversão Model <-> Entidade)
# ====================================================================

# Mappers de Entidade para Modelo (usados na escrita) e vice-versa (usados na leitura)

def map_categoria_model_to_entity(model: CategoriaModel) -> Categoria:
    """Converte CategoriaModel em Entidade Categoria."""
    return Categoria(
        id=model.id,
        nome=model.nome,
        slug=model.slug,
        descricao=model.descricao
    )

def map_joia_model_to_entity(model: JoiaModel) -> Joia:
    """Converte JoiaModel em Entidade Joia."""
    return Joia(
        id=model.id,
        nome=model.nome,
        descricao=model.descricao,
        preco=float(model.preco),
        estoque=model.estoque,
        categoria=map_categoria_model_to_entity(model.categoria) if model.categoria else None,
        material=model.material,
        peso_gramas=float(model.peso_gramas) if model.peso_gramas else 0.0,
        dimensoes=model.dimensoes,
        imagem_url=model.imagem_url,
        is_destaque=model.is_destaque
    )

def map_user_model_to_entity(user: User) -> Usuario:
    """Converte Django User em Entidade Usuario (simplificado)."""
    return Usuario(
        id=user.id,
        email=user.email,
        first_name=user.first_name,
        last_name=user.last_name,
        # Assume que o modelo User tem is_staff para admin
        is_admin=user.is_staff 
    )

def map_endereco_model_to_entity(model: EnderecoModel) -> Endereco:
    """Converte EnderecoModel em Entidade Endereco (usado em listagem de endereços)."""
    return Endereco(
        id=model.id,
        usuario_id=model.usuario_id,
        apelido=model.apelido,
        cep=model.cep,
        rua=model.rua,
        numero=model.numero,
        complemento=model.complemento,
        bairro=model.bairro,
        cidade=model.cidade,
        estado=model.estado,
    )

def map_item_carrinho_model_to_entity(model: ItemCarrinhoModel) -> ItemCarrinho:
    """Converte ItemCarrinhoModel em Entidade ItemCarrinho."""
    return ItemCarrinho(
        joia=map_joia_model_to_entity(model.joia),
        quantidade=model.quantidade
    )


# ====================================================================
# 1. REPOSITÓRIOS (Implementação Django ORM)
# ====================================================================

class JoiaRepositoryDjango(JoiaRepositoryInterface):
    """Implementação do JoiaRepository usando o Django ORM."""

    def buscar_por_id(self, id: int) -> Optional[Joia]:
        try:
            model = JoiaModel.objects.select_related('categoria').get(pk=id)
            return map_joia_model_to_entity(model)
        except JoiaModel.DoesNotExist:
            return None

    def buscar_por_criterios(
        self, 
        em_estoque: bool, 
        busca: Optional[str] = None, 
        categoria_slug: Optional[str] = None
    ) -> List[Joia]:
        
        qs = JoiaModel.objects.all().select_related('categoria')
        
        if em_estoque:
            qs = qs.filter(estoque__gt=0)

        if busca:
            # Busca por nome ou descrição
            qs = qs.filter(Q(nome__icontains=busca) | Q(descricao__icontains=busca))
            
        if categoria_slug:
            qs = qs.filter(categoria__slug=categoria_slug)
            
        return [map_joia_model_to_entity(model) for model in qs]
    
    @transaction.atomic
    def salvar(self, joia: Joia) -> Joia:
        """Salva ou atualiza uma Joia, convertendo a entidade para o modelo."""
        categoria_model = None
        if joia.categoria and joia.categoria.id:
            try:
                categoria_model = CategoriaModel.objects.get(pk=joia.categoria.id)
            except CategoriaModel.DoesNotExist:
                pass # Caso a categoria não exista, salva sem categoria
                
        # Atualiza ou cria o modelo
        if joia.id:
            try:
                model = JoiaModel.objects.get(pk=joia.id)
            except JoiaModel.DoesNotExist:
                raise JoiaNaoEncontradaError(f"Joia ID {joia.id} não existe para atualização.")
                
            model.nome = joia.nome
            model.descricao = joia.descricao
            model.preco = Decimal(joia.preco)
            model.estoque = joia.estoque
            model.categoria = categoria_model
            model.material = joia.material
            model.peso_gramas = Decimal(joia.peso_gramas) if joia.peso_gramas else None
            model.dimensoes = joia.dimensoes
            model.imagem_url = joia.imagem_url
            model.is_destaque = joia.is_destaque
        else:
            model = JoiaModel(
                nome=joia.nome,
                descricao=joia.descricao,
                preco=Decimal(joia.preco),
                estoque=joia.estoque,
                categoria=categoria_model,
                material=joia.material,
                peso_gramas=Decimal(joia.peso_gramas) if joia.peso_gramas else None,
                dimensoes=joia.dimensoes,
                imagem_url=joia.imagem_url,
                is_destaque=joia.is_destaque
            )
            
        model.save()
        joia.id = model.id # Garante que a entidade retorne com o ID
        return joia

    def deletar(self, joia_id: int):
        try:
            JoiaModel.objects.get(pk=joia_id).delete()
        except JoiaModel.DoesNotExist:
            raise JoiaNaoEncontradaError(f"Joia ID {joia_id} não pode ser deletada, pois não existe.")


class CarrinhoRepositoryDjango(CarrinhoRepositoryInterface):
    """Implementação do CarrinhoRepository usando o Django ORM."""

    def buscar_por_usuario(self, usuario: Usuario) -> Carrinho:
        try:
            # Tenta encontrar o carrinho e pré-carrega os itens e as joias relacionadas
            carrinho_model = CarrinhoModel.objects.select_related('usuario').prefetch_related(
                models.Prefetch(
                    'itens',
                    queryset=ItemCarrinhoModel.objects.select_related('joia__categoria')
                )
            ).get(usuario_id=usuario.id)
        except CarrinhoModel.DoesNotExist:
            # Cria um novo carrinho se não existir (regra da interface)
            user_model = User.objects.get(pk=usuario.id)
            carrinho_model = CarrinhoModel.objects.create(usuario=user_model)

        itens_entity = [
            map_item_carrinho_model_to_entity(item_model)
            for item_model in carrinho_model.itens.all()
        ]
        
        return Carrinho(
            id=carrinho_model.id,
            usuario=usuario,
            itens=itens_entity
        )

    @transaction.atomic
    def salvar(self, carrinho: Carrinho) -> Carrinho:
        """Salva a Entidade Carrinho, sincronizando os ItemCarrinhoModels."""
        
        if not carrinho.id:
            # Isso só acontece se o mapeamento falhar, pois buscar_por_usuario já deve criar um ID.
            raise ValueError("Carrinho deve ter um ID para ser salvo.")
        
        carrinho_model = CarrinhoModel.objects.get(pk=carrinho.id)
        
        # 1. Identifica os Joia IDs que devem estar no carrinho
        joia_ids_atuais = {item.joia.id: item.quantidade for item in carrinho.itens}
        
        # 2. Atualiza ou Cria os itens existentes/novos
        for joia_id, quantidade in joia_ids_atuais.items():
            joia_model = JoiaModel.objects.get(pk=joia_id)
            
            # Use get_or_create para evitar race conditions ou erros de unicidade
            item, created = ItemCarrinhoModel.objects.get_or_create(
                carrinho=carrinho_model, 
                joia=joia_model,
                defaults={'quantidade': quantidade}
            )
            
            if not created:
                item.quantidade = quantidade
                item.save()

        # 3. Deleta itens que foram removidos da entidade
        ItemCarrinhoModel.objects.filter(
            carrinho=carrinho_model
        ).exclude(joia_id__in=joia_ids_atuais.keys()).delete()
        
        carrinho_model.save()
        return carrinho

    @transaction.atomic
    def limpar_carrinho(self, usuario: Usuario):
        """Remove todos os ItemCarrinhoModels do CarrinhoModel do usuário."""
        try:
            carrinho_model = CarrinhoModel.objects.get(usuario_id=usuario.id)
            ItemCarrinhoModel.objects.filter(carrinho=carrinho_model).delete()
            carrinho_model.save()
        except CarrinhoModel.DoesNotExist:
            # Se o carrinho não existe, não há o que limpar
            pass


class PedidoRepositoryDjango(PedidoRepositoryInterface):
    """Implementação do PedidoRepository usando o Django ORM."""

    def _map_pedido_model_to_entity(self, model: PedidoModel) -> Pedido:
        """Converte PedidoModel em Entidade Pedido, incluindo itens e endereço."""
        # 1. Mapeia Endereço (armazenado como JSON no modelo)
        endereco_data = model.endereco_entrega_json
        endereco_entity = Endereco(
            # O ID do endereço na entidade Pedido é o snapshot JSON.
            cep=endereco_data.get('cep', ''),
            rua=endereco_data.get('rua', ''),
            numero=endereco_data.get('numero', ''),
            complemento=endereco_data.get('complemento', ''),
            bairro=endereco_data.get('bairro', ''),
            cidade=endereco_data.get('cidade', ''),
            estado=endereco_data.get('estado', ''),
        )
        
        # 2. Mapeia Usuário (precisamos buscar o modelo Django para o mapeamento completo)
        user_model = model.usuario
        usuario_entity = map_user_model_to_entity(user_model)

        # 3. Mapeia Itens
        itens_entity = [
            ItemPedido(
                joia_id=item_model.joia_id,
                nome_joia=item_model.nome_joia,
                preco_unitario=float(item_model.preco_unitario),
                quantidade=item_model.quantidade
            ) 
            for item_model in model.itens.all()
        ]
        
        # 4. Cria a Entidade Pedido
        return Pedido(
            id=model.id,
            usuario=usuario_entity,
            itens=itens_entity,
            endereco_entrega=endereco_entity,
            valor_total=float(model.valor_total),
            status=model.status,
            data_pedido=model.data_pedido
        )

    def buscar_por_id(self, id: int) -> Optional[Pedido]:
        try:
            model = PedidoModel.objects.select_related('usuario').prefetch_related('itens').get(pk=id)
            return self._map_pedido_model_to_entity(model)
        except PedidoModel.DoesNotExist:
            return None

    def listar(self, usuario: Optional[Usuario] = None) -> List[Pedido]:
        qs = PedidoModel.objects.all().select_related('usuario').prefetch_related('itens')
        if usuario:
            qs = qs.filter(usuario_id=usuario.id)
            
        qs = qs.order_by('-data_pedido')
        
        return [self._map_pedido_model_to_entity(model) for model in qs]

    @transaction.atomic
    def salvar(self, pedido: Pedido) -> Pedido:
        """Salva a Entidade Pedido, incluindo os itens."""
        
        # 1. Prepara dados do PedidoModel
        endereco_json = {
            'cep': pedido.endereco_entrega.cep,
            'rua': pedido.endereco_entrega.rua,
            'numero': pedido.endereco_entrega.numero,
            'complemento': pedido.endereco_entrega.complemento,
            'bairro': pedido.endereco_entrega.bairro,
            'cidade': pedido.endereco_entrega.cidade,
            'estado': pedido.endereco_entrega.estado,
        }
        
        # Garante que o usuário existe no DB
        user_model = User.objects.get(pk=pedido.usuario.id)
        
        # 2. Cria ou Atualiza o Pedido principal
        if pedido.id:
            model = PedidoModel.objects.get(pk=pedido.id)
            model.status = pedido.status
            model.save()
            # Se for atualização, não precisamos recriar os itens (apenas o status muda)
        else:
            model = PedidoModel.objects.create(
                usuario=user_model,
                endereco_entrega_json=endereco_json,
                valor_total=Decimal(pedido.valor_total),
                status=pedido.status
            )
            pedido.id = model.id
            
            # 3. Cria os Itens do Pedido (apenas na criação)
            item_models = [
                ItemPedidoModel(
                    pedido=model,
                    joia_id=item.joia_id,
                    nome_joia=item.nome_joia,
                    preco_unitario=Decimal(item.preco_unitario),
                    quantidade=item.quantidade
                )
                for item in pedido.itens
            ]
            ItemPedidoModel.objects.bulk_create(item_models)
            
            # 4. Baixa o estoque das joias (Regra crítica de negócio na Infraestrutura)
            # Para cada item, diminui o estoque da JoiaModel correspondente
            for item in pedido.itens:
                JoiaModel.objects.filter(pk=item.joia_id).update(
                    estoque=F('estoque') - item.quantidade
                )
                
        return pedido


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
            if pedido.valor_total > 5000:
                # Valores altos ficam Pendentes no Mock
                status = "PENDENTE"
                mensagem = "Pagamento sob revisão de segurança (alto valor)."
            else:
                status = "APROVADO"
                mensagem = "Pagamento processado com sucesso pelo Mock."
                
        else:
            # Falha
            status = "REJEITADO"
            mensagem = "Pagamento rejeitado: Cartão inválido ou limite excedido (Mock)."
            raise PagamentoFalhouError(mensagem)
            
        return TransacaoPagamento(
            transacao_id_externo=f"MOCK-{random.randint(100000, 999999)}",
            status=status,
            valor=pedido.valor_total,
            mensagem=mensagem
        )

    def verificar_status(self, transacao_id: str) -> TransacaoPagamento:
        """Simula a verificação de status (ex: para boleto/pix)."""
        # Simplificação: se a transação começa com MOCK e tem 6 dígitos, retorna PENDENTE
        if transacao_id.startswith("MOCK-"):
             return TransacaoPagamento(
                transacao_id_externo=transacao_id,
                status="PENDENTE",
                valor=0.0,
                mensagem="Status Pendente (Mock: aguardando confirmação)."
            )
        else:
            return TransacaoPagamento(
                status="REJEITADO",
                valor=0.0,
                mensagem="Transação Mock não encontrada."
            )
