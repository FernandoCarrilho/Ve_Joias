from rest_framework import serializers
from infrastructure.models import Joia as JoiaModel, Endereco
from infrastructure.models import Carrinho as CarrinhoModel, ItemCarrinho as ItemCarrinhoModel

class JoiaSerializer(serializers.ModelSerializer):
    class Meta:
        model = JoiaModel
        fields = ['id', 'nome', 'descricao', 'preco', 'estoque', 'categoria']


# ====================================================================
# SERIALIZERS PARA O CARRINHO
# ====================================================================

class ItemCarrinhoSerializer(serializers.ModelSerializer):
    """
    Serializer para o item do carrinho.
    Usa o JoiaSerializer para representar a joia aninhada.
    """
    joia = JoiaSerializer(read_only=True)
    joia_id = serializers.CharField(write_only=True) # Campo para receber o ID da joia na requisição POST

    class Meta:
        model = ItemCarrinhoModel
        fields = ['joia', 'joia_id', 'quantidade']
        extra_kwargs = {'quantidade': {'required': False, 'allow_null': True}}


class CarrinhoSerializer(serializers.ModelSerializer):
    """
    Serializer principal para o carrinho de compras.
    Representa a lista de itens usando o ItemCarrinhoSerializer.
    """
    itens = ItemCarrinhoSerializer(many=True, read_only=True)
    
    class Meta:
        model = CarrinhoModel
        fields = ['id', 'usuario', 'itens']
        read_only_fields = ['usuario']


# SERIALIZER PARA CHECKOUT
# ====================================================================
class CheckoutSerializer(serializers.Serializer):
    """
    Serializer para a validação dos dados de checkout.
    """
    tipo_pagamento = serializers.CharField(max_length=50)
    cep = serializers.CharField(max_length=9)
    rua = serializers.CharField(max_length=255)
    numero = serializers.CharField(max_length=50)
    bairro = serializers.CharField(max_length=255)
    cidade = serializers.CharField(max_length=255)
    estado = serializers.CharField(max_length=2)

    def to_endereco_entity(self):
        """
        Converte os dados validados do serializer para uma entidade Endereco.
        """
        return Endereco(
            cep=self.validated_data['cep'],
            rua=self.validated_data['rua'],
            numero=self.validated_data['numero'],
            bairro=self.validated_data['bairro'],
            cidade=self.validated_data['cidade'],
            estado=self.validated_data['estado'],
        )
