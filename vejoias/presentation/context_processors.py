"""
Context processors para a aplicação presentation.
"""

def carrinho_context(request):
    """
    Adiciona informações do carrinho ao contexto global dos templates.
    """
    try:
        from vejoias.infrastructure.models import Carrinho

        # Tenta obter o carrinho do usuário logado
        if request.user.is_authenticated:
            carrinho, _ = Carrinho.objects.get_or_create(usuario=request.user)
            sessao_key = None
        else:
            # Para usuários anônimos, usa a sessão
            sessao_key = request.session.session_key
            if not sessao_key:
                request.session.save()
                sessao_key = request.session.session_key
            
            carrinho, _ = Carrinho.objects.get_or_create(sessao_key=sessao_key)

        return {
            'carrinho': carrinho,
            'quantidade_itens': carrinho.itens.count(),
            'total_carrinho': carrinho.total_carrinho
        }

    except Exception as e:
        # Em caso de erro, retorna um dicionário vazio para não quebrar o template
        print(f"Erro ao processar carrinho_context: {e}")
        return {}