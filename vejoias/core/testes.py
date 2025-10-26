# vejoias/core/tests.py

import unittest
from unittest.mock import Mock, patch, call
from decimal import Decimal

# Importamos as classes que queremos testar
from vejoias.core.use_cases import AdicionarItemAoCarrinho, CriarPedido, RemoverItemDoCarrinho, AtualizarStatusPedido, AtualizarStatusManual, StatusInvalidoError, PedidoNaoEncontradoError
from vejoias.core.entities import Joia, Usuario, Carrinho, ItemCarrinho, Pedido, Endereco
from vejoias.core.exceptions import EstoqueInsuficienteError, CarrinhoVazioError, PagamentoFalhouError, ItemNaoEncontradoError

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
            slug='anel-de-ouro',
            descricao='Um lindo anel de ouro',
            preco=Decimal('1500.00'),
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

    def test_cria_pedido_e_notifica_com_boleto(self):
        """
        Testa se o pedido é criado com sucesso usando o método Boleto 
        e se as notificações são chamadas.
        """
        
        # ACT: Executar o caso de uso com tipo_pagamento="BOLETO"
        pedido = self.uc_criar_pedido.execute(
            usuario=carrinho_cheio.usuario,
            tipo_pagamento="BOLETO", # NOVO PAGAMENTO
            endereco=endereco_entrega,
            numero_telefone=numero_whatsapp 
        )

        # ASSERT 1: Pedido criado corretamente
        self.assertIsInstance(pedido, Pedido)
        self.assertEqual(pedido.total, 200.00) # (100.00 * 2)

        # ASSERT 2: Pagamento chamado com o método CORRETO e os dados DO PAGADOR
        # O Use Case deve ter passado 'usuario' e 'endereco' corretamente
        self.pagamento_gateway.processar_pagamento_boleto.assert_called_once_with(
            200.00, # total
            carrinho_cheio.usuario, # entidade Usuario
            endereco_entrega # entidade Endereco
        )

        # ASSERT 3: Estoque, Carrinho e Repositório chamados
        self.assertEqual(joia_ouro.estoque, 3) # Estoque decrementado
        self.joia_repo.salvar.assert_called_once()
        self.carrinho_repo.salvar.assert_called_once()
        self.pedido_repo.salvar.assert_called_once()

        # ASSERT 4: Notificação de WhatsApp e E-mail chamada
        self.whatsapp_gateway.enviar_confirmacao_pedido.assert_called_once()
        self.email_service.enviar_confirmacao_pedido.assert_called_once()

    def test_falha_se_boleto_falhar_no_gateway(self):
        """Testa se uma exceção é lançada se a criação do Boleto falhar."""
        
        # Configurar o mock para simular uma falha na criação do Boleto
        self.pagamento_gateway.processar_pagamento_boleto.side_effect = PagamentoFalhouError("Boleto não gerado")
        
        # ASSERT: Deve levantar a exceção
        with self.assertRaises(PagamentoFalhouError):
            self.uc_criar_pedido.execute(
                usuario=carrinho_cheio.usuario,
                tipo_pagamento="BOLETO",
                endereco=endereco_entrega,
                numero_telefone=numero_whatsapp
            )
            
        # Garante que as notificações NÃO são enviadas
        self.whatsapp_gateway.enviar_confirmacao_pedido.assert_not_called()
        self.email_service.enviar_confirmacao_pedido.assert_not_called()


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
        self.joia1 = Joia(id='joia-1', nome='Anel', slug='anel', descricao='Anel simples', preco=Decimal('100.00'), estoque=5)
        self.joia2 = Joia(id='joia-2', nome='Colar', slug='colar', descricao='Colar simples', preco=Decimal('200.00'), estoque=3)
        
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
# CONFIGURAÇÃO DE FIXTURES (Dados Mock)
# ====================================================================
joia_ouro = Joia(id=1, nome="Colar de Ouro", slug="colar-de-ouro", descricao="Colar banhado a ouro", preco=Decimal('100.00'), estoque=5)
item_carrinho = ItemCarrinho(joia=joia_ouro, quantidade=2)
carrinho_cheio = Carrinho(id=99, usuario=Usuario(id=10, email="teste@vejoias.com"), itens=[item_carrinho])
endereco_entrega = Endereco(linha1="Rua Teste, 10", cidade="São Paulo", estado="SP", cep="00000-000")
numero_whatsapp = "5511987654321"

# ====================================================================
# TESTE DO USE CASE CRIAR PEDIDO
# ====================================================================

class CriarPedidoTestCase(unittest.TestCase):

    def setUp(self):
        # Mocks para Dependências
        self.carrinho_repo = Mock()
        self.joia_repo = Mock()
        self.pedido_repo = Mock()
        self.pagamento_gateway = Mock()
        self.whatsapp_gateway = Mock()
        self.email_service = Mock() 

        # Configuração do Comportamento Padrão
        self.carrinho_repo.buscar_por_usuario.return_value = carrinho_cheio
        self.joia_repo.buscar_por_id.return_value = joia_ouro
        self.pagamento_gateway.processar_pagamento_pix.return_value = "TRANS-PIX-123"

        # Instância do Use Case com Mocks injetados
        self.uc_criar_pedido = CriarPedido(
            self.carrinho_repo,
            self.joia_repo,
            self.pedido_repo,
            self.pagamento_gateway,
            self.whatsapp_gateway,
            self.email_service
        )
        
    def test_cria_pedido_e_notifica_com_sucesso(self):
        """Testa o fluxo de sucesso: pedido criado, estoque, pagamento e ambas notificações OK."""
        
        pedido = self.uc_criar_pedido.execute(
            usuario=carrinho_cheio.usuario,
            tipo_pagamento="pix",
            endereco=endereco_entrega,
            numero_telefone=numero_whatsapp 
        )

        # ASSERT: Notificações chamadas
        self.whatsapp_gateway.enviar_confirmacao_pedido.assert_called_once()
        self.email_service.enviar_confirmacao_pedido.assert_called_once()
        self.assertEqual(joia_ouro.estoque, 3) 
        self.assertIsInstance(pedido, Pedido)


    def test_falha_se_estoque_insuficiente(self):
        """Testa se uma exceção é lançada se o estoque for insuficiente."""
        self.joia_repo.buscar_por_id.return_value.estoque = 1 # Estoque insuficiente (precisa de 2)
        
        with self.assertRaises(EstoqueInsuficienteError):
            self.uc_criar_pedido.execute(
                usuario=carrinho_cheio.usuario,
                tipo_pagamento="pix",
                endereco=endereco_entrega,
                numero_telefone=numero_whatsapp
            )
            
        # Garante que NENHUM processo posterior é chamado
        self.pagamento_gateway.processar_pagamento_pix.assert_not_called()
        self.whatsapp_gateway.enviar_confirmacao_pedido.assert_not_called()
        

    def test_falha_se_pagamento_falhar(self):
        """Testa se uma exceção é lançada se o gateway de pagamento falhar."""
        # Configurar o mock do pagamento para levantar uma exceção simulada
        self.pagamento_gateway.processar_pagamento_pix.side_effect = Exception("Falha de comunicação com o Mercado Pago")
        
        with self.assertRaises(PagamentoFalhouError):
            self.uc_criar_pedido.execute(
                usuario=carrinho_cheio.usuario,
                tipo_pagamento="pix",
                endereco=endereco_entrega,
                numero_telefone=numero_whatsapp
            )
            
        # Garante que o pedido NÃO é salvo e as notificações NÃO são enviadas
        self.pedido_repo.salvar.assert_not_called()
        self.whatsapp_gateway.enviar_confirmacao_pedido.assert_not_called()


    def test_continua_fluxo_se_whatsapp_falhar(self):
        """
        Testa se o pedido é criado e o e-mail é enviado, mesmo que o WhatsApp falhe.
        Falha em notificação não deve interromper o checkout.
        """
        # Configurar o mock do WhatsApp para retornar False ou levantar uma exceção
        self.whatsapp_gateway.enviar_confirmacao_pedido.side_effect = Exception("Erro na Evolution API")
        
        # O Use Case deve ser concluído com sucesso (retorna o objeto Pedido)
        pedido = self.uc_criar_pedido.execute(
            usuario=carrinho_cheio.usuario,
            tipo_pagamento="pix",
            endereco=endereco_entrega,
            numero_telefone=numero_whatsapp
        )
        
        # ASSERT:
        self.assertIsInstance(pedido, Pedido) # O pedido é criado
        self.email_service.enviar_confirmacao_pedido.assert_called_once() # O e-mail ainda é enviado
        self.pedido_repo.salvar.assert_called_once() # O pedido é salvo
        self.assertEqual(joia_ouro.estoque, 3) # O estoque é decrementado


# ====================================================================
# TESTE DO USE CASE ATUALIZAR STATUS
# ====================================================================

class AtualizarStatusPedidoTestCase(unittest.TestCase):
    
    def setUp(self):
        # Mocks para Dependências
        self.pedido_repo = Mock()
        self.pagamento_gateway = Mock()
        self.whatsapp_gateway = Mock()
        self.email_service = Mock()
        
        # FIXTURE: Pedido inicial com status PENDENTE (simulando Boleto/PIX)
        self.pedido_pendente = Pedido(
            id=101, 
            usuario=Usuario(id=10, email="teste@vejoias.com", numero_telefone_contato="5511999999999"), 
            total=200.00, 
            transacao_id="TRANS-BOL-ABCDE",
            status="PENDENTE" # Status inicial
        )

        # Configurar Mocks
        self.pedido_repo.buscar_por_transacao_id.return_value = self.pedido_pendente
        
        # Instância do Use Case com Mocks injetados
        self.uc_atualizar_status = AtualizarStatusPedido(
            pedido_repo=self.pedido_repo,
            pagamento_gateway=self.pagamento_gateway,
            whatsapp_gateway=self.whatsapp_gateway,
            email_service=self.email_service
        )

    def test_atualiza_status_para_pago_e_notifica(self):
        """
        Testa o fluxo de sucesso: Webhook de Pagamento Aprovado.
        """
        # ARRANGE: Simular que o Mercado Pago retornou 'approved'
        self.pagamento_gateway.buscar_status_transacao.return_value = "approved"
        
        transacao_id = "TRANS-BOL-ABCDE"
        
        # ACT: Executar o caso de uso (Webhook)
        self.uc_atualizar_status.execute(transacao_id)

        # ASSERT 1: O pedido deve ter sido atualizado e salvo
        self.assertEqual(self.pedido_pendente.status, "PAGO")
        self.pedido_repo.salvar.assert_called_once()
        
        # ASSERT 2: Os gateways de notificação de aprovação devem ser chamados
        self.whatsapp_gateway.enviar_aprovacao_pagamento.assert_called_once_with(
            pedido=self.pedido_pendente,
            numero_telefone=self.pedido_pendente.usuario.numero_telefone_contato
        )
        self.email_service.enviar_aprovacao_pagamento.assert_called_once_with(self.pedido_pendente)
        
    def test_status_pendente_nao_muda_nada(self):
        """
        Testa se um Webhook com status 'pending' não causa mudanças ou notificações repetidas.
        """
        # ARRANGE: Simular que o Mercado Pago retornou 'pending' (novo webhook antes da compensação)
        self.pagamento_gateway.buscar_status_transacao.return_value = "pending"
        
        # ACT
        self.uc_atualizar_status.execute("TRANS-BOL-ABCDE")

        # ASSERT:
        self.assertEqual(self.pedido_pendente.status, "PENDENTE") # Status não mudou
        self.pedido_repo.salvar.assert_not_called() # Não deve salvar
        self.whatsapp_gateway.enviar_aprovacao_pagamento.assert_not_called() # Não deve notificar

    def test_status_rejected_cancela_pedido(self):
        """
        Testa se um Webhook de status 'rejected' muda o status para CANCELADO.
        """
        # ARRANGE: Simular que o Mercado Pago retornou 'rejected' (Boleto expirado)
        self.pagamento_gateway.buscar_status_transacao.return_value = "rejected"
        
        # ACT
        self.uc_atualizar_status.execute("TRANS-BOL-ABCDE")

        # ASSERT:
        self.assertEqual(self.pedido_pendente.status, "CANCELADO")
        self.pedido_repo.salvar.assert_called_once()
        self.whatsapp_gateway.enviar_aprovacao_pagamento.assert_not_called()


# ====================================================================
# TESTE DO USE CASE ATUALIZAR STATUS MANUAL
# ====================================================================

class AtualizarStatusManualTestCase(unittest.TestCase):
    
    def setUp(self):
        # Mocks para Dependências
        self.pedido_repo = Mock()
        self.notificacao_service = Mock()
        
        # Fixture: Pedido inicial
        self.usuario = Usuario(id=1, email="admin@teste.com", telefone="5511987654321")
        self.endereco = Endereco(cep="12345678", rua="Rua Teste", numero="10", bairro="Centro", cidade="SP", estado="SP")
        self.pedido_em_processo = Pedido(
            id=102, 
            usuario=self.usuario, 
            endereco_entrega=self.endereco,
            total=Decimal('150.00'),
            transacao_id="TRANS-CARTAO-XYZ",
            status="PAGO", # Estado inicial
            items=[ItemCarrinho(joia=Joia(nome="Anel Teste", slug="anel-teste", descricao="Um anel para teste", preco=Decimal('150.00'), estoque=5), quantidade=1)]
        )

        # Configurar Mock do Repositório para retornar o pedido
        self.pedido_repo.buscar_por_id.return_value = self.pedido_em_processo
        
        # Instância do Use Case
        self.uc_atualizar_status = AtualizarStatusManual(
            pedido_repo=self.pedido_repo,
            notificacao_service=self.notificacao_service
        )

    # ----------------------------------------------------------------------
    # TESTES DE SUCESSO E FLUXO
    # ----------------------------------------------------------------------
    
    def test_atualiza_status_para_enviado_e_notifica(self):
        """
        Testa a mudança de status e a notificação de envio.
        """
        novo_status = "ENVIADO"
        
        # ACT: Executar o Use Case
        pedido_atualizado = self.uc_atualizar_status.execute(
            pedido_id=self.pedido_em_processo.id, 
            novo_status=novo_status
        )

        # ASSERT 1: Status e Persistência
        self.assertEqual(pedido_atualizado.status, novo_status)
        self.pedido_repo.salvar.assert_called_once_with(pedido_atualizado)
        self.pedido_repo.buscar_por_id.assert_called_once()
        
        # ASSERT 2: Notificação Específica deve ser chamada
        self.notificacao_service.enviar_status_rastreamento.assert_called_once_with(pedido_atualizado)
        self.notificacao_service.enviar_status_processamento.assert_not_called() # Não deve notificar processamento

    def test_atualiza_status_para_processando_e_notifica(self):
        """
        Testa a mudança de status e a notificação de processamento.
        """
        novo_status = "PROCESSANDO"
        self.pedido_em_processo.status = "PAGO" # Garante o status inicial
        
        # ACT
        pedido_atualizado = self.uc_atualizar_status.execute(
            pedido_id=self.pedido_em_processo.id, 
            novo_status=novo_status
        )

        # ASSERT 1: Status e Persistência
        self.assertEqual(pedido_atualizado.status, novo_status)
        self.pedido_repo.salvar.assert_called_once()
        
        # ASSERT 2: Notificação de Processamento
        self.notificacao_service.enviar_status_processamento.assert_called_once_with(pedido_atualizado)
        self.notificacao_service.enviar_status_rastreamento.assert_not_called()

    def test_nao_muda_se_status_for_o_mesmo(self):
        """
        Testa que o repositório não é chamado se o status não muda.
        """
        self.pedido_em_processo.status = "PAGO"
        
        # ACT
        self.uc_atualizar_status.execute(pedido_id=self.pedido_em_processo.id, novo_status="PAGO")

        # ASSERT: Não deve ter salvado
        self.pedido_repo.salvar.assert_not_called()
        self.notificacao_service.enviar_status_processamento.assert_not_called()
        
    # ----------------------------------------------------------------------
    # TESTES DE VALIDAÇÃO E ERRO
    # ----------------------------------------------------------------------

    def test_falha_se_status_for_invalido(self):
        """
        Testa a exceção para um status que não existe na lista de válidos.
        """
        # ACT & ASSERT
        with self.assertRaises(StatusInvalidoError):
            self.uc_atualizar_status.execute(pedido_id=self.pedido_em_processo.id, novo_status="CANCELADO_PELO_CLIENTE")
            
        # Garante que nada foi salvo
        self.pedido_repo.salvar.assert_not_called()

    def test_falha_se_pedido_nao_for_encontrado(self):
        """
        Testa a exceção se o repositório não retornar o pedido.
        """
        # ARRANGE: Configurar o mock para retornar None
        self.pedido_repo.buscar_por_id.return_value = None
        
        # ACT & ASSERT
        with self.assertRaises(PedidoNaoEncontradoError):
            self.uc_atualizar_status.execute(pedido_id=999, novo_status="CANCELADO")
            
        # Garante que o repositório foi chamado (tentou buscar)
        self.pedido_repo.buscar_por_id.assert_called_once()
        self.pedido_repo.salvar.assert_not_called()
