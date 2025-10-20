from django.views import View
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404, HttpResponseRedirect
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required
from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
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
from django.views.generic import ListView 
from vejoias.core.use_cases import AtualizarStatusManual, StatusInvalidoError, BuscarPedidoPorId, PedidoNaoEncontradoError



# Importamos as classes que criamos nas camadas anteriores
from vejoias.infrastructure.repositories import (
    JoiaRepository,
    CarrinhoRepository,
    PedidoRepository,
)
from vejoias.infrastructure.gateways import MercadoPagoGateway, EvolutionAPIGateway, EmailServiceGateway
from vejoias.infrastructure.models import Joia as JoiaModel
from vejoias.core.use_cases import (
    AdicionarItemAoCarrinho,
    RemoverItemDoCarrinho,
    CriarPedido,
    ListarPedidos,
    BuscarPedidosPorUsuario, # Adicionado novo Use Case
    
)
from vejoias.core.exceptions import (
    EstoqueInsuficienteError,
    ItemNaoEncontradoError,
    CarrinhoVazioError,
    PagamentoFalhouError,
)
from vejoias.core.entities import Usuario, Endereco
from vejoias.core.use_cases import AtualizarStatusPedido

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
whatsapp_notifier = EvolutionAPIGateway()
email_service = EmailServiceGateway()
# pedido_repo = PedidoRepository() # Linha duplicada removida
notificacao_service = AtualizarStatusManual(pedido_repo)


@login_required
def meu_perfil(request):
    """View para a página de perfil do usuário."""
    # O contexto já estava correto, mas garantindo as URLs nomeadas.
    context = {
        'usuario': request.user,
    }
    return render(request, 'perfil.html', context)


# -- NOVAS VIEWS PARA ROTEAMENTO DE PERFIL (Vazias por enquanto) --

@login_required
def editar_perfil(request):
    """View placeholder para Editar Informações de Perfil."""
    # Aqui, você usaria um formulário para User/Profile
    context = {'usuario': request.user}
    return render(request, 'perfil/editar_perfil.html', context)

@login_required
def alterar_senha(request):
    """View placeholder para Alterar Senha."""
    # Django tem views built-in, mas criamos um placeholder para rota customizada
    context = {'usuario': request.user}
    return render(request, 'perfil/alterar_senha.html', context)

@login_required
def historico_pedidos(request):
    """View para listar o histórico de pedidos do usuário logado."""
    usuario_entity = Usuario(id=request.user.id)
    
    # Use Case para buscar pedidos por usuário
    uc_buscar_pedidos = BuscarPedidosPorUsuario(pedido_repo)
    pedidos = uc_buscar_pedidos.execute(usuario=usuario_entity)
    
    context = {
        'pedidos': pedidos,
    }
    return render(request, 'perfil/historico_pedidos.html', context)


# -- FIM DAS NOVAS VIEWS DE PERFIL --

def lista_joias(request):
    """
    View para a página inicial e listagem de joias (agora buscando todas).
    """
    try:
        joias = joia_repo.buscar_todos() 
    except Exception as e:
        messages.error(request, f"Erro ao carregar o catálogo de joias: {e}")
        joias = []

    context = {
        'joias': joias
    }
    return render(request, 'lista_joias.html', context)


def detalhe_joia(request, joia_id):
    """
    Busca os detalhes da joia.
    """
    # A URL da API deve apontar para o host do servidor Django (localhost:8000)
    api_url = f"http://localhost:8000/api/joias/{joia_id}/"
    
    try:
        # Faz a requisição HTTP para buscar o produto
        response = requests.get(api_url)
        response.raise_for_status() # Levanta um erro se o status for 4xx ou 5xx

        # A resposta é JSON, que é convertida em um dicionário Python
        joia_data = response.json()
        
        carrinho = None
        if request.user.is_authenticated:
            carrinho = carrinho_repo.buscar_por_usuario(Usuario(id=request.user.id))
        
        context = {
            'joia': joia_data, 
            'form': AdicionarItemCarrinhoForm(initial={'joia_id': joia_id}),
            'carrinho': carrinho,
        }
        return render(request, 'detalhe_joia.html', context)
        
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 404:
            raise Http404("Jóia não encontrada.")
        return HttpResponseServerError("Erro de comunicação com o serviço de catálogo.")
    except requests.exceptions.RequestException:
        return HttpResponseServerError("Erro ao conectar com o serviço de API. Verifique se o servidor está ativo.")


@login_required
def adicionar_ao_carrinho(request):
    """
    Adiciona item ao carrinho (requisição AJAX).
    """
    if request.method == 'POST':
        form = AdicionarItemCarrinhoForm(request.POST)

        if form.is_valid():
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
            return JsonResponse({'success': False, 'message': 'Erro de validação.', 'errors': form.errors}, status=400)

    return JsonResponse({'success': False, 'message': 'Método não permitido'}, status=405)


@login_required
def ver_carrinho(request):
    """
    CORREÇÃO: Adicionado 'url_confirmar_pagamento' ao contexto.
    View para a página do carrinho de compras.
    """
    usuario_entity = Usuario(id=request.user.id)
    carrinho = carrinho_repo.buscar_por_usuario(usuario_entity)
    context = {
        'carrinho': carrinho,
        # CORRIGIDO: Passa a URL nomeada para o botão Confirmar Pagamento no template
        'url_confirmar_pagamento': reverse('processar_checkout'), 
    }
    return render(request, 'carrinho.html', context)


# vejoias/presentation/views.py

# ... (restante do código das views processar_checkout, detalhe_pedido, registro, login_usuario, etc., mantido) ...


@login_required
@transaction.atomic
def processar_checkout(request):
    """
    View para exibir o formulário de checkout (GET) e processar o pedido (POST).
    """
    usuario_entity = Usuario(id=request.user.id)
    carrinho = carrinho_repo.buscar_por_usuario(usuario_entity)

    # 1. Checagem de segurança inicial: Carrinho vazio
    if not carrinho.itens:
        messages.error(request, "Seu carrinho está vazio. Adicione itens para finalizar a compra.")
        return redirect('ver_carrinho')

    if request.method == 'POST':
        # Lógica POST: Tenta processar o pedido com dados do formulário completo
        form = CheckoutForm(request.POST) 

        if form.is_valid():
            # Acessamos os dados validados e seguros do formulário
            endereco_entity = form.to_endereco_entity()
            tipo_pagamento = form.cleaned_data['tipo_pagamento']
            numero_do_cliente = form.cleaned_data['telefone_whatsapp']

            # Injeção de Dependência
            criar_pedido_uc = CriarPedido(
                carrinho_repo,
                joia_repo,
                pedido_repo,
                pagamento_gateway,
                whatsapp_notifier,
                email_service, 
            )

            try:
                pedido = criar_pedido_uc.execute(
                    usuario=usuario_entity,
                    tipo_pagamento=tipo_pagamento,
                    endereco=endereco_entity,
                    numero_telefone=numero_do_cliente 
                )
                
                messages.success(request, f"Pedido #{pedido.id} realizado com sucesso! Você receberá a confirmação por WhatsApp.")
                return redirect('detalhe_pedido', pedido_id=pedido.id) 
            
            except (CarrinhoVazioError, EstoqueInsuficienteError, PagamentoFalhouError) as e:
                messages.error(request, f"Erro ao finalizar pedido: {str(e)}")
        
    else:
        form = CheckoutForm()

    context = {
        'form': form,
        'carrinho': carrinho
    }
    return render(request, 'checkout.html', context)

@login_required
def detalhe_pedido(request, pedido_id):
    """
    View para a página de detalhes de um pedido específico.
    """
    usuario_entity = Usuario(id=request.user.id)
    
    # 1. Buscar o pedido pelo ID (assumindo que PedidoRepository tem buscar_por_id)
    pedido = pedido_repo.buscar_por_id(pedido_id)
    
    # 2. Verificar se o pedido existe
    if not pedido:
        raise Http404("Pedido não encontrado.")
    
    # 3. Verificar se o usuário logado é o proprietário do pedido
    if pedido.usuario.id != usuario_entity.id:
        raise PermissionDenied("Você não tem permissão para visualizar este pedido.")

    context = {
        'pedido': pedido
    }
    return render(request, 'detalhe_pedido.html', context)


# ====================================================================
# VIEWS DE AUTENTICAÇÃO
# ====================================================================

def registro(request):
    """
    View para a página de registro de usuário.
    """
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            return redirect('login')
    else:
        form = RegistroForm()
    
    context = {'form': form}
    return render(request, 'registro.html', context)


def login_usuario(request):
    """
    View para a página de login.
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
    """
    logout(request)
    return redirect('lista_joias') # Redireciona para a página inicial após o logout


@login_required
def dashboard_admin(request):
    """
    View para o painel de administração.
    """
    if not request.user.is_staff:
        raise PermissionDenied("Você não tem permissão para acessar esta página.")
    
    return render(request, 'admin/dashboard.html')


@login_required
def gerenciar_produtos(request):
    # ...
    repo = JoiaRepository() 
    joias = repo.buscar_todos() 
    # ...
    context = {'joias': joias}
    return render(request, 'gerenciar_produtos.html', context)


# ====================================================================
# VIEWS PARA GERENCIAR PRODUTOS
# ====================================================================
@login_required
def adicionar_joia(request):
    """
    View para adicionar uma nova joia.
    """
    if not request.user.is_staff:
        raise PermissionDenied("Você não tem permissão para acessar esta página.")
        
    if request.method == 'POST':
        form = JoiaForm(request.POST)
        if form.is_valid():
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
@require_POST 
def excluir_joia(request, joia_id):
    """
    View para excluir uma joia.
    """
    if not request.user.is_staff:
        raise PermissionDenied("Você não tem permissão para acessar esta página.")
        
    try:
        joia_model = JoiaModel.objects.get(id=joia_id)
        joia_model.delete()
        messages.success(request, 'Jóia excluída com sucesso!')
    except JoiaModel.DoesNotExist:
        messages.error(request, 'Jóia não encontrada.')
        
    return redirect('gerenciar_produtos')


class JoiaViewSet(viewsets.ModelViewSet):
    """
    API ViewSet para gerenciar joias.
    """
    queryset = JoiaModel.objects.all()
    serializer_class = JoiaSerializer
    
    def get_permissions(self):
        """
        Define as permissões para cada ação.
        """
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            self.permission_classes = [IsAdminUser]
        else:
            self.permission_classes = []
            
        return [permission() for permission in self.permission_classes]


class CarrinhoAPIView(APIView):
    """
    API View para gerenciar o carrinho do usuário logado.
    """
    permission_classes = [IsAuthenticated] 

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
            numero_do_cliente = serializer.validated_data.get('telefone_whatsapp')

            criar_pedido_uc = CriarPedido(
                carrinho_repo=carrinho_repo,
                joia_repo=joia_repo,
                pedido_repo=pedido_repo,
                pagamento_gateway=pagamento_gateway,
                whatsapp_gateway=whatsapp_notifier,
                email_service=email_service, 
            )

            try:
                pedido = criar_pedido_uc.execute(
                    usuario=Usuario(id=request.user.id),
                    tipo_pagamento=tipo_pagamento,
                    endereco=endereco_entity,
                    numero_telefone=numero_do_cliente,
                )
                return Response({'message': 'Pedido criado com sucesso!', 'pedido_id': pedido.id}, status=status.HTTP_201_CREATED)
            except (CarrinhoVazioError, EstoqueInsuficienteError, PagamentoFalhouError) as e:
                return Response({'message': str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
       
class WebhookMercadoPago(APIView):
    """
    Recebe as notificações (IPN) do Mercado Pago para atualizar o status do pedido.
    """

    def post(self, request):
        data = request.data
        
        resource_id = data.get('resource') or data.get('data', {}).get('id')
        topic = data.get('topic') 
        
        if topic == 'payment' and resource_id:
            
            uc_atualizar_status = AtualizarStatusPedido(
                pedido_repo=pedido_repo, 
                pagamento_gateway=pagamento_gateway,
                whatsapp_gateway=whatsapp_notifier,
                email_service=email_service,

            )
            
            try:
                uc_atualizar_status.execute(resource_id)
            except Exception as e:
                print(f"Erro interno ao processar webhook {resource_id}: {e}")

            return Response(status=status.HTTP_200_OK)
        
        return Response(status=status.HTTP_400_BAD_REQUEST)
    

class ListagemPedidosView(LoginRequiredMixin, ListView):
    # Garante que apenas usuários logados acessem esta página
    login_url = '/login/' 

    # Configurações básicas da lista
    template_name = 'admin/listagem_pedidos.html'
    context_object_name = 'pedidos'
    paginate_by = 20 

    def get_queryset(self):
        uc_listar_pedidos = ListarPedidos(pedido_repo=pedido_repo)
        status_filtro = self.request.GET.get('status')
        queryset = uc_listar_pedidos.execute(status=status_filtro)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_selecionado'] = self.request.GET.get('status', '')
        context['status_choices'] = ["PAGO", "PENDENTE", "CANCELADO", "PROCESSANDO", "ENVIADO"]
        return context
    

class DetalhePedidoAdminView(LoginRequiredMixin, View):
    template_name = 'admin/detalhe_pedido.html'

    def get(self, request, pedido_id):
        uc_detalhes = BuscarPedidoPorId(pedido_repo=pedido_repo)
        pedido = uc_detalhes.execute(pedido_id=pedido_id)
        
        if not pedido:
            raise Http404("Pedido não encontrado.") 

        status_choices = ["PAGO", "PENDENTE", "PROCESSANDO", "ENVIADO", "ENTREGUE", "CANCELADO"]
        
        context = {
            'pedido': pedido,
            'status_choices': status_choices
        }
        return render(request, self.template_name, context)

    def post(self, request, pedido_id):
        novo_status = request.POST.get('status', '').strip()
        
        uc_atualizar_status = AtualizarStatusManual(
            pedido_repo=pedido_repo,
            notificacao_service=notificacao_service 
        )
        
        try:
            uc_atualizar_status.execute(pedido_id=pedido_id, novo_status=novo_status)
            messages.success(request, f"Status do Pedido #{pedido_id} atualizado para {novo_status} com sucesso.")
            
        except PedidoNaoEncontradoError:
            messages.error(request, f"Erro: Pedido #{pedido_id} não foi encontrado.")
            
        except StatusInvalidoError as e:
            messages.error(request, f"Erro de validação: {e}")
            
        except Exception as e:
            messages.error(request, f"Ocorreu uma falha inesperada ao salvar: {e}")
        
        return HttpResponseRedirect(reverse('admin_detalhe_pedido', args=[pedido_id]))
