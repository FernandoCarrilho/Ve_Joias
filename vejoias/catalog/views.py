# vejoias/catalog/views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.views import View
from django.contrib import messages
from django.urls import reverse_lazy
from django.contrib.auth.mixins import UserPassesTestMixin

# Imports do Django
from django.views.generic import ListView, CreateView, UpdateView, DeleteView
from django.core.paginator import Paginator
from django.db.models import Q # Para busca

# Imports Locais
from .forms import JoiaAdminForm, CategoriaAdminForm
from .models import Joia, Categoria # Usamos os Models para as Views genéricas de admin
from vejoias.core.entities import Joia as JoiaEntity, Categoria as CategoriaEntity, Usuario
from vejoias.core.exceptions import JoiaNaoEncontradaError, EstoqueInsuficienteError
from vejoias.core.dependency_injection import (
    get_criar_joia_use_case, 
    get_listar_joias_use_case,
    get_atualizar_joia_use_case,
    get_deletar_joia_use_case
)
from vejoias.infrastructure.repositories import map_user_model_to_entity


# ====================================================================
# Mixin para garantir que apenas administradores acessem
# ====================================================================

class AdminRequiredMixin(UserPassesTestMixin):
    """Garante que apenas usuários staff (administradores) possam acessar as views."""
    def test_func(self):
        return self.request.user.is_authenticated and self.request.user.is_staff

    def handle_no_permission(self):
        messages.error(self.request, "Você não tem permissão para acessar esta área.")
        return redirect('home')


# ====================================================================
# VIEWS DO CATÁLOGO (PÚBLICO)
# ====================================================================

class CatalogoView(ListView):
    """Exibe o catálogo principal de joias com filtros."""
    model = Joia
    template_name = 'catalog/catalogo.html'
    context_object_name = 'joias'
    paginate_by = 12

    def get_queryset(self):
        """Usa o Use Case para listar as joias."""
        listar_uc = get_listar_joias_use_case()
        
        busca = self.request.GET.get('busca', None)
        categoria_slug = self.request.GET.get('categoria', None)
        
        # O Use Case retorna Entidades, não Models.
        joias_entities = listar_uc.execute(
            em_estoque=True, # Apenas joias em estoque para o público
            busca=busca,
            categoria_slug=categoria_slug
        )
        
        # Para a View Genérica funcionar com paginação, 
        # precisaríamos de um adaptador mais complexo ou usar View base.
        # Por simplicidade e performance, vamos retornar a QuerySet filtrada
        # e fazer o mapeamento dos dados na template (ou usar um adapter View)
        
        # ADAPTADOR SIMPLES: Filtrar o QuerySet do Django para a ListView
        qs = Joia.objects.filter(estoque__gt=0, is_destaque=True if categoria_slug == 'destaques' else False).select_related('categoria')
        
        if busca:
            qs = qs.filter(Q(nome__icontains=busca) | Q(descricao__icontains=busca))
        
        if categoria_slug and categoria_slug != 'destaques':
            qs = qs.filter(categoria__slug=categoria_slug)
        
        return qs.order_by('-data_criacao')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Adiciona todas as categorias para o menu de filtros
        context['categorias'] = Categoria.objects.all().order_by('nome')
        context['busca'] = self.request.GET.get('busca', '')
        context['categoria_selecionada'] = self.request.GET.get('categoria', '')
        return context


class DetalheJoiaView(View):
    """Exibe os detalhes de uma joia específica."""
    def get(self, request, pk):
        listar_uc = get_listar_joias_use_case()
        
        try:
            joia_entity = listar_uc.buscar_por_id(pk)
            if not joia_entity:
                raise JoiaNaoEncontradaError(f"Joia ID {pk} não encontrada.")

            context = {
                'joia': joia_entity,
            }
            return render(request, 'catalog/detalhe_joia.html', context)
            
        except JoiaNaoEncontradaError:
            messages.error(request, "A jóia solicitada não foi encontrada.")
            return redirect('catalogo')


# ====================================================================
# VIEWS DO PAINEL DE ADMINISTRAÇÃO (CRUD)
# ====================================================================

class AdminJoiaListView(AdminRequiredMixin, ListView):
    """Lista todas as joias (ativas e inativas) para o administrador."""
    model = Joia
    template_name = 'admin/joia_list.html'
    context_object_name = 'joias'
    paginate_by = 20
    
    def get_queryset(self):
        """Retorna todas as joias para o Admin, com filtros opcionais."""
        qs = Joia.objects.all().select_related('categoria').order_by('-data_criacao')
        
        busca = self.request.GET.get('busca')
        categoria_id = self.request.GET.get('categoria')
        
        if busca:
            qs = qs.filter(Q(nome__icontains=busca) | Q(descricao__icontains=busca))
        
        if categoria_id:
            qs = qs.filter(categoria_id=categoria_id)
            
        return qs
        
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categorias'] = Categoria.objects.all().order_by('nome')
        context['busca'] = self.request.GET.get('busca', '')
        context['categoria_selecionada'] = self.request.GET.get('categoria', '')
        return context


class AdminJoiaCreateUpdateView(AdminRequiredMixin, View):
    """Criação e Edição de Joia, interagindo com o Use Case."""
    template_name = 'admin/joia_form.html'

    def get_joia_entity_from_form(self, form) -> JoiaEntity:
        """Converte os dados limpos do form em uma Joia Entity."""
        data = form.cleaned_data
        
        # Categoria Entity (pode ser None)
        categoria_model = data.get('categoria')
        categoria_entity = None
        if categoria_model:
            categoria_entity = CategoriaEntity(
                id=categoria_model.id, 
                nome=categoria_model.nome,
                slug=categoria_model.slug,
                descricao=categoria_model.descricao
            )
            
        return JoiaEntity(
            id=getattr(form.instance, 'pk', None), # Pk existe na edição
            nome=data['nome'],
            descricao=data['descricao'],
            preco=float(data['preco']),
            estoque=data['estoque'],
            categoria=categoria_entity,
            material=data['material'],
            peso_gramas=float(data.get('peso_gramas') or 0.0),
            dimensoes=data.get('dimensoes'),
            imagem_url=data.get('imagem_url'),
            is_destaque=data.get('is_destaque', False)
        )


    def get(self, request, pk=None):
        if pk:
            # Edição
            joia_model = get_object_or_404(Joia, pk=pk)
            form = JoiaAdminForm(instance=joia_model)
            titulo = "Editar Jóia"
        else:
            # Criação
            form = JoiaAdminForm()
            titulo = "Criar Nova Jóia"
            
        return render(request, self.template_name, {'form': form, 'titulo': titulo})

    def post(self, request, pk=None):
        if pk:
            joia_model = get_object_or_404(Joia, pk=pk)
            form = JoiaAdminForm(request.POST, instance=joia_model)
            uc = get_atualizar_joia_use_case()
            titulo = "Editar Jóia"
            success_message = "Jóia atualizada com sucesso!"
        else:
            form = JoiaAdminForm(request.POST)
            uc = get_criar_joia_use_case()
            titulo = "Criar Nova Jóia"
            success_message = "Jóia criada com sucesso!"

        if form.is_valid():
            try:
                joia_entity = self.get_joia_entity_from_form(form)
                uc.execute(joia_entity)
                messages.success(request, success_message)
                return redirect('admin_joia_list')
            except Exception as e:
                # Captura exceções do Use Case (ex: validação de estoque se reescrita)
                messages.error(request, f"Erro ao salvar a jóia: {e}")
                
        return render(request, self.template_name, {'form': form, 'titulo': titulo})


class AdminJoiaDeleteView(AdminRequiredMixin, View):
    """Deleta uma joia usando o Use Case."""
    
    def post(self, request, pk):
        deletar_uc = get_deletar_joia_use_case()
        try:
            deletar_uc.execute(pk)
            messages.success(request, "Jóia deletada com sucesso.")
        except JoiaNaoEncontradaError:
            messages.error(request, "Erro: Jóia não encontrada para deletar.")
        except Exception as e:
            messages.error(request, f"Erro ao deletar: {e}")
            
        return redirect('admin_joia_list')


# ====================================================================
# VIEWS DE CATEGORIAS (ADMIN)
# Usando Views Genéricas do Django para CRUD simples de Modelo
# ====================================================================

class AdminCategoriaListView(AdminRequiredMixin, ListView):
    """Lista todas as categorias para o administrador."""
    model = Categoria
    template_name = 'admin/categoria_list.html'
    context_object_name = 'categorias'
    paginate_by = 10


class AdminCategoriaCreateView(AdminRequiredMixin, CreateView):
    """Cria uma nova categoria."""
    model = Categoria
    form_class = CategoriaAdminForm
    template_name = 'admin/categoria_form.html'
    success_url = reverse_lazy('admin_categoria_list')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = "Criar Nova Categoria"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Categoria criada com sucesso.")
        return super().form_valid(form)


class AdminCategoriaUpdateView(AdminRequiredMixin, UpdateView):
    """Edita uma categoria existente."""
    model = Categoria
    form_class = CategoriaAdminForm
    template_name = 'admin/categoria_form.html'
    success_url = reverse_lazy('admin_categoria_list')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['titulo'] = f"Editar Categoria: {self.object.nome}"
        return context

    def form_valid(self, form):
        messages.success(self.request, "Categoria atualizada com sucesso.")
        return super().form_valid(form)


class AdminCategoriaDeleteView(AdminRequiredMixin, DeleteView):
    """Deleta uma categoria (com confirmação)."""
    model = Categoria
    template_name = 'admin/categoria_confirm_delete.html'
    success_url = reverse_lazy('admin_categoria_list')

    def form_valid(self, form):
        messages.success(self.request, f"Categoria '{self.object.nome}' deletada com sucesso.")
        return super().form_valid(form)
