# vejoias/presentation/views_admin.py
"""
Views para o painel de administração.
"""

from django.views.generic import ListView, DetailView, View
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import Http404

from django.views.generic import ListView, DetailView, View, CreateView, UpdateView, DeleteView, TemplateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import Http404
from django.urls import reverse_lazy

from vejoias.core.use_cases import GerenciarPedidosAdminUseCase
from vejoias.core.exceptions import PedidoNaoEncontradoError, StatusInvalidoError
from vejoias.infrastructure.instances import pedido_repo, joia_repo, pagamento_gateway
from vejoias.infrastructure.email_service import EmailService
from vejoias.infrastructure.gateways import WhatsAppGatewayMock

email_service = EmailService()
whatsapp_notifier = WhatsAppGatewayMock()
from vejoias.core.use_cases import GerenciarPedidosAdminUseCase
from vejoias.core.exceptions import PedidoNaoEncontradoError, StatusInvalidoError
from vejoias.catalog.models import Joia
from .forms import JoiaForm

User = get_user_model()

# ====================================================================
# DASHBOARD
# ====================================================================

class DashboardAdminView(LoginRequiredMixin, TemplateView):
    """
    View para o dashboard principal do painel administrativo.
    """
    template_name = 'admin/dashboard.html'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Você não tem permissão para acessar esta página.")
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['pedidos_recentes'] = pedido_repo.listar_recentes(limite=5)
        context['total_pedidos'] = pedido_repo.contar_total()
        context['total_joias'] = joia_repo.contar_total()
        context['total_usuarios'] = User.objects.count()
        return context


# ====================================================================
# GERENCIAMENTO DE PEDIDOS
# ====================================================================

class GerenciarPedidosView(LoginRequiredMixin, ListView):
    """
    View para listagem e gerenciamento de pedidos no painel admin.
    """
    template_name = 'admin/orders_list.html'
    context_object_name = 'pedidos'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Você não tem permissão para acessar esta página.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        gerenciar_pedidos_uc = GerenciarPedidosAdminUseCase(
            pedido_repo=pedido_repo,
            email_service=email_service,
            whatsapp_gateway=whatsapp_notifier,
        )
        status_filtro = self.request.GET.get('status')
        return gerenciar_pedidos_uc.listar_todos(status=status_filtro)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = ["PAGO", "PENDENTE", "CANCELADO", "PROCESSANDO", "ENVIADO"]
        context['status_selecionado'] = self.request.GET.get('status', '')
        return context


class AtualizarStatusPedidoView(LoginRequiredMixin, View):
    """
    View para atualizar o status de um pedido.
    """
    def post(self, request, pk):
        if not request.user.is_staff:
            raise PermissionDenied("Você não tem permissão para acessar esta página.")
            
        novo_status = request.POST.get('status', '').strip()
        if not novo_status:
            messages.error(request, "Status inválido.")
            return redirect('admin_detalhe_pedido', pk=pk)
        
        gerenciar_pedidos_uc = GerenciarPedidosAdminUseCase(
            pedido_repo=pedido_repo,
            email_service=email_service,
            whatsapp_gateway=whatsapp_notifier,
        )
        
        try:
            gerenciar_pedidos_uc.atualizar_status_manual(pedido_id=pk, novo_status=novo_status)
            messages.success(request, f"Status do Pedido #{pk} atualizado para {novo_status} com sucesso.")
            
        except (PedidoNaoEncontradoError, StatusInvalidoError) as e:
            messages.error(request, f"Erro ao atualizar status: {str(e)}")
        
        return redirect('admin_detalhe_pedido', pk=pk)


class DetalhePedidoAdminView(LoginRequiredMixin, DetailView):
    """
    View para exibir os detalhes de um pedido no painel admin.
    """
    template_name = 'admin/order_detail.html'
    context_object_name = 'pedido'

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Você não tem permissão para acessar esta página.")
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        pedido_id = self.kwargs.get('pk')
        pedido = pedido_repo.buscar_por_id(pedido_id)
        
        if not pedido:
            raise Http404("Pedido não encontrado.")
        
        return pedido

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['status_choices'] = ["PAGO", "PENDENTE", "CANCELADO", "PROCESSANDO", "ENVIADO"]
        return context


# ====================================================================
# GERENCIAMENTO DE JOIAS
# ====================================================================

class GerenciarJoiasView(LoginRequiredMixin, ListView):
    """
    View para listagem e gerenciamento de joias.
    """
    template_name = 'admin/products_list.html'
    context_object_name = 'joias'
    paginate_by = 20

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Você não tem permissão para acessar esta página.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return joia_repo.listar_todas()


class AdicionarJoiaView(LoginRequiredMixin, CreateView):
    """
    View para adicionar uma nova joia.
    """
    model = Joia
    form_class = JoiaForm
    template_name = 'admin/product_form.html'
    success_url = reverse_lazy('gerenciar_joias')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Você não tem permissão para acessar esta página.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Joia adicionada com sucesso!')
        return response


class EditarJoiaView(LoginRequiredMixin, UpdateView):
    """
    View para editar uma joia existente.
    """
    model = Joia
    form_class = JoiaForm
    template_name = 'admin/product_form.html'
    success_url = reverse_lazy('gerenciar_joias')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Você não tem permissão para acessar esta página.")
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, 'Joia atualizada com sucesso!')
        return response


class DeletarJoiaView(LoginRequiredMixin, DeleteView):
    """
    View para excluir uma joia.
    """
    model = Joia
    template_name = 'admin/product_delete_confirm.html'
    success_url = reverse_lazy('gerenciar_joias')

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Você não tem permissão para acessar esta página.")
        return super().dispatch(request, *args, **kwargs)

    def delete(self, request, *args, **kwargs):
        response = super().delete(request, *args, **kwargs)
        messages.success(request, 'Joia excluída com sucesso!')
        return response


# ====================================================================
# GERENCIAMENTO DE USUÁRIOS
# ====================================================================

class GerenciarUsuariosView(LoginRequiredMixin, ListView):
    """
    View para listagem e gerenciamento de usuários.
    """
    template_name = 'admin/users_list.html'
    context_object_name = 'usuarios'
    paginate_by = 20
    
    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_staff:
            raise PermissionDenied("Você não tem permissão para acessar esta página.")
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        return User.objects.all().order_by('username')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Adiciona estatísticas de usuários
        context['total_usuarios'] = User.objects.count()
        context['usuarios_ativos'] = User.objects.filter(is_active=True).count()
        context['usuarios_staff'] = User.objects.filter(is_staff=True).count()
        return context