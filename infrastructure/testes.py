from django.test import TestCase
from django.core.exceptions import ObjectDoesNotExist

# Importamos as classes que queremos testar
from infrastructure.models import Joia as JoiaModel
from infrastructure.repositories import JoiaRepository
from core.entities import Joia as JoiaEntity
from core.exceptions import ItemNaoEncontradoError

# A classe de teste herda do TestCase do Django, que prepara o banco de dados de teste
class JoiaRepositoryTestCase(TestCase):
    
    def setUp(self):
        """
        Configura o ambiente para cada teste, criando uma instância do repositório
        e um objeto Joia real no banco de dados.
        """
        self.repository = JoiaRepository()
        self.joia_model = JoiaModel.objects.create(
            id='joia-teste-1',
            nome='Anel de Diamante',
            descricao='Um belo anel de diamante.',
            preco=5000.00,
            estoque=10,
            categoria='OURO',
            subcategoria='ANEL'
        )

    def test_buscar_por_id_com_sucesso(self):
        """
        Cenário: Verificar se o repositório consegue encontrar uma joia existente.
        """
        # ACT: Chamamos o método para buscar a joia
        joia_encontrada = self.repository.buscar_por_id(self.joia_model.id)
        
        # ASSERT: Verificamos se o resultado é uma entidade Joia e se os dados estão corretos
        self.assertIsInstance(joia_encontrada, JoiaEntity)
        self.assertEqual(joia_encontrada.id, self.joia_model.id)
        self.assertEqual(joia_encontrada.nome, self.joia_model.nome)

    def test_buscar_por_id_nao_encontrado(self):
        """
        Cenário: Verificar se o repositório levanta a exceção correta
        quando a joia não é encontrada.
        """
        # ACT e ASSERT: Verificamos se a exceção é levantada
        with self.assertRaises(ItemNaoEncontradoError):
            self.repository.buscar_por_id('id-nao-existente')

    def test_buscar_por_categoria_com_sucesso(self):
        """
        Cenário: Verificar se o repositório consegue encontrar joias por categoria.
        """
        # ACT
        joias_encontradas = self.repository.buscar_por_categoria('OURO')
        
        # ASSERT
        self.assertEqual(len(joias_encontradas), 1)
        self.assertEqual(joias_encontradas[0].id, self.joia_model.id)
