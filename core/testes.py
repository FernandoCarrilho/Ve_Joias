# vejoias/core/tests.py

import unittest
from unittest.mock import Mock

# Importamos as classes que queremos testar
from core.use_cases import AdicionarItemAoCarrinho, CriarPedido, RemoverItemDoCarrinho
from core.entities import Joia, Usuario, Carrinho, ItemCarrinho, Pedido, Endereco
from core.exceptions import EstoqueInsuficienteError, CarrinhoVazioError, PagamentoFalhouError, ItemNaoEncontradoError

# A classe de teste herda de unittest.TestCase
class TestAdicionarItemAoCarrinho(unittest.TestCase):
    
    def setUp(self):
        """
        Método chamado antes de cada teste.
        Ele prepara o ambiente com objetos "Mock" para simular
        as dependências externas (banco de dados, por exemplo).
        """
        self.carrinho_repo_mock = Mock()
        self.joia_repo_mock = Mock()

        # Instância do nosso Use Case que será testado
        self.use_case = AdicionarItemAoCarrinho(
            carrinho_repo=self.carrinho_repo_mock,
            joia_repo=self.joia_repo_mock
        )
        
        # Criamos um objeto Joia simulado
        self.joia_mock = Joia(
            id='joia-123',
            nome='Anel de Ouro',
            preco=1500.00,
            estoque=10
        )
        
        # Criamos um objeto Usuario simulado
        self.usuario_mock = Usuario(id=1, email='teste@example.com')
        
    def test_adicionar_item_com_sucesso(self):
        """
        Cenário: Adicionar um item a um carrinho vazio com sucesso.
        """
        # ARRANGE: Configuramos nossos mocks para se comportarem como queremos
        # O repositório de joias vai "encontrar" nossa joia simulada
        self.joia_repo_mock.buscar_por_id.return_value = self.joia_mock
        
        # O repositório de carrinho vai retornar um carrinho vazio
        self.carrinho_repo_mock.buscar_por_usuario.return_value = Carrinho(
            id='carrinho-mock',
            usuario=self.usuario_mock,
            itens=[]
        )
        
        # ACT: Chamamos o método que queremos testar
        carrinho_resultante = self.use_case.execute(
            usuario=self.usuario_mock,
            joia_id='joia-123',
            quantidade=2
        )
        
        # ASSERT: Verificamos se o resultado é o esperado
        # 1. Verificamos se o carrinho resultante não está vazio
        self.assertEqual(len(carrinho_resultante.itens), 1)
        
        # 2. Verificamos se a joia e a quantidade estão corretas
        item_adicionado = carrinho_resultante.itens[0]
        self.assertEqual(item_adicionado.joia.id, self.joia_mock.id)
        self.assertEqual(item_adicionado.quantidade, 2)
        
        # 3. Verificamos se o método de salvar foi chamado exatamente uma vez
        self.carrinho_repo_mock.salvar_carrinho.assert_called_once_with(carrinho_resultante)
        
    def test_adicionar_item_com_estoque_insuficiente_falha(self):
        """
        Cenário: Tentar adicionar mais itens do que o disponível em estoque.
        """
        # ARRANGE
        self.joia_repo_mock.buscar_por_id.return_value = self.joia_mock
        self.carrinho_repo_mock.buscar_por_usuario.return_value = Carrinho(
            id='carrinho-mock',
            usuario=self.usuario_mock,
            itens=[]
        )
        
        # ACT e ASSERT: Verificamos se a exceção correta é levantada
        with self.assertRaises(EstoqueInsuficienteError):
            self.use_case.execute(
                usuario=self.usuario_mock,
                joia_id='joia-123',
                quantidade=11  # Mais do que o estoque (10)
            )
        
        # Verificamos que o método de salvar NÃO foi chamado
        self.carrinho_repo_mock.salvar_carrinho.assert_not_called()

# ====================================================================
# NOVO TESTE PARA CRIAR PEDIDO
# ====================================================================
class TestCriarPedido(unittest.TestCase):
    
    def setUp(self):
        self.carrinho_repo_mock = Mock()
        self.joia_repo_mock = Mock()
        self.pedido_repo_mock = Mock()
        self.pagamento_gateway_mock = Mock()

        self.use_case = CriarPedido(
            carrinho_repo=self.carrinho_repo_mock,
            joia_repo=self.joia_repo_mock,
            pedido_repo=self.pedido_repo_mock,
            pagamento_gateway=self.pagamento_gateway_mock
        )

        self.usuario_mock = Usuario(id=1, email='teste@example.com')
        self.endereco_mock = Endereco(
            cep='12345678', rua='Rua Teste', numero='100',
            bairro='Centro', cidade='Cidade Teste', estado='SP'
        )
        self.joia1 = Joia(id='joia-1', nome='Anel', preco=100.00, estoque=5)
        self.joia2 = Joia(id='joia-2', nome='Colar', preco=200.00, estoque=3)
        
        self.carrinho_com_itens = Carrinho(
            id='carrinho-1',
            usuario=self.usuario_mock,
            itens=[
                ItemCarrinho(joia=self.joia1, quantidade=1),
                ItemCarrinho(joia=self.joia2, quantidade=2)
            ]
        )

    def test_criar_pedido_com_sucesso(self):
        """
        Cenário: Criar um pedido a partir de um carrinho com itens.
        """
        # ARRANGE
        self.carrinho_repo_mock.buscar_por_usuario.return_value = self.carrinho_com_itens
        
        # ACT
        pedido_criado = self.use_case.execute(
            usuario=self.usuario_mock,
            tipo_pagamento='pix',
            endereco=self.endereco_mock
        )

        # ASSERT
        # 1. Verificamos se o método de pagamento foi chamado
        self.pagamento_gateway_mock.processar_pagamento.assert_called_once_with(
            tipo_pagamento='pix',
            valor_total=500.00 # 100 * 1 + 200 * 2
        )
        
        # 2. Verificamos se o pedido foi salvo no repositório
        self.pedido_repo_mock.salvar_pedido.assert_called_once()
        
        # 3. Verificamos se o carrinho foi esvaziado
        self.carrinho_repo_mock.esvaziar_carrinho.assert_called_once_with(self.carrinho_com_itens)

    def test_criar_pedido_com_carrinho_vazio_falha(self):
        """
        Cenário: Tentar criar um pedido com um carrinho vazio.
        """
        # ARRANGE
        self.carrinho_repo_mock.buscar_por_usuario.return_value = Carrinho(
            id='carrinho-vazio',
            usuario=self.usuario_mock,
            itens=[]
        )
        
        # ACT e ASSERT
        with self.assertRaises(CarrinhoVazioError):
            self.use_case.execute(
                usuario=self.usuario_mock,
                tipo_pagamento='pix',
                endereco=self.endereco_mock
            )
        
        # Verificamos que nenhum método de pagamento ou salvamento foi chamado
        self.pagamento_gateway_mock.processar_pagamento.assert_not_called()
        self.pedido_repo_mock.salvar_pedido.assert_not_called()


# ====================================================================
# TESTES PARA REMOVER ITEM DO CARRINHO
# ====================================================================
class TestRemoverItemDoCarrinho(unittest.TestCase):
    def setUp(self):
        self.carrinho_repo_mock = Mock()
        self.use_case = RemoverItemDoCarrinho(
            carrinho_repo=self.carrinho_repo_mock
        )
        self.usuario_mock = Usuario(id=1, email='teste@example.com')
        self.joia1 = Joia(id='joia-1', nome='Anel', preco=100.00, estoque=5)
        self.joia2 = Joia(id='joia-2', nome='Colar', preco=200.00, estoque=3)
        
        self.carrinho_com_itens = Carrinho(
            id='carrinho-1',
            usuario=self.usuario_mock,
            itens=[
                ItemCarrinho(joia=self.joia1, quantidade=1),
                ItemCarrinho(joia=self.joia2, quantidade=2)
            ]
        )

    def test_remover_item_com_sucesso(self):
        """
        Cenário: Remover um item existente do carrinho.
        """
        # ARRANGE
        self.carrinho_repo_mock.buscar_por_usuario.return_value = self.carrinho_com_itens
        
        # ACT
        carrinho_atualizado = self.use_case.execute(
            usuario=self.usuario_mock,
            joia_id='joia-1'
        )

        # ASSERT
        self.assertEqual(len(carrinho_atualizado.itens), 1)
        self.assertEqual(carrinho_atualizado.itens[0].joia.id, 'joia-2')
        self.carrinho_repo_mock.salvar_carrinho.assert_called_once_with(carrinho_atualizado)

    def test_remover_item_nao_existente_falha(self):
        """
        Cenário: Tentar remover um item que não está no carrinho.
        """
        # ARRANGE
        self.carrinho_repo_mock.buscar_por_usuario.return_value = self.carrinho_com_itens
        
        # ACT & ASSERT
        with self.assertRaises(ItemNaoEncontradoError):
            self.use_case.execute(
                usuario=self.usuario_mock,
                joia_id='joia-nao-existente'
            )
        
        # Verificamos que o carrinho não foi alterado nem salvo
        self.carrinho_repo_mock.salvar_carrinho.assert_not_called()

# ====================================================================
# TESTE DE FALHA PARA O CRIAR PEDIDO
# ====================================================================
class TestCriarPedido(unittest.TestCase):
    # ... (Seu código existente da classe TestCriarPedido) ...
    
    def test_criar_pedido_com_pagamento_falho(self):
        """
        Cenário: Verificar se o use case lida corretamente com a falha no pagamento.
        """
        # ARRANGE
        self.carrinho_repo_mock.buscar_por_usuario.return_value = self.carrinho_com_itens
        
        # Configurar o mock para levantar a exceção de falha de pagamento
        self.pagamento_gateway_mock.processar_pagamento.side_effect = PagamentoFalhouError("Pagamento recusado.")
        
        # ACT & ASSERT
        with self.assertRaises(PagamentoFalhouError):
            self.use_case.execute(
                usuario=self.usuario_mock,
                tipo_pagamento='cartao',
                endereco=self.endereco_mock
            )
        
        # Verificamos que o pedido NÃO foi salvo, pois o pagamento falhou
        self.pedido_repo_mock.salvar_pedido.assert_not_called()
