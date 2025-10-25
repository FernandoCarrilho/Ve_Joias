"""
Mapeadores (Mappers) para converter entre:
1. Modelos do Django ORM (vejoias.infrastructure.models)
2. Entidades de Domínio (vejoias.core.entities)

Isto garante que a camada Core trabalhe apenas com entidades puras.
"""
from typing import List, Optional

# Importa as Entidades Puras do Core
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
    TransacaoPagamento as TransacaoPagamentoEntity
)

# Importa os Modelos do Django ORM da Infraestrutura
from .models import (
    Usuario,
    Endereco,
    Joia,
    Categoria,
    Subcategoria,
    Carrinho,
    ItemCarrinho,
    Pedido,
    ItemPedido
)


class BaseMapper:
    """Classe base para Mapeadores com métodos de conversão genéricos."""

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
    """Mapeador para Categoria e Subcategoria."""

    @staticmethod
    def to_entity(model: Categoria) -> CategoriaEntity:
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
    @staticmethod
    def to_entity(model: Subcategoria) -> SubcategoriaEntity:
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

    @staticmethod
    def to_entity(model: Joia) -> JoiaEntity:
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
    def to_model(entity: JoiaEntity, model: Optional[Joia] = None) -> Joia:
        """Converte Joia Entity para Joia Model."""
        if not model:
            # Se for um novo registro
            model = Joia()
            
        model.nome = entity.nome
        model.slug = entity.slug
        model.descricao = entity.descricao
        model.preco = entity.preco
        model.estoque = entity.estoque
        model.desconto = entity.desconto
        model.em_destaque = entity.em_destaque
        model.categoria = entity.categoria.id if entity.categoria else None
        
        return model


# ====================================================================
# MAPERS DE USUÁRIO E ENDEREÇO
# ====================================================================

class UsuarioMapper(BaseMapper):
    """Mapeador para o Usuário."""

    @staticmethod
    def to_entity(model: Usuario) -> UsuarioEntity:
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

    @staticmethod
    def to_entity(model: Endereco) -> EnderecoEntity:
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
    def to_model(entity: EnderecoEntity, usuario_id: int, model: Optional[Endereco] = None) -> Endereco:
        """Converte Endereco Entity para Endereco Model."""
        if not model:
            model = Endereco(usuario_id=usuario_id)
        
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
    @staticmethod
    def to_entity(model: ItemCarrinho) -> ItemCarrinhoEntity:
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
    def to_model(entity: ItemCarrinhoEntity, carrinho_id: int, model: Optional[ItemCarrinho] = None) -> ItemCarrinho:
        """Converte ItemCarrinho Entity para ItemCarrinho Model."""
        if not model:
            model = ItemCarrinho(carrinho_id=carrinho_id)
        
        model.joia_id = entity.joia_id
        model.quantidade = entity.quantidade
        
        return model

class CarrinhoMapper(BaseMapper):
    """Mapeador para Carrinho."""
    @staticmethod
    def to_entity(model: Carrinho) -> CarrinhoEntity:
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
    def to_model(entity: CarrinhoEntity, model: Optional[Carrinho] = None) -> Carrinho:
        """Converte Carrinho Entity para Carrinho Model."""
        if not model:
            model = Carrinho()
            
        model.usuario_id = entity.usuario_id
        model.sessao_key = entity.sessao_key
        
        return model


# ====================================================================
# MAPERS DE PEDIDO
# ====================================================================

class ItemPedidoMapper(BaseMapper):
    """Mapeador para ItemPedido."""
    @staticmethod
    def to_entity(model: ItemPedido) -> ItemPedidoEntity:
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
    def to_model(entity: ItemPedidoEntity, pedido_id: int, model: Optional[ItemPedido] = None) -> ItemPedido:
        """Converte ItemPedido Entity para ItemPedido Model."""
        if not model:
            model = ItemPedido(pedido_id=pedido_id)
            
        # Snapshot dos dados, não dependem de FK para Joia
        model.joia_nome = entity.joia_nome
        model.joia_preco = entity.joia_preco
        model.quantidade = entity.quantidade
        model.subtotal = entity.subtotal
        
        return model


class PedidoMapper(BaseMapper):
    """Mapeador para Pedido."""
    @staticmethod
    def to_entity(model: Pedido) -> PedidoEntity:
        """Converte Pedido Model para Pedido Entity, incluindo endereço snapshot."""
        if not model: return None
        
        # Mapeia o snapshot de endereço para a Entidade EnderecoEntity
        endereco_entity = EnderecoEntity(
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
    def to_model(entity: PedidoEntity, model: Optional[Pedido] = None) -> Pedido:
        """Converte Pedido Entity para Pedido Model."""
        if not model:
            model = Pedido(usuario_id=entity.usuario_id)
            
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
