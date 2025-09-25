# vejoias/presentation/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.db import transaction

from vejoias.infrastructure.repositories import (
    JoiaRepository, 
    CarrinhoRepository, 
    PedidoRepository
)
from vejoias.infrastructure.gateways import MercadoPagoGateway
from vejoias.infrastructure.models import Joia as JoiaModel # Importa o modelo Django
from vejoias.core.use_cases import (
    AdicionarItemAoCarrinho, 
    RemoverItemDoCarrinho, 
    CriarPedido
)
from vejoias.core.exceptions import (
    EstoqueInsuficienteError, 
    ItemNaoEncontradoError, 
    CarrinhoVazioError,
    PagamentoFalhouError
)
from vejoias.core.entities import Usuario, Endereco # Importa as entidades de domínio

# ====================================================================
# VIEWS: Orquestram a requisição, a execução dos casos de uso e a resposta.
# ====================================================================

# -- Instância dos Repositórios e Gateways (dependências) --
joia_repo = JoiaRepository()
carrinho_repo = CarrinhoRepository()
pedido_repo = PedidoRepository()
pagamento_gateway = MercadoPagoGateway()

@login_required
def meu_perfil(request):
    """View para a página de perfil do usuário."""
    # A view 'pega' a entidade de domínio do usuário
    usuario_entity = Usuario(id=request.user.id, email=request.user.email)

    # Exemplo: chamar um caso de uso para buscar os pedidos do usuário
    # pedidos = BuscarPedidosDoUsuario(pedido_repo).execute(usuario_entity)
    
    context = {
        'usuario': request.user,
        # 'pedidos': pedidos
    }
    return render(request, 'perfil.html', context)


def lista_joias(request):
    """View para a página inicial e listagem de joias."""
    # A view chama o repositório diretamente para obter os dados de exibição
    joias = joia_repo.buscar_por_categoria('OURO') # Exemplo de busca
    
    context = {
        'joias': joias
    }
    return render(request, 'lista_joias.html', context)


def detalhe_joia(request, joia_id):
    """View para a página de detalhes de uma joia específica."""
    try:
        joia = joia_repo.buscar_por_id(joia_id)
        if not joia:
            return HttpResponse("Jóia não encontrada", status=404)
        
        context = {
            'joia': joia
        }
        return render(request, 'detalhe_joia.html', context)
    except ItemNaoEncontradoError as e:
        return HttpResponse(str(e), status=404)


@login_required
def adicionar_ao_carrinho(request):
    """
    Endpoint para adicionar um item ao carrinho via requisição POST.
    Chama o caso de uso `AdicionarItemAoCarrinho`.
    """
    if request.method == 'POST':
        joia_id = request.POST.get('joia_id')
        quantidade = int(request.POST.get('quantidade', 1))

        # Pega a entidade de domínio do usuário
        usuario_entity = Usuario(id=request.user.id)
        
        adicionar_item_uc = AdicionarItemAoCarrinho(carrinho_repo, joia_repo)

        try:
            carrinho_atualizado = adicionar_item_uc.execute(
                usuario=usuario_entity, 
                joia_id=joia_id, 
                quantidade=quantidade
            )
            return JsonResponse({
                'success': True, 
                'message': 'Item adicionado ao carrinho!',
                'total_itens': sum(item.quantidade for item in carrinho_atualizado.itens)
            })
        except (EstoqueInsuficienteError, ItemNaoEncontradoError) as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'}, status=405)


@login_required
def ver_carrinho(request):
    """View para a página do carrinho de compras."""
    usuario_entity = Usuario(id=request.user.id)
    carrinho = carrinho_repo.buscar_por_usuario(usuario_entity)
    
    context = {
        'carrinho': carrinho
    }
    return render(request, 'carrinho.html', context)


@login_required
@transaction.atomic # Garante que todas as operações de DB sejam atômicas
def processar_checkout(request):
    """
    Endpoint para processar o checkout e criar um pedido.
    Chama o caso de uso `CriarPedido`.
    """
    if request.method == 'POST':
        # Exemplo de como pegar os dados do formulário de checkout
        endereco_entrega_model = get_object_or_404(
            JoiaModel, pk=request.POST.get('endereco_id')
        )
        endereco_entity = Endereco(
            cep=endereco_entrega_model.cep,
            rua=endereco_entrega_model.rua,
            numero=endereco_entrega_model.numero,
            bairro=endereco_entrega_model.bairro,
            cidade=endereco_entrega_model.cidade,
            estado=endereco_entrega_model.estado
        )
        tipo_pagamento = request.POST.get('tipo_pagamento')
        
        usuario_entity = Usuario(id=request.user.id)
        
        criar_pedido_uc = CriarPedido(
            carrinho_repo, 
            joia_repo, 
            pedido_repo, 
            pagamento_gateway
        )
        
        try:
            pedido = criar_pedido_uc.execute(
                usuario=usuario_entity, 
                tipo_pagamento=tipo_pagamento, 
                endereco=endereco_entity
            )
            # Redireciona para uma página de sucesso
            return JsonResponse({'success': True, 'pedido_id': pedido.id}, status=201)
        
        except (CarrinhoVazioError, EstoqueInsuficienteError, PagamentoFalhouError) as e:
            # Retorna um erro amigável para o frontend
            return JsonResponse({'success': False, 'message': str(e)}, status=400)
    
    return JsonResponse({'success': False, 'message': 'Método não permitido'}, status=405)
