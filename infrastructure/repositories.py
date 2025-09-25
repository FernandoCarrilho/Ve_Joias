from typing import List, Optional
from django.core.exceptions import ObjectDoesNotExist

from vejoias.infrastructure import models
from vejoias.core import entities
from vejoias.core.exceptions import ItemNaoEncontradoError, CarrinhoVazioError

# ====================================================================
# REPOSITÓRIOS: Adaptadores que implementam os protocolos da camada de domínio.
# Responsáveis por converter entre modelos do Django e entidades de negócio.
# ====================================================================

class JoiaRepository:
    """Implementação do IRepositorioJoias para o Django ORM."""

    def buscar_por_id(self, joia_id: int) -> Optional[entities.Joia]:
        """Busca uma joia pelo ID e retorna a entidade de domínio."""
        try:
            joia_model = models.Joia.objects.get(pk=joia_id)
            return self._to_entity(joia_model)
        except ObjectDoesNotExist:
            return None

    def buscar_por_categoria(self, categoria: str) -> List[entities.Joia]:
        """Busca joias por categoria e retorna uma lista de entidades."""
        joia_models = models.Joia.objects.filter(categoria=categoria, disponivel=True)
        return [self._to_entity(model) for model in joia_models]

    def salvar(self, joia_entity: entities.Joia):
        """Salva ou atualiza uma joia a partir da entidade."""
        joia_model, created = models.Joia.objects.get_or_create(
            pk=joia_entity.id,
            defaults=self._to_model_data(joia_entity)
        )
        if not created:
            for attr, value in self._to_model_data(joia_entity).items():
                setattr(joia_model, attr, value)
            joia_model.save()

    def _to_entity(self, joia_model: models.Joia) -> entities.Joia:
        """Converte um modelo Django para uma entidade de domínio."""
        return entities.Joia(
            id=joia_model.id,
            nome=joia_model.nome,
            descricao=joia_model.descricao,
            categoria=joia_model.categoria,
            subcategoria=joia_model.subcategoria,
            tamanho=joia_model.tamanho,
            genero=joia_model.genero,
            tipo=joia_model.tipo_publico,
            preco=joia_model.preco,
            estoque=joia_model.estoque,
            disponivel=joia_model.disponivel
        )

    def _to_model_data(self, joia_entity: entities.Joia) -> dict:
        """Converte uma entidade para um dicionário de dados do modelo."""
        return {
            'nome': joia_entity.nome,
            'descricao': joia_entity.descricao,
            'categoria': joia_entity.categoria,
            'subcategoria': joia_entity.subcategoria,
            'tamanho': joia_entity.tamanho,
            'genero': joia_entity.genero,
            'tipo_publico': joia_entity.tipo,
            'preco': joia_entity.preco,
            'estoque': joia_entity.estoque,
            'disponivel': joia_entity.disponivel
        }


class CarrinhoRepository:
    """Implementação do IRepositorioCarrinhos para o Django ORM."""

    def buscar_por_usuario(self, usuario_entity: entities.Usuario) -> Optional[entities.Carrinho]:
        """Busca o carrinho de um usuário e retorna a entidade de domínio."""
        try:
            usuario_model = models.Usuario.objects.get(pk=usuario_entity.id)
            carrinho_model = models.Carrinho.objects.get(usuario=usuario_model)
            itens = [self._item_to_entity(item) for item in carrinho_model.itens.all()]
            return entities.Carrinho(
                id=carrinho_model.id,
                usuario=usuario_entity,
                itens=itens
            )
        except (ObjectDoesNotExist, models.Usuario.DoesNotExist):
            return None

    def salvar(self, carrinho_entity: entities.Carrinho):
        """Salva ou atualiza o carrinho a partir da entidade."""
        if not carrinho_entity.id:
            raise ValueError("ID do carrinho não pode ser nulo ao salvar.")

        carrinho_model = models.Carrinho.objects.get(pk=carrinho_entity.id)
        
        # Sincroniza os itens do carrinho
        carrinho_model.itens.all().delete()
        for item_entity in carrinho_entity.itens:
            joia_model = models.Joia.objects.get(pk=item_entity.joia.id)
            models.ItemCarrinho.objects.create(
                carrinho=carrinho_model,
                joia=joia_model,
                quantidade=item_entity.quantidade
            )
        carrinho_model.save()
    
    def criar(self, usuario_entity: entities.Usuario) -> entities.Carrinho:
        """Cria um novo carrinho para o usuário."""
        usuario_model = models.Usuario.objects.get(pk=usuario_entity.id)
        carrinho_model = models.Carrinho.objects.create(usuario=usuario_model)
        return entities.Carrinho(
            id=carrinho_model.id,
            usuario=usuario_entity,
            itens=[]
        )

    def _item_to_entity(self, item_model: models.ItemCarrinho) -> entities.ItemCarrinho:
        """Converte um modelo de ItemCarrinho para a entidade de domínio."""
        joia_repo = JoiaRepository()
        joia_entity = joia_repo.buscar_por_id(item_model.joia.id)
        return entities.ItemCarrinho(
            joia=joia_entity,
            quantidade=item_model.quantidade
        )


class PedidoRepository:
    """Implementação do IRepositorioPedidos para o Django ORM."""

    def salvar(self, pedido_entity: entities.Pedido):
        """Salva um pedido completo, incluindo seus itens."""
        usuario_model = models.Usuario.objects.get(pk=pedido_entity.usuario.id)
        endereco_model = models.Endereco.objects.get(pk=pedido_entity.endereco_entrega.id)

        pedido_model = models.Pedido.objects.create(
            usuario=usuario_model,
            endereco_entrega=endereco_model,
            total=pedido_entity.total,
            transacao_id=pedido_entity.transacao_id,
            status=pedido_entity.status
        )
        
        # Salva os itens do pedido
        for item_entity in pedido_entity.itens:
            joia_model = models.Joia.objects.get(pk=item_entity.joia.id)
            models.ItemPedido.objects.create(
                pedido=pedido_model,
                joia=joia_model,
                quantidade=item_entity.quantidade,
                preco_unitario=item_entity.joia.preco
            )