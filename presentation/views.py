# vejoias/presentation/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.db import transaction
from rest_framework import viewsets
from .serializers import JoiaSerializer, CarrinhoSerializer, ItemCarrinhoSerializer, CheckoutSerializer
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.http import Http404, HttpResponseServerError
import requests

# Importamos as classes que criamos nas camadas anteriores
from infrastructure.repositories import (
    JoiaRepository,
    CarrinhoRepository,
    PedidoRepository
)
from infrastructure.gateways import MercadoPagoGateway
from infrastructure.models import Joia as JoiaModel
from core.use_cases import (
    AdicionarItemAoCarrinho,
    RemoverItemDoCarrinho,
    CriarPedido
)
from core.exceptions import (
    EstoqueInsuficienteError,
    ItemNaoEncontradoError,
    CarrinhoVazioError,
    PagamentoFalhouError
)
from core.entities import Usuario, Endereco

from .forms import (
    AdicionarItemCarrinhoForm,
    CheckoutForm,
    RegistroForm,
    LoginForm,
    JoiaForm
)


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
    usuario_entity = Usuario(id=request.user.id, email=request.user.email)
    context = {
        'usuario': request.user,
    }
    return render(request, 'perfil.html', context)


def lista_joias(request):
    """View para a página inicial e listagem de joias."""
    joias = joia_repo.buscar_por_categoria('OURO')
    context = {
        'joias': joias
    }
    return render(request, 'lista_joias.html', context)


def detalhe_joia(request, joia_id):
    """
    Refatorado: Busca os detalhes da joia consumindo a própria API do projeto.
    """
    # A URL da API deve apontar para o host do servidor Django (localhost:8000)
    api_url = f"http://localhost:8000/api/joias/{joia_id}/"
    
    try:
        # Faz a requisição HTTP para buscar o produto
        response = requests.get(api_url)
        response.raise_for_status() # Levanta um erro se o status for 4xx ou 5xx

        # A resposta é JSON, que é convertida em um dicionário Python
        joia_data = response.json()
        
        # O carrinho e o formulário de adição continuam os mesmos
        carrinho = carrinho_repo.buscar_por_usuario(Usuario(id=request.user.id))
        
        context = {
            'joia': joia_data, # joia_data é um dicionário, não mais uma entidade Joia
            'form': AdicionarItemCarrinhoForm(initial={'joia_id': joia_id}),
            'carrinho': carrinho,
        }
        return render(request, 'detalhe_joia.html', context)
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            # Se a API retornar 404, levantamos o 404 do Django para a página web
            raise Http404("Jóia não encontrada.")
        # Para outros erros HTTP, retornamos um erro genérico
        return HttpResponseServerError("Erro de comunicação com o serviço de catálogo.")
    except requests.exceptions.RequestException:
        # Captura erros de rede (ex: a API não está rodando)
        return HttpResponseServerError("Erro ao conectar com o serviço de API. Verifique se o servidor está ativo.")


@login_required
def adicionar_ao_carrinho(request):
    """
    Refatorado para usar o formulário.
    A view agora delega a validação ao formulário AdicionarItemCarrinhoForm.
    """
    if request.method == 'POST':
        form = AdicionarItemCarrinhoForm(request.POST)

        if form.is_valid():
            # Acessamos os dados validados e seguros aqui
            joia_id = form.cleaned_data['joia_id']
            quantidade = form.cleaned_data['quantidade']

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
        else:
            # Se o formulário for inválido, retornamos os erros
            return JsonResponse({'success': False, 'message': 'Erro de validação.', 'errors': form.errors}, status=400)

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
@transaction.atomic
def processar_checkout(request):
    """
    Refatorado para usar o formulário.
    A view agora delega a validação ao formulário CheckoutForm.
    """
    if request.method == 'POST':
        form = CheckoutForm(request.POST)

        if form.is_valid():
            # Acessamos os dados validados e seguros do formulário
            endereco_entity = form.to_endereco_entity()
            tipo_pagamento = form.cleaned_data['tipo_pagamento']

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
                return JsonResponse({'success': True, 'pedido_id': pedido.id}, status=201)
            except (CarrinhoVazioError, EstoqueInsuficienteError, PagamentoFalhouError) as e:
                return JsonResponse({'success': False, 'message': str(e)}, status=400)
        else:
            return JsonResponse({'success': False, 'message': 'Erro de validação no checkout.', 'errors': form.errors}, status=400)

    return JsonResponse({'success': False, 'message': 'Método não permitido'}, status=405)


# ====================================================================
# VIEWS DE AUTENTICAÇÃO
# ====================================================================

def registro(request):
    """
    View para a página de registro de usuário.
    Usa o RegistroForm para validação e criação de um novo usuário.
    """
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Opcional: logar o usuário automaticamente após o registro
            # login(request, user)
            return redirect('login')
    else:
        form = RegistroForm()
    
    context = {'form': form}
    return render(request, 'registro.html', context)


def login_usuario(request):
    """
    View para a página de login.
    Usa o LoginForm e as funções built-in do Django para autenticação.
    """
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return redirect('lista_joias') # Redireciona para a página inicial
    else:
        form = LoginForm()

    context = {'form': form}
    return render(request, 'login.html', context)


@login_required
def logout_usuario(request):
    """
    View para a saída do usuário.
    Usa a função built-in de logout do Django.
    """
    logout(request)
    return redirect('lista_joias') # Redireciona para a página inicial após o logout


@login_required
def dashboard_admin(request):
    """
    View para o painel de administração.
    Apenas usuários logados e com status de staff podem acessar.
    """
    if not request.user.is_staff:
        raise PermissionDenied("Você não tem permissão para acessar esta página.")
    
    # Renderiza o painel de administração
    return render(request, 'admin/dashboard.html')


@login_required
def gerenciar_produtos(request):
    """
    View para listar todos os produtos na área de administração.
    Apenas usuários logados e com status de staff podem acessar.
    """
    if not request.user.is_staff:
        raise PermissionDenied("Você não tem permissão para acessar esta página.")

    # Busca todos os produtos usando o repositório
    joias = joia_repo.buscar_todos() # MÉTODO NECESSÁRIO NO REPOSITÓRIO
    context = {
        'joias': joias
    }
    return render(request, 'admin/produtos.html', context)


# ====================================================================
# VIEWS PARA GERENCIAR PRODUTOS
# ====================================================================
@login_required
def adicionar_joia(request):
    """
    View para adicionar uma nova joia.
    Apenas usuários staff podem acessar.
    """
    if not request.user.is_staff:
        raise PermissionDenied("Você não tem permissão para acessar esta página.")
        
    if request.method == 'POST':
        form = JoiaForm(request.POST)
        if form.is_valid():
            # Cria e salva a nova joia usando o formulário
            form.save()
            return redirect('gerenciar_produtos')
    else:
        form = JoiaForm()
        
    context = {'form': form, 'acao': 'Adicionar'}
    return render(request, 'admin/form_joia.html', context)


@login_required
def editar_joia(request, joia_id):
    """
    View para editar uma joia existente.
    Apenas usuários staff podem acessar.
    """
    if not request.user.is_staff:
        raise PermissionDenied("Você não tem permissão para acessar esta página.")

    try:
        joia_model = JoiaModel.objects.get(id=joia_id)
    except JoiaModel.DoesNotExist:
        return HttpResponse("Joia não encontrada.", status=404)
        
    if request.method == 'POST':
        form = JoiaForm(request.POST, instance=joia_model)
        if form.is_valid():
            form.save()
            return redirect('gerenciar_produtos')
    else:
        form = JoiaForm(instance=joia_model)
        
    context = {'form': form, 'acao': 'Editar'}
    return render(request, 'admin/form_joia.html', context)


@login_required
@require_POST # GARANTE QUE A VIEW SÓ RESPONDA A REQUISIÇÕES POST
def excluir_joia(request, joia_id):
    """
    View para excluir uma joia.
    Apenas usuários staff e com método POST podem acessar.
    """
    if not request.user.is_staff:
        raise PermissionDenied("Você não tem permissão para acessar esta página.")
        
    try:
        joia_model = JoiaModel.objects.get(id=joia_id)
        joia_model.delete()
        # Opcional: Adicione uma mensagem de sucesso para o usuário
        messages.success(request, 'Jóia excluída com sucesso!')
    except JoiaModel.DoesNotExist:
        messages.error(request, 'Jóia não encontrada.')
        
    return redirect('gerenciar_produtos')


class JoiaViewSet(viewsets.ModelViewSet):
    """
    API ViewSet para gerenciar joias.
    Fornece as ações de listagem, criação, atualização e exclusão.
    """
    queryset = JoiaModel.objects.all()
    serializer_class = JoiaSerializer
    
    def get_permissions(self):
        """
        Define as permissões para cada ação.
        Apenas admins podem criar, atualizar ou excluir joias.
        Qualquer um pode ver a lista de joias.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAdminUser]
        else:
            self.permission_classes = []
            
        return [permission() for permission in self.permission_classes]


class CarrinhoAPIView(APIView):
    """
    API View para gerenciar o carrinho do usuário logado.
    Permite visualizar, adicionar, remover e esvaziar itens.
    """
    permission_classes = [IsAuthenticated] # Garante que apenas usuários logados podem usar essa API

    def get(self, request):
        """
        Retorna o carrinho do usuário logado.
        """
        carrinho = carrinho_repo.buscar_por_usuario(Usuario(id=request.user.id))
        serializer = CarrinhoSerializer(carrinho)
        return Response(serializer.data)

    def post(self, request):
        """
        Adiciona um item ao carrinho.
        Espera um JSON com 'joia_id' e 'quantidade'.
        """
        joia_id = request.data.get('joia_id')
        quantidade = request.data.get('quantidade', 1)

        adicionar_item_uc = AdicionarItemAoCarrinho(carrinho_repo, joia_repo)
        
        try:
            carrinho_atualizado = adicionar_item_uc.execute(
                usuario=Usuario(id=request.user.id),
                joia_id=joia_id,
                quantidade=quantidade
            )
            serializer = CarrinhoSerializer(carrinho_atualizado)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except (EstoqueInsuficienteError, ItemNaoEncontradoError) as e:
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        """
        Remove um item do carrinho.
        Espera um JSON com 'joia_id'.
        """
        joia_id = request.data.get('joia_id')
        remover_item_uc = RemoverItemDoCarrinho(carrinho_repo)

        try:
            carrinho_atualizado = remover_item_uc.execute(
                usuario=Usuario(id=request.user.id),
                joia_id=joia_id
            )
            serializer = CarrinhoSerializer(carrinho_atualizado)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except ItemNaoEncontradoError as e:
            return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)
        

    class CheckoutAPIView(APIView):
        """
        API View para processar o checkout de um pedido.
        """
        permission_classes = [IsAuthenticated]

        def post(self, request):
            serializer = CheckoutSerializer(data=request.data)
            if serializer.is_valid():
                # Cria a entidade Endereco a partir dos dados validados
                endereco_entity = serializer.to_endereco_entity()
                tipo_pagamento = serializer.validated_data['tipo_pagamento']

                criar_pedido_uc = CriarPedido(
                    carrinho_repo=carrinho_repo,
                    joia_repo=joia_repo,
                    pedido_repo=pedido_repo,
                    pagamento_gateway=pagamento_gateway
                )

                try:
                    pedido = criar_pedido_uc.execute(
                        usuario=Usuario(id=request.user.id),
                        tipo_pagamento=tipo_pagamento,
                        endereco=endereco_entity
                    )
                    return Response({'message': 'Pedido criado com sucesso!', 'pedido_id': pedido.id}, status=status.HTTP_201_CREATED)
                except (CarrinhoVazioError, EstoqueInsuficienteError, PagamentoFalhouError) as e:
                    return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
