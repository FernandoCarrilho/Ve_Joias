from django.views import View
from django.views.generic import ListView, DetailView, View as BaseView
from django.urls import reverse
from django.shortcuts import render, redirect, HttpResponseRedirect
from django.http import JsonResponse, Http404, HttpResponseServerError
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.contrib.auth import authenticate, login, logout
from django.db import transaction
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
import requests

from vejoias.infrastructure.repositories import (
    JoiaRepository,
    CarrinhoRepository,
    PedidoRepository,
)
from vejoias.infrastructure.gateways import MercadoPagoGateway, EvolutionAPIGateway, EmailServiceGateway
from vejoias.core.use_cases import GerenciarCarrinhoUseCase, ListarPedidosDoUsuarioUseCase, CriarPedidoUseCase
from vejoias.core.exceptions import (
    EstoqueInsuficienteError,
    ItemNaoEncontradoError,
    CarrinhoVazioError,
    PagamentoFalhouError,
)
from vejoias.core.entities import Usuario

from vejoias.catalog.models import Joia as JoiaModel
from .serializers import JoiaSerializer, CarrinhoSerializer, CheckoutSerializer
from .forms import AdicionarItemCarrinhoForm, CheckoutForm, RegistroForm, LoginForm
from vejoias.core.use_cases import GerenciarPedidosAdminUseCase


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


class UsuarioView(LoginRequiredMixin, View):
    """View para a página de perfil do usuário."""
    template_name = 'user/perfil.html'

    def get(self, request):
        context = {
            'usuario': request.user,
        }
        return render(request, self.template_name, context)


class EditarPerfilView(LoginRequiredMixin, View):
    """View placeholder para Editar Informações de Perfil."""
    template_name = 'user/editar_perfil.html'

    def get(self, request):
        context = {'usuario': request.user}
        return render(request, self.template_name, context)


class AlterarSenhaView(LoginRequiredMixin, View):
    """View placeholder para Alterar Senha."""
    template_name = 'user/alterar_senha.html'

    def get(self, request):
        context = {'usuario': request.user}
        return render(request, self.template_name, context)


class HistoricoPedidosView(LoginRequiredMixin, View):
    """View para listar o histórico de pedidos do usuário logado."""
    template_name = 'perfil/historico_pedidos.html'

    def get(self, request):
        usuario_entity = Usuario(id=request.user.id)
        
        # Use Case para buscar pedidos por usuário
        uc_listar_pedidos = ListarPedidosDoUsuarioUseCase(pedido_repo)
        pedidos = uc_listar_pedidos.executar(usuario_id=usuario_entity.id)
        
        context = {
            'pedidos': pedidos,
        }
        return render(request, self.template_name, context)


# -- FIM DAS NOVAS VIEWS DE PERFIL --

class HomeView(View):
    """
    View para a página inicial da loja.
    """
    template_name = 'home.html'

    def get(self, request):
        try:
            # Busca joias em destaque
            produtos_destaque = joia_repo.buscar_por_criterios(em_destaque=True)[:8]
            if not produtos_destaque:  # Se não houver joias em destaque, pega as mais recentes
                produtos_destaque = joia_repo.buscar_todos()[:8]
                
            # Busca categorias em destaque
            categorias = joia_repo.buscar_categorias_destaque()[:3]
            
        except Exception as e:
            messages.error(request, f"Erro ao carregar os dados: {e}")
            produtos_destaque = []
            categorias = []

        context = {
            'produtos_destaque': produtos_destaque,
            'categorias_destaque': categorias,
        }
        return render(request, self.template_name, context)


class ListaJoiasView(View):
    """
    View para a página de listagem de joias, incluindo filtros, busca e ordenação 
    baseados nos parâmetros de query string (request.GET), conforme o template.
    """
    # A CORREÇÃO JÁ ESTAVA AQUI: template_name = 'catalog/lista_joias.html'
    template_name = 'catalog/lista_joias.html'

    def get(self, request):
        
        # 1. Captura dos parâmetros de filtro e ordenação do request
        busca_termo = request.GET.get('busca', '').strip()
        # O template usa 'categoria' como ID
        categoria_selecionada_id = request.GET.get('categoria', '') 
        ordem_selecionada = request.GET.get('ordem', 'recente') # Default: mais recente

        # 2. Definição do critério de ordenação para o repositório
        # Mapeia a string do template para o formato de ordenação do Django/Repositório
        ordem_map = {
            'recente': '-data_criacao', 
            'preco_asc': 'preco',
            'preco_desc': '-preco',
        }
        ordem_repo = ordem_map.get(ordem_selecionada, '-data_criacao')

        joias = []
        categorias = []
        nome_categoria_selecionada = ''
        
        try:
            # Busca todas as categorias para popular o filtro <select>
            # ATENÇÃO: É necessário que o JoiaRepository implemente 'buscar_todas_categorias()'.
            categorias = joia_repo.buscar_todas_categorias() 
            
            # Joias: Aplica filtros, busca e ordenação
            joias = joia_repo.buscar_por_criterios(
                termo_busca=busca_termo,
                categoria_id=categoria_selecionada_id,
                ordem_por=ordem_repo,
                em_estoque=True # Critério padrão
            )
            
            # Nome amigável da categoria selecionada (para a mensagem de resultado)
            if categoria_selecionada_id:
                try:
                    # Encontra o nome da categoria usando o ID
                    # Assume-se que 'cat' é uma entidade/objeto com atributos 'id' e 'nome'
                    cat_obj = next(cat for cat in categorias if str(cat.id) == categoria_selecionada_id)
                    nome_categoria_selecionada = cat_obj.nome
                except StopIteration:
                    # Se o ID for inválido ou não encontrado, limpa o filtro de categoria
                    categoria_selecionada_id = '' 
                    
        except AttributeError:
             messages.error(request, "Erro: O JoiaRepository precisa do método 'buscar_todas_categorias()' para o filtro de categorias funcionar.")
             
        except Exception as e:
            messages.error(request, f"Erro ao carregar o catálogo de joias: {e}")

        # 3. Construção do Contexto
        context = {
            'joias': joias,
            'categorias': categorias, # Lista completa para o <select>
            'busca_termo': busca_termo,
            'categoria_selecionada': categoria_selecionada_id, # ID da categoria selecionada
            'ordem_selecionada': ordem_selecionada,
            'nome_categoria_selecionada': nome_categoria_selecionada,
            'is_paginated': False # Placeholder para futura implementação de paginação
        }
        return render(request, self.template_name, context)


class ListaJoiasPorCategoriaView(View):
    """
    View para a página de listagem de joias por categoria usando SLUG. 
    (Esta view pode ser removida se o catálogo usar apenas ListaJoiasView, mas foi mantida por compatibilidade)
    """
    template_name = 'catalog/lista_joias.html'

    def get(self, request, slug):
        try:
            # Busca apenas por slug. Não implementa os filtros completos da ListaJoiasView.
            joias = joia_repo.buscar_por_criterios(em_estoque=True, categoria_slug=slug)
            
            # AVISO: Para evitar que o template falhe na renderização dos filtros, 
            # as variáveis 'categorias', 'busca_termo', 'categoria_selecionada', 
            # etc. devem ser fornecidas, mesmo que vazias.
            categorias = joia_repo.buscar_todas_categorias()
            
            # Tenta encontrar o ID da categoria pelo slug para preencher o contexto de filtro
            categoria_selecionada_id = ''
            nome_categoria_selecionada = ''
            try:
                cat_obj = next(cat for cat in categorias if cat.slug == slug)
                categoria_selecionada_id = str(cat_obj.id)
                nome_categoria_selecionada = cat_obj.nome
            except:
                pass # Ignora se não encontrar a categoria pelo slug
            
        except Exception as e:
            messages.error(request, f"Erro ao carregar o catálogo de joias: {e}")
            joias = []
            categorias = []

        context = {
            'joias': joias,
            'categorias': categorias,
            'categoria_selecionada': categoria_selecionada_id,
            'nome_categoria_selecionada': nome_categoria_selecionada,
            'busca_termo': '',
            'ordem_selecionada': 'recente',
        }
        return render(request, self.template_name, context)


class DetalheJoiaView(View):
    """
    View para a página de detalhes de uma joia.
    """
    # CORREÇÃO APLICADA: Incluindo o prefixo 'catalog/'
    template_name = 'catalog/detalhe_joia.html'

    def get(self, request, pk):
        api_url = f"http://localhost:8000/api/joias/{pk}/"

        try:
            response = requests.get(api_url)
            response.raise_for_status()

            joia_data = response.json()

            carrinho = None
            if request.user.is_authenticated:
                carrinho = carrinho_repo.buscar_por_usuario(Usuario(id=request.user.id))

            context = {
                'joia': joia_data,
                'form': AdicionarItemCarrinhoForm(initial={'joia_id': pk}),
                'carrinho': carrinho,
            }
            return render(request, self.template_name, context)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                raise Http404("Jóia não encontrada.")
            return HttpResponseServerError("Erro de comunicação com o serviço de catálogo.")
        except requests.exceptions.RequestException:
            return HttpResponseServerError("Erro ao conectar com o serviço de API. Verifique se o servidor está ativo.")


class CarrinhoView(LoginRequiredMixin, View):
    """
    View para a página do carrinho de compras.
    """
    template_name = 'cart/carrinho.html'

    def get(self, request):
        usuario_entity = Usuario(id=request.user.id)
        gerenciar_carrinho_uc = GerenciarCarrinhoUseCase(carrinho_repo, joia_repo)
        carrinho = gerenciar_carrinho_uc.obter_carrinho(usuario=usuario_entity)
        context = {
            'carrinho': carrinho,
            'url_confirmar_pagamento': reverse('processar_checkout'),
        }
        return render(request, self.template_name, context)


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
            gerenciar_carrinho_uc = GerenciarCarrinhoUseCase(carrinho_repo, joia_repo)

            try:
                carrinho = gerenciar_carrinho_uc.obter_carrinho(usuario=usuario_entity)
                carrinho_atualizado = gerenciar_carrinho_uc.adicionar_item(
                    carrinho=carrinho,
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
def remover_do_carrinho(request, joia_id):
    """
    Remove item do carrinho (requisição AJAX).
    """
    if request.method == 'POST':
        usuario_entity = Usuario(id=request.user.id)
        gerenciar_carrinho_uc = GerenciarCarrinhoUseCase(carrinho_repo, joia_repo)

        try:
            carrinho = gerenciar_carrinho_uc.obter_carrinho(usuario=usuario_entity)
            carrinho_atualizado = gerenciar_carrinho_uc.remover_item(
                carrinho=carrinho,
                joia_id=joia_id
            )
            return JsonResponse({
                'success': True,
                'message': 'Item removido do carrinho!',
                'total_itens': sum(item.quantidade for item in carrinho_atualizado.itens)
            })
        except ItemNaoEncontradoError as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

    return JsonResponse({'success': False, 'message': 'Método não permitido'}, status=405)


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
            criar_pedido_uc = CriarPedidoUseCase(
                carrinho_repo,
                pedido_repo,
                joia_repo,
                pagamento_gateway,
                email_service, 
                whatsapp_notifier,
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
    return render(request, 'checkout/checkout.html', context)

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
    # CORREÇÃO APLICADA: Incluindo o prefixo 'pedido/'
    return render(request, 'pedido/detalhe_pedido.html', context)


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
    return render(request, 'auth/registro.html', context)


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
    return render(request, 'auth/login.html', context)


@login_required
def logout_usuario(request):
    """
    View para a saída do usuário.
    """
    logout(request)
    return redirect('lista_joias') # Redireciona para a página inicial após o logout


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


# ====================================================================
# VIEWS PARA CHECKOUT
# ====================================================================

class ProcessarCheckoutView(LoginRequiredMixin, View):
    """
    View para processar o checkout.
    """
    template_name = 'checkout/checkout.html'

    def get(self, request):
        usuario_entity = Usuario(id=request.user.id)
        carrinho = carrinho_repo.buscar_por_usuario(usuario_entity)

        if not carrinho.itens:
            messages.error(request, "Seu carrinho está vazio. Adicione itens para finalizar a compra.")
            return redirect('ver_carrinho')

        form = CheckoutForm()
        context = {
            'form': form,
            'carrinho': carrinho
        }
        return render(request, self.template_name, context)

    def post(self, request):
        usuario_entity = Usuario(id=request.user.id)
        carrinho = carrinho_repo.buscar_por_usuario(usuario_entity)

        if not carrinho.itens:
            messages.error(request, "Seu carrinho está vazio. Adicione itens para finalizar a compra.")
            return redirect('ver_carrinho')

        form = CheckoutForm(request.POST)
        if form.is_valid():
            endereco_entity = form.to_endereco_entity()
            tipo_pagamento = form.cleaned_data['tipo_pagamento']
            numero_do_cliente = form.cleaned_data['telefone_whatsapp']

            criar_pedido_uc = CriarPedidoUseCase(
                carrinho_repo,
                pedido_repo,
                joia_repo,
                pagamento_gateway,
                email_service,
                whatsapp_notifier,
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

        context = {
            'form': form,
            'carrinho': carrinho
        }
        return render(request, self.template_name, context)


class DetalhePedidoView(LoginRequiredMixin, DetailView):
    """
    View para exibir os detalhes de um pedido.
    """
    # CORREÇÃO APLICADA: Incluindo o prefixo 'pedido/'
    template_name = 'pedido/detalhe_pedido.html'
    context_object_name = 'pedido'

    def get_object(self, queryset=None):
        pedido_id = self.kwargs.get('pk')
        pedido = pedido_repo.buscar_por_id(pedido_id)
        
        if not pedido:
            raise Http404("Pedido não encontrado.")
        
        if pedido.usuario.id != self.request.user.id:
            raise PermissionDenied("Você não tem permissão para visualizar este pedido.")
        
        return pedido


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

        gerenciar_carrinho_uc = GerenciarCarrinhoUseCase(carrinho_repo, joia_repo)
        
        try:
            carrinho = gerenciar_carrinho_uc.obter_carrinho(usuario=Usuario(id=request.user.id))
            carrinho_atualizado = gerenciar_carrinho_uc.adicionar_item(
                carrinho=carrinho,
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
        gerenciar_carrinho_uc = GerenciarCarrinhoUseCase(carrinho_repo, joia_repo)

        try:
            carrinho = gerenciar_carrinho_uc.obter_carrinho(usuario=Usuario(id=request.user.id))
            carrinho_atualizado = gerenciar_carrinho_uc.remover_item(
                carrinho=carrinho,
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

            criar_pedido_uc = CriarPedidoUseCase(
                carrinho_repo=carrinho_repo,
                pedido_repo=pedido_repo,
                joia_repo=joia_repo,
                pagamento_gateway=pagamento_gateway,
                email_service=email_service,
                whatsapp_gateway=whatsapp_notifier,
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
            
            gerenciar_pedidos_uc = GerenciarPedidosAdminUseCase(
                pedido_repo=pedido_repo,
                email_service=email_service,
                whatsapp_gateway=whatsapp_notifier,
            )
            
            try:
                gerenciar_pedidos_uc.atualizar_status_manual(pedido_id=resource_id, novo_status="PROCESSANDO")
            except Exception as e:
                print(f"Erro interno ao processar webhook {resource_id}: {e}")

            return Response(status=status.HTTP_200_OK)
        
        return Response(status=status.HTTP_400_BAD_REQUEST)
