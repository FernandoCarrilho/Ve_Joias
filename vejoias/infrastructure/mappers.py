"""
Mapeadores (Mappers) para converter entre:
1. Modelos do Django ORM
2. Entidades de Domínio (vejoias.core.entities)
"""
from typing import Any, Optional, TypeVar, Type, List, Dict
from django.db import models
from django.apps import apps

# Importa as entidades do Core
from vejoias.core.entities import (
    Usuario as UsuarioEntity,
    Endereco as EnderecoEntity,
    Joia as JoiaEntity,
    Categoria as CategoriaEntity,
    Subcategoria as SubcategoriaEntity,
    Carrinho as CarrinhoEntity,
    ItemCarrinho as ItemCarrinhoEntity,
    Pedido as PedidoEntity,
    ItemPedido as ItemPedidoEntity,
)

# Define tipos genéricos para os modelos
DjangoModel = TypeVar('DjangoModel', bound=models.Model)
Entity = TypeVar('Entity')

# ====================================================================
# Uso de apps.get_model para evitar dependências circulares
# ====================================================================
from django.apps import apps

def get_model(app_label: str, model_name: str):
    """Retorna um modelo do Django de forma segura (lazy loading)."""
    return apps.get_model(app_label, model_name)

# Classes de modelo acessadas via lazy loading
def get_usuario_model():
    return get_model('infrastructure', 'Usuario')

def get_endereco_model():
    return get_model('infrastructure', 'Endereco')

def get_joia_model():
    return get_model('catalog', 'Joia')

def get_categoria_model():
    return get_model('catalog', 'Categoria')

def get_subcategoria_model():
    return get_model('catalog', 'Subcategoria')

def get_carrinho_model():
    return get_model('carrinho', 'Carrinho')

def get_item_carrinho_model():
    return get_model('carrinho', 'ItemCarrinho')

def get_pedido_model():
    return get_model('vendas', 'Pedido')

def get_item_pedido_model():
    return get_model('vendas', 'ItemPedido')


class BaseMapper:
# ... (O restante do código da classe BaseMapper permanece o mesmo)
# ...

    @staticmethod
    def to_entity(model, entity_class):
        """Converte um Model Django genérico para uma Entidade do Core."""
        if not model:
            return None
        
        # Mapeia campos comuns automaticamente (IDs, nomes, slugs)
        entity_data = {
            field.name: getattr(model, field.name)
            for field in entity_class.__dataclass_fields__.values()
            if hasattr(model, field.name)
        }
        
        return entity_class(**entity_data)


# ====================================================================
# MAPERS DO CATÁLOGO
# ====================================================================

class CategoriaMapper(BaseMapper):
    """Mapeador para Categoria."""

    @classmethod
    def model_class(cls) -> Type[models.Model]:
        return get_model('catalog', 'Categoria')

    @staticmethod
    def to_entity(model: Any) -> Optional[CategoriaEntity]:
        """Converte Categoria Model para Categoria Entity."""
        if not model: return None
        return CategoriaEntity(
            id=model.id,
            nome=model.nome,
            slug=model.slug,
            imagem=model.imagem.url if model.imagem else None,
            descricao=model.descricao,
            em_destaque=model.em_destaque
        )

class SubcategoriaMapper(BaseMapper):
    """Mapeador para Subcategoria."""

    @classmethod
    def model_class(cls) -> Type[models.Model]:
        return get_model('catalog', 'Subcategoria')
    @staticmethod
    def to_entity(model: Any) -> Optional[SubcategoriaEntity]:
        """Converte Subcategoria Model para Subcategoria Entity."""
        if not model: return None
        return SubcategoriaEntity(
            id=model.id,
            nome=model.nome,
            slug=model.slug,
            categoria_id=model.categoria_id
        )

class JoiaMapper(BaseMapper):
    """Mapeador para Joia (Produto)."""

    @classmethod
    def model_class(cls) -> Type[models.Model]:
        return get_model('catalog', 'Joia')

    @staticmethod
    def to_entity(model: Any) -> Optional[JoiaEntity]:
        """Converte Joia Model para Joia Entity."""
        if not model: return None
        return JoiaEntity(
            id=model.id,
            nome=model.nome,
            slug=model.slug,
            descricao=model.descricao,
            preco=model.preco,
            estoque=model.estoque,
            desconto=model.desconto,
            em_destaque=model.em_destaque,
            imagem_principal=model.imagem_principal.url if model.imagem_principal else None,
            categoria=CategoriaMapper.to_entity(model.categoria) if model.categoria else None
        )

    @staticmethod
    @classmethod
    def to_model(cls, entity: JoiaEntity, model: Optional[Any] = None) -> Any:
        """Converte Joia Entity para Joia Model."""
        if not model:
            # Se for um novo registro
            model = cls.model_class()()
            
        model.nome = entity.nome
        model.slug = entity.slug
        model.descricao = entity.descricao
        model.preco = entity.preco
        model.estoque = entity.estoque
        model.desconto = entity.desconto
        model.em_destaque = entity.em_destaque
        model.categoria_id = entity.categoria.id if entity.categoria else None
        
        return model


# ====================================================================
# MAPERS DE USUÁRIO E ENDEREÇO
# ====================================================================

class UsuarioMapper(BaseMapper):
    """Mapeador para o Usuário."""

    @classmethod
    def model_class(cls) -> Type[models.Model]:
        return get_model('core', 'Usuario')

    @staticmethod
    def to_entity(model: Any) -> Optional[UsuarioEntity]:
        """Converte Usuario Model para Usuario Entity."""
        if not model: return None
        return UsuarioEntity(
            id=model.id,
            email=model.email,
            first_name=model.first_name,
            last_name=model.last_name,
            telefone=model.telefone,
            cpf=model.cpf,
            is_active=model.is_active,
            is_staff=model.is_staff,
            is_superuser=model.is_superuser
        )

class EnderecoMapper(BaseMapper):
    """Mapeador para Endereço."""

    @classmethod
    def model_class(cls) -> Type[models.Model]:
        return get_model('core', 'Endereco')

    @staticmethod
    def to_entity(model: Any) -> Optional[EnderecoEntity]:
        """Converte Endereco Model para Endereco Entity."""
        if not model: return None
        return EnderecoEntity(
            id=model.id,
            cep=model.cep,
            rua=model.rua,
            numero=model.numero,
            bairro=model.bairro,
            cidade=model.cidade,
            estado=model.estado,
            referencia=model.referencia,
            principal=model.principal
        )

    @staticmethod
    @classmethod
    def to_model(cls, entity: EnderecoEntity, usuario_id: int, model: Optional[Any] = None) -> Any:
        """Converte Endereco Entity para Endereco Model."""
        if not model:
            model = cls.model_class()(usuario_id=usuario_id)
        
        model.cep = entity.cep
        model.rua = entity.rua
        model.numero = entity.numero
        model.bairro = entity.bairro
        model.cidade = entity.cidade
        model.estado = entity.estado
        model.referencia = entity.referencia
        model.principal = entity.principal
        
        return model


# ====================================================================
# MAPERS DO CARRINHO
# ====================================================================

class ItemCarrinhoMapper(BaseMapper):
    """Mapeador para ItemCarrinho."""

    @classmethod
    def model_class(cls) -> Type[models.Model]:
        return get_model('carrinho', 'ItemCarrinho')
    @staticmethod
    def to_entity(model: Any) -> Optional[ItemCarrinhoEntity]:
        """Converte ItemCarrinho Model para ItemCarrinho Entity."""
        if not model: return None
        return ItemCarrinhoEntity(
            id=model.id,
            joia_id=model.joia_id,
            quantidade=model.quantidade,
            # Obtemos o preço unitário e subtotal diretamente do Model (que usa a Joia relacionada)
            preco_unitario=model.preco_unitario, 
            subtotal=model.subtotal
        )

    @staticmethod
    @classmethod
    def to_model(cls, entity: ItemCarrinhoEntity, carrinho_id: int, model: Optional[Any] = None) -> Any:
        """Converte ItemCarrinho Entity para ItemCarrinho Model."""
        if not model:
            model = cls.model_class()(carrinho_id=carrinho_id)
        
        model.joia_id = entity.joia_id
        model.quantidade = entity.quantidade
        
        return model

class CarrinhoMapper(BaseMapper):
    """Mapeador para Carrinho."""

    @classmethod
    def model_class(cls) -> Type[models.Model]:
        return get_model('carrinho', 'Carrinho')
    @staticmethod
    def to_entity(model: Any) -> Optional[CarrinhoEntity]:
        """Converte Carrinho Model para Carrinho Entity, incluindo itens."""
        if not model: return None
        
        itens_entity = [ItemCarrinhoMapper.to_entity(item) for item in model.itens.all()]
        
        return CarrinhoEntity(
            id=model.id,
            usuario_id=model.usuario_id,
            sessao_key=model.sessao_key,
            data_criacao=model.data_criacao,
            data_atualizacao=model.data_atualizacao,
            itens=itens_entity
        )
        
    @staticmethod
    @classmethod
    def to_model(cls, entity: CarrinhoEntity, model: Optional[Any] = None) -> Any:
        """Converte Carrinho Entity para Carrinho Model."""
        if not model:
            model = cls.model_class()()
            
        model.usuario_id = entity.usuario_id
        model.sessao_key = entity.sessao_key
        
        return model


# ====================================================================
# MAPERS DE PEDIDO
# ====================================================================

class ItemPedidoMapper(BaseMapper):
    """Mapeador para ItemPedido."""

    @classmethod
    def model_class(cls) -> Type[models.Model]:
        return get_model('vendas', 'ItemPedido')
    @staticmethod
    def to_entity(model: Any) -> Optional[ItemPedidoEntity]:
        """Converte ItemPedido Model para ItemPedido Entity."""
        if not model: return None
        return ItemPedidoEntity(
            id=model.id,
            joia_nome=model.joia_nome,
            joia_preco=model.joia_preco,
            quantidade=model.quantidade,
            subtotal=model.subtotal,
            pedido_id=model.pedido_id
        )
        
    @staticmethod
    @classmethod
    def to_model(cls, entity: ItemPedidoEntity, pedido_id: int, model: Optional[Any] = None) -> Any:
        """Converte ItemPedido Entity para ItemPedido Model."""
        if not model:
            model = cls.model_class()(pedido_id=pedido_id)
            
        # Snapshot dos dados, não dependem de FK para Joia
        model.joia_nome = entity.joia_nome
        model.joia_preco = entity.joia_preco
        model.quantidade = entity.quantidade
        model.subtotal = entity.subtotal
        
        return model


class PedidoMapper(BaseMapper):
    """Mapeador para Pedido."""

    @classmethod
    def model_class(cls) -> Type[models.Model]:
        return get_model('vendas', 'Pedido')
    @staticmethod
    def to_entity(model: Any) -> Optional[PedidoEntity]:
        """Converte Pedido Model para Pedido Entity, incluindo endereço snapshot."""
        if not model: return None
        
        # Mapeia o snapshot de endereço para a Entidade EnderecoEntity
        endereco_entity = EnderecoEntity(
            # Campos do EnderecoEntity que são opcionais podem ser omitidos
            id=None,
            principal=False,
            # Campos mapeados do snapshot do Pedido
            cep=model.cep_entrega,
            rua=model.rua_entrega,
            numero=model.numero_entrega,
            bairro=model.bairro_entrega,
            cidade=model.cidade_entrega,
            estado=model.estado_entrega,
            referencia=model.referencia_entrega
        )
        
        # Mapeia os itens do pedido
        itens_entity = [ItemPedidoMapper.to_entity(item) for item in model.itens.all()]
        
        return PedidoEntity(
            id=model.id,
            usuario_id=model.usuario_id,
            data_pedido=model.data_pedido,
            status=model.status,
            total_pedido=model.total_pedido,
            tipo_pagamento=model.tipo_pagamento,
            endereco_entrega=endereco_entity,
            telefone_whatsapp=model.telefone_whatsapp,
            itens=itens_entity
            # Transacao não está mapeada aqui, pois seria carregada por outro serviço/mapper
        )
        
    @staticmethod
    @classmethod
    def to_model(cls, entity: PedidoEntity, model: Optional[Any] = None) -> Any:
        """Converte Pedido Entity para Pedido Model."""
        if not model:
            model = cls.model_class()(usuario_id=entity.usuario_id)
            
        model.status = entity.status
        model.total_pedido = entity.total_pedido
        model.tipo_pagamento = entity.tipo_pagamento
        model.telefone_whatsapp = entity.telefone_whatsapp
        
        # Mapeia a Entidade Endereco para os campos snapshot do Model
        model.cep_entrega = entity.endereco_entrega.cep
        model.rua_entrega = entity.endereco_entrega.rua
        model.numero_entrega = entity.endereco_entrega.numero
        model.bairro_entrega = entity.endereco_entrega.bairro
        model.cidade_entrega = entity.endereco_entrega.cidade
        model.estado_entrega = entity.endereco_entrega.estado
        model.referencia_entrega = entity.endereco_entrega.referencia
        
        return model


