from rest_framework import serializers
from vejoias.infrastructure.models import Joia as JoiaModel, Endereco
from vejoias.infrastructure.models import Carrinho as CarrinhoModel, ItemCarrinho as ItemCarrinhoModel

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

    # Campo de Pagamento
    TIPO_PAGAMENTO_CHOICES = [
        ('PIX', 'PIX'),
        ('CARTAO', 'Cartão de Crédito'),
    ]
    tipo_pagamento = serializers.ChoiceField(choices=TIPO_PAGAMENTO_CHOICES)

    # NOVO CAMPO: Telefone para o WhatsApp
    telefone_whatsapp = serializers.CharField(
        max_length=15,
        required=True, # O campo é obrigatório para a notificação
        help_text="Número de telefone no formato DDI+DDD+Número (Ex: 5511987654321)"
    )

    # Método para criar a Entidade Endereco (se necessário, adapte para incluir o telefone)
    def to_endereco_entity(self) -> Endereco:
        return Endereco(
            linha1=self.validated_data['endereco_linha1'],
            cidade=self.validated_data['cidade'],
            estado=self.validated_data['estado'],
            cep=self.validated_data['cep'],
            # Inclua o telefone na entidade Endereco se o seu modelo o aceitar
        )
        
    # Opcional: Se a API precisar de validação rigorosa (limpeza) como no forms.py:
    def validate_telefone_whatsapp(self, value):
        import re
        
        numero_limpo = re.sub(r'\D', '', value)
        
        if not (12 <= len(numero_limpo) <= 13):
            raise serializers.ValidationError(
                "O telefone deve ter entre 12 e 13 dígitos no formato DDI+DDD+Número."
            )
            
        # Garante que o número está padronizado (EvolutionAPI) antes de ser processado
        if not (numero_limpo.startswith('55') or len(numero_limpo) == 10 or len(numero_limpo) == 11):
            raise serializers.ValidationError("Formato de telefone inválido. Inclua o DDI.")
        
        # O Use Case deve lidar com a normalização final (adicionar o '55' se faltar) se for necessário
        # ou você pode adicionar a lógica de padronização aqui.
        if len(numero_limpo) in [10, 11] and not numero_limpo.startswith('55'):
            numero_limpo = '55' + numero_limpo
            
        return numero_limpo
