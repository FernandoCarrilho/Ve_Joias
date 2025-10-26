from django.core.management.base import BaseCommand
from django.utils.text import slugify
from vejoias.infrastructure.models import Categoria, Joia
from decimal import Decimal
import random

class Command(BaseCommand):
    help = 'Carrega dados iniciais para teste do site'

    def handle(self, *args, **kwargs):
        self.stdout.write('Criando dados iniciais...')

        # Categorias
        categorias = [
            {
                'nome': 'Anéis',
                'descricao': 'Anéis elegantes para todas as ocasiões',
                'em_destaque': True,
            },
            {
                'nome': 'Brincos',
                'descricao': 'Brincos delicados e sofisticados',
                'em_destaque': True,
            },
            {
                'nome': 'Colares',
                'descricao': 'Colares que marcam presença',
                'em_destaque': True,
            },
            {
                'nome': 'Pulseiras',
                'descricao': 'Pulseiras para todos os estilos',
                'em_destaque': False,
            },
            {
                'nome': 'Conjuntos',
                'descricao': 'Conjuntos completos para ocasiões especiais',
                'em_destaque': False,
            },
        ]

        for cat_data in categorias:
            categoria, created = Categoria.objects.get_or_create(
                nome=cat_data['nome'],
                defaults={
                    'slug': slugify(cat_data['nome']),
                    'descricao': cat_data['descricao'],
                    'em_destaque': cat_data['em_destaque'],
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Criada categoria "{categoria.nome}"'))

        # Produtos por categoria
        produtos = {
            'Anéis': [
                ('Anel Solitário Ouro 18k', 'Anel solitário em ouro 18k com zircônia', Decimal('599.90'), 10),
                ('Anel Infinito Prata 925', 'Anel modelo infinito em prata 925', Decimal('199.90'), 15),
            ],
            'Brincos': [
                ('Brinco Pérola Cultivada', 'Brinco com pérola cultivada e banho de ouro', Decimal('299.90'), 8),
                ('Brinco Argola Clássica', 'Brinco argola em prata 925', Decimal('159.90'), 12),
            ],
            'Colares': [
                ('Colar Ponto de Luz', 'Colar com pingente de zircônia', Decimal('399.90'), 6),
                ('Gargantilha Delicada', 'Gargantilha em ouro 18k', Decimal('799.90'), 4),
            ],
            'Pulseiras': [
                ('Pulseira Veneziana', 'Pulseira estilo veneziana em prata 925', Decimal('249.90'), 10),
                ('Pulseira Rígida', 'Pulseira rígida em ouro 18k', Decimal('899.90'), 5),
            ],
            'Conjuntos': [
                ('Conjunto Elegance', 'Conjunto com colar e brincos', Decimal('599.90'), 3),
                ('Conjunto Glamour', 'Conjunto completo com anel, colar e brincos', Decimal('899.90'), 2),
            ],
        }

        for cat_nome, prods in produtos.items():
            try:
                categoria = Categoria.objects.get(nome=cat_nome)
                for nome, desc, preco, estoque in prods:
                    joia, created = Joia.objects.get_or_create(
                        nome=nome,
                        defaults={
                            'slug': slugify(nome),
                            'descricao': desc,
                            'preco': preco,
                            'estoque': estoque,
                            'categoria': categoria,
                            'em_destaque': random.choice([True, False]),
                            'desconto': random.choice([0, 10, 15, 20]) if random.random() > 0.7 else 0,
                        }
                    )
                    if created:
                        self.stdout.write(self.style.SUCCESS(f'Criado produto "{joia.nome}"'))
            except Categoria.DoesNotExist:
                self.stdout.write(self.style.ERROR(f'Categoria "{cat_nome}" não encontrada'))

        self.stdout.write(self.style.SUCCESS('Dados iniciais carregados com sucesso!'))