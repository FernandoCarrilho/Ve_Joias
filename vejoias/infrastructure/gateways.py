import os
import requests
from datetime import datetime
import uuid
from decouple import config
from decimal import Decimal
from django.conf import settings
from django.core.mail import send_mail
from typing import List, Protocol, Optional, Tuple

# Importa os Protocols e Entidades da camada Core (Use Cases e Entities)
from vejoias.core.use_cases import IGatewayPagamento, IEmailService, IWhatsappGateway
from vejoias.core.entities import Pedido, Usuario, Endereco, TransacaoPagamento
from vejoias.core.exceptions import PagamentoFalhouError


# ====================================================================
# GATEWAYS: Implementações concretas que se comunicam com APIs externas.
# ====================================================================

class MercadoPagoGateway(IGatewayPagamento):
    """
    Gateway para comunicação com a API de Pagamento do Mercado Pago.
    Implementa a interface IGatewayPagamento do Core, unificando os 
    métodos de pagamento específicos.
    """
    
    # Mapeamento do status do Mercado Pago para o status de TransacaoPagamento
    _STATUS_MAP = {
        "approved": "APROVADO",
        "pending": "PENDENTE",
        "in_process": "PENDENTE",
        "rejected": "REJEITADO",
        "refunded": "ESTORNADO",
        "cancelled": "CANCELADO",
        # Adicionar outros conforme a documentação do MP
    }

    def __init__(self):
        self.api_base_url = "https://api.mercadopago.com/v1"
        # Deve ser lido de variáveis de ambiente seguras (configurado no settings.py do Django ou .env)
        self.access_token = os.environ.get("MERCADO_PAGO_ACCESS_TOKEN", config("MERCADO_PAGO_ACCESS_TOKEN", default="TOKEN_NAO_CONFIGURADO"))
        
        if not self.access_token or self.access_token == "TOKEN_NAO_CONFIGURADO":
            # Em vez de levantar ValueError, quebra o __init__ de forma controlada
            print("ERRO: MERCADO_PAGO_ACCESS_TOKEN não configurado. Pagamentos reais falharão.")

    # --- MÉTODOS PRIVADOS DE PROCESSAMENTO ESPECÍFICO ---

    def _processar_pix(self, pedido: Pedido, usuario: Usuario, dados: dict) -> TransacaoPagamento:
        """Processa um pagamento via Pix (Gerando QR Code)."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": str(uuid.uuid4()),  # Para evitar duplicidade
        }
        
        # Assumindo que o CPF, nome e email vêm do objeto Usuario
        payload = {
            "transaction_amount": float(pedido.total_pedido),
            "payment_method_id": "pix",
            "description": f"Pedido {pedido.id} - Vê Jóias",
            "payer": {
                "email": usuario.email,
                "first_name": usuario.nome.split()[0] if usuario.nome else "Comprador",
                "last_name": usuario.nome.split()[-1] if usuario.nome and len(usuario.nome.split()) > 1 else "", 
                "identification": {
                    "type": "CPF",
                    # CPF é um campo vital para Pix/Boleto. Assumimos que está em 'dados' ou no model Usuario
                    "number": dados.get('cpf', '00000000000'), 
                }
            },
        }
        
        try:
            url = f"{self.api_base_url}/payments"
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            mp_status = data.get("status")
            transacao_id = data.get("id")
            
            if mp_status in ["pending", "in_process"]:
                # Pix/Boleto gera um link ou um QR Code. Buscamos o link/código.
                url_pagamento = data.get("point_of_interaction", {}).get("transaction_data", {}).get("ticket_url")
                
                return TransacaoPagamento(
                    referencia_externa=str(transacao_id),
                    valor=pedido.total_pedido,
                    status_pagamento=self._STATUS_MAP.get(mp_status, "PENDENTE"),
                    data_criacao=datetime.now(),
                    url_pagamento=url_pagamento
                )
            else:
                raise PagamentoFalhouError(f"Pagamento Pix recusado. Status MP: {mp_status}")

        except requests.exceptions.RequestException as e:
            raise PagamentoFalhouError(f"Erro de conexão com a API do Mercado Pago: {e}")

    def _processar_boleto(self, pedido: Pedido, usuario: Usuario, endereco: Endereco, dados: dict) -> TransacaoPagamento:
        """Processa um pagamento via Boleto (Geração do PDF/Linha digitável)."""
        # Implementação similar ao _processar_pix, mas com payment_method_id="bolbradesco"
        # e mais dependente dos dados de endereço (Endereco) para cobrança.
        # Por brevidade, vamos usar o mesmo retorno de _processar_pix, mas o MP exige mais dados aqui.
        
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": str(uuid.uuid4()),  # Para evitar duplicidade
        }
        
        # O payload para Boleto exige os dados de Endereço no payer/address
        payload = {
             "transaction_amount": float(pedido.total_pedido),
             "payment_method_id": "bolbradesco",
             "description": f"Pedido {pedido.id} - Vê Jóias",
             "payer": {
                 "email": usuario.email,
                 "first_name": usuario.nome.split()[0] if usuario.nome else "Comprador",
                 "last_name": usuario.nome.split()[-1] if usuario.nome and len(usuario.nome.split()) > 1 else "", 
                 "identification": {
                    "type": "CPF",
                    "number": dados.get('cpf', '00000000000'), 
                 },
                 "address": {
                    "zip_code": endereco.cep.replace('-', ''),
                    "street_name": endereco.rua,
                    "street_number": endereco.numero,
                    "city": endereco.cidade,
                    "federal_unit": endereco.estado
                },
             },
        }
        
        try:
            url = f"{self.api_base_url}/payments"
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            mp_status = data.get("status")
            transacao_id = data.get("id")
            
            if mp_status in ["pending", "in_process"]:
                url_pagamento = data.get("point_of_interaction", {}).get("transaction_data", {}).get("ticket_url")
                
                return TransacaoPagamento(
                    referencia_externa=str(transacao_id),
                    valor=pedido.total_pedido,
                    status_pagamento=self._STATUS_MAP.get(mp_status, "PENDENTE"),
                    data_criacao=datetime.now(),
                    url_pagamento=url_pagamento
                )
            else:
                raise PagamentoFalhouError(f"Pagamento Boleto recusado. Status MP: {mp_status}")

        except requests.exceptions.RequestException as e:
            raise PagamentoFalhouError(f"Erro de conexão com a API do Mercado Pago: {e}")


    def _processar_cartao(self, pedido: Pedido, usuario: Usuario, dados: dict) -> TransacaoPagamento:
        """
        Processa um pagamento via cartão de crédito usando o token do cartão 
        obtido no frontend.
        """
        card_token = dados.get('card_token') # Token obtido no frontend via Mercado Pago SDK
        if not card_token:
             raise PagamentoFalhouError("Token de cartão ausente na requisição.")

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Idempotency-Key": str(uuid.uuid4()),
        }
        
        payload = {
            "transaction_amount": float(pedido.total_pedido),
            "description": f"Pedido {pedido.id} - Vê Jóias",
            "token": card_token,  # Token do cartão
            "installments": dados.get('installments', 1),
            "payment_method_id": dados.get('payment_method_id', 'visa'), # Ex: master, visa, etc.
            "payer": {
                "email": usuario.email,
                "identification": {
                    "type": "CPF",
                    "number": dados.get('cpf', '00000000000'), 
                },  
            }
        }

        try:
            url = f"{self.api_base_url}/payments"
            response = requests.post(url, json=payload, headers=headers, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            mp_status = data.get("status")
            transacao_id = data.get("id")
            
            # Cartão geralmente retorna approved ou rejected imediatamente
            return TransacaoPagamento(
                referencia_externa=str(transacao_id),
                valor=pedido.total_pedido,
                status_pagamento=self._STATUS_MAP.get(mp_status, "REJEITADO"),
                data_criacao=datetime.now(),
                url_pagamento=None
            )

        except requests.exceptions.RequestException as e:
            raise PagamentoFalhouError(f"Erro de conexão com a API do Mercado Pago: {e}")


    # --- MÉTODOS PÚBLICOS QUE IMPLEMENTAM O PROTOCOLO CORE ---

    def processar_pagamento(self, pedido: Pedido, metodo: str, usuario: Usuario, dados: dict) -> TransacaoPagamento:
        """
        Método unificado do Protocolo IGatewayPagamento.
        Despacha a chamada para o método de pagamento específico.
        """
        endereco = dados.get('endereco')
        
        if not usuario:
             raise PagamentoFalhouError("Dados de Usuário ausentes para processamento do pagamento.")

        metodo_upper = metodo.upper()

        if metodo_upper == "PIX":
            return self._processar_pix(pedido, usuario, dados)
        elif metodo_upper == "BOLETO":
            if not endereco:
                raise PagamentoFalhouError("Endereço de cobrança ausente para Boleto.")
            return self._processar_boleto(pedido, usuario, endereco, dados)
        elif metodo_upper == "CARTAO":
            return self._processar_cartao(pedido, usuario, dados)
        else:
            raise PagamentoFalhouError(f"Método de pagamento '{metodo}' não suportado.")

    def verificar_status(self, transacao_id: str) -> TransacaoPagamento:
        """
        Implementa o Protocolo IGatewayPagamento.
        Busca o status atual de uma transação (pagamento) no Mercado Pago.
        """
        headers = {
            "Authorization": f"Bearer {self.access_token}",
        }
        
        url = f"{self.api_base_url}/payments/{transacao_id}"
        
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status() 
            
            data = response.json()
            mp_status = data.get("status")
            valor = Decimal(str(data.get("transaction_amount", 0.0))) # Garante precisão decimal
            
            core_status = self._STATUS_MAP.get(mp_status, "PENDENTE")

            return TransacaoPagamento(
                referencia_externa=transacao_id,
                valor=valor,
                status_pagamento=core_status,
                data_criacao=datetime.now() # Data da verificação
            )
            
        except requests.exceptions.RequestException as e:
            print(f"ERRO MP API: Falha ao buscar status da transação {transacao_id}: {e}")
            # Lançamos uma exceção genérica para o Use Case lidar
            raise Exception("Falha ao buscar status da transação no Gateway.")


class GroqGateway:
    """Gateway para comunicação com a API da Groq para o chatbot (Não implementa protocolo Core)."""
    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY", config("GROQ_API_KEY", default="KEY_NAO_CONFIGURADA"))
        self.base_url = "https://api.groq.com/openai/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        if self.api_key == "KEY_NAO_CONFIGURADA":
            print("AVISO: GROQ_API_KEY não configurada.")
    
    def perguntar_ao_chatbot(self, prompt: str) -> str:
        """Envia um prompt para o chatbot e retorna a resposta."""
        payload = {
            "model": "llama3-8b-8192",  
            "messages": [{"role": "user", "content": prompt}],
        }
        
        try:
            response = requests.post(f"{self.base_url}/chat/completions", json=payload, headers=self.headers, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            # Certifica-se de que a data_criacao está sendo atribuída corretamente
            return data["choices"][0]["message"]["content"]
            
        except requests.exceptions.RequestException as e:
            raise Exception(f"Erro de conexão com a API da Groq: {e}")


class EvolutionAPIGateway(IWhatsappGateway):
    """
    Gateway para automação de mensagens no WhatsApp via EvolutionAPI.
    Implementa o Protocolo IWhatsappGateway.
    """
    
    def __init__(self):
        # Lendo configurações de ambiente
        self.api_key = os.environ.get("EVOLUTION_API_KEY", config("EVOLUTION_API_KEY", default="KEY_NAO_CONFIGURADA"))
        self.instance_name = os.environ.get("EVOLUTION_INSTANCE_NAME", config("EVOLUTION_INSTANCE_NAME", default="INSTANCIA_NAO_CONFIGURADA"))
        self.base_url = os.environ.get("EVOLUTION_API_URL", config("EVOLUTION_API_URL", default="URL_NAO_CONFIGURADA"))
        
        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }
        if self.api_key == "KEY_NAO_CONFIGURADA":
            print("AVISO: Chave Evolution-API não configurada.")

    def _enviar_mensagem(self, numero_telefone: str, mensagem: str) -> bool:
        """Método auxiliar para enviar a mensagem real."""
        if not self.api_key or not self.instance_name or not self.base_url:
            print("AVISO: Configuração da Evolution-API incompleta. Envio de WhatsApp ignorado.")
            return False

        payload = {
            "number": numero_telefone,
            "options": {"delay": 1200, "presence": "typing"},
            "textMessage": {"text": mensagem}
        }
        
        try:
            url = f"{self.base_url}/{self.instance_name}/message/sendText"
            response = requests.post(url, json=payload, headers=self.headers, timeout=5)
            response.raise_for_status() 
            
            return response.status_code in [200, 201]
            
        except requests.exceptions.RequestException as e:
            print(f"ERRO EvolutionAPI: Falha ao enviar mensagem: {e}")
            return False

    def enviar_confirmacao_pedido(self, pedido: Pedido, numero_telefone: str) -> bool:
        """Implementa IWhatsappGateway - Confirmação do pedido."""
        mensagem = (
            f"🎉 Pedido {pedido.id} confirmado na Vê Jóias! 🎉\n\n"
            f"Status: {pedido.status}\n"
            f"Total: R$ {pedido.total_pedido:.2f}\n" # Usando total_pedido, que é o correto
            f"Obrigado por comprar conosco!"
        )
        return self._enviar_mensagem(numero_telefone, mensagem)
    
    def enviar_aprovacao_pagamento(self, pedido: Pedido, numero_telefone: str) -> bool:
        """Implementa IWhatsappGateway - Aprovação do pagamento."""
        mensagem = (
            f"✅ Ótima notícia! Seu pagamento para o Pedido {pedido.id} foi APROVADO! 🎉\n\n"
            f"Estamos preparando o envio. Você receberá um código de rastreio em breve.\n"
            f"Equipe Vê Jóias."
        )
        return self._enviar_mensagem(numero_telefone, mensagem)

    def enviar_status_mudanca(self, pedido: Pedido, numero_telefone: str) -> bool:
        """Implementa IWhatsappGateway - Mudança de status do pedido."""
        mensagem = (
            f"🔄 O status do seu Pedido {pedido.id} foi atualizado para: {pedido.status}\n\n"
            f"Para mais informações, acesse nossa plataforma.\n"
            f"Equipe Vê Jóias."
        )
        return self._enviar_mensagem(numero_telefone, mensagem)


class WhatsAppGatewayMock(IWhatsappGateway):
    """
    Gateway Mock para simulação de mensagens WhatsApp.
    Implementa o Protocolo IWhatsappGateway.
    """
    
    def _enviar_mensagem(self, numero_telefone: str, mensagem: str) -> bool:
        """Método auxiliar que simula envio de mensagem."""
        print(f"[MOCK WhatsApp] Para: {numero_telefone}\nMensagem: {mensagem}")
        return True

    def enviar_confirmacao_pedido(self, pedido: Pedido, numero_telefone: str) -> bool:
        """Implementa IWhatsappGateway - Confirmação do pedido."""
        mensagem = (
            f"🎉 Pedido {pedido.id} confirmado na Vê Jóias! 🎉\n\n"
            f"Status: {pedido.status}\n"
            f"Total: R$ {pedido.total_pedido:.2f}\n"
            f"Obrigado por comprar conosco!"
        )
        return self._enviar_mensagem(numero_telefone, mensagem)
    
    def enviar_aprovacao_pagamento(self, pedido: Pedido, numero_telefone: str) -> bool:
        """Implementa IWhatsappGateway - Aprovação do pagamento."""
        mensagem = (
            f"✅ Ótima notícia! Seu pagamento para o Pedido {pedido.id} foi APROVADO! 🎉\n\n"
            f"Estamos preparando o envio. Você receberá um código de rastreio em breve.\n"
            f"Equipe Vê Jóias."
        )
        return self._enviar_mensagem(numero_telefone, mensagem)

    def enviar_status_mudanca(self, pedido: Pedido, numero_telefone: str) -> bool:
        """Implementa IWhatsappGateway - Mudança de status do pedido."""
        mensagem = (
            f"🔄 O status do seu Pedido {pedido.id} foi atualizado para: {pedido.status}\n\n"
            f"Para mais informações, acesse nossa plataforma.\n"
            f"Equipe Vê Jóias."
        )
        return self._enviar_mensagem(numero_telefone, mensagem)


class EmailServiceGateway(IEmailService):
    """
    Gateway para envio de e-mails usando o sistema de e-mail do Django.
    Implementa o Protocolo IEmailService.
    """

    def enviar_confirmacao_pedido(self, pedido: Pedido) -> bool:
        """Implementa IEmailService - Confirmação do pedido."""
        
        # O destinatário deve ser o e-mail do usuário, que deve ser recuperado no Use Case.
        # Aqui assumimos que o objeto Pedido tem o email do comprador em algum lugar (ou no User)
        destinatario = 'cliente@example.com' # Placeholder
        if hasattr(pedido, 'usuario') and hasattr(pedido.usuario, 'email'):
             destinatario = pedido.usuario.email
        
        assunto = f"Confirmação do Pedido #{pedido.id} na Vê Jóias ({pedido.status})"
        
        mensagem = (
            f"Olá,\n\n"
            f"Seu pedido #{pedido.id} foi recebido e está com status: {pedido.status}.\n"
            f"O valor total é de R$ {pedido.total_pedido:.2f}.\n\n"
            f"Obrigado por comprar na Vê Joias!"
        )
        
        remetente = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@vejoias.com'

        try:
            send_mail(
                assunto,
                mensagem,
                remetente,
                [destinatario],
                fail_silently=False, 
            )
            return True
            
        except Exception as e:
            print(f"ERRO: Falha ao enviar e-mail de confirmação do pedido {pedido.id}: {e}")
            return False

    def enviar_aprovacao_pagamento(self, pedido: Pedido) -> bool:
        """Implementa IEmailService - Aprovação do pagamento."""
        
        destinatario = 'cliente@example.com' # Placeholder
        if hasattr(pedido, 'usuario') and hasattr(pedido.usuario, 'email'):
             destinatario = pedido.usuario.email
             
        assunto = f"Pagamento APROVADO! Pedido #{pedido.id} - Vê Jóias"
        
        mensagem = (
            f"Olá,\n\n"
            f"Informamos que o pagamento do seu Pedido #{pedido.id} foi APROVADO com sucesso!\n"
            f"Seu pedido está sendo preparado para envio.\n\n"
            f"Equipe Vê Jóias."
        )
        
        remetente = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@vejoias.com'

        try:
            send_mail(
                assunto,
                mensagem,
                remetente,
                [destinatario],
                fail_silently=False, 
            )
            return True
        except Exception as e:
            print(f"ERRO: Falha ao enviar e-mail de aprovação do pedido {pedido.id}: {e}")
            return False

    def enviar_status_mudanca(self, pedido: Pedido) -> bool:
        """Implementa IEmailService - Mudança de status do pedido."""
        
        destinatario = 'cliente@example.com' # Placeholder
        if hasattr(pedido, 'usuario') and hasattr(pedido.usuario, 'email'):
            destinatario = pedido.usuario.email
             
        assunto = f"Status Atualizado - Pedido #{pedido.id} - Vê Jóias"
        
        mensagem = (
            f"Olá,\n\n"
            f"O status do seu Pedido #{pedido.id} foi atualizado para: {pedido.status}\n"
            f"Para mais informações, acesse nossa plataforma.\n\n"
            f"Equipe Vê Jóias."
        )
        
        remetente = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@vejoias.com'

        try:
            send_mail(
                assunto,
                mensagem,
                remetente,
                [destinatario],
                fail_silently=False, 
            )
            return True
        except Exception as e:
            print(f"ERRO: Falha ao enviar e-mail de mudança de status do pedido {pedido.id}: {e}")
            return False
