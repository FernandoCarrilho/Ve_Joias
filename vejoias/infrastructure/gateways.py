# vejoias/infrastructure/gateways.py

import os
import requests
import uuid
from decouple import config
from decimal import Decimal
from django.conf import settings
from django.core.mail import send_mail
from typing import Protocol, List

from vejoias.core.entities import Pedido, Usuario, Endereco
from vejoias.core.exceptions import PagamentoFalhouError


# ====================================================================
# PROTOCOLOS: As interfaces que os gateways devem implementar.
# Reutilizamos as interfaces definidas na camada de 'use_cases'.
# ====================================================================

# Definido em vejoias/core/use_cases.py
class IGatewayPagamento(Protocol):
    def processar_pagamento_pix(self, valor: Decimal) -> str: ...
    def processar_pagamento_boleto(self, valor: Decimal) -> str: ...
    def processar_pagamento_cartao(self, valor: Decimal) -> str: ...

# ====================================================================
# GATEWAYS: Implementações concretas que se comunicam com APIs externas.
# ====================================================================

class MercadoPagoGateway(IGatewayPagamento):
    """
    Gateway para comunicação com a API de Pagamento do Mercado Pago.
    Implementa a interface IGatewayPagamento.
    """
    def __init__(self):
        # A chave de API deve ser lida de um arquivo .env para segurança
        self.api_base_url = "https://api.mercadopago.com/v1"
        self.access_token = os.environ.get("MERCADO_PAGO_ACCESS_TOKEN")
        
        if not self.access_token:
            raise ValueError("MERCADO_PAGO_ACCESS_TOKEN")

    def processar_pagamento_pix(self, valor: Decimal) -> str:
        """Processa um pagamento via Pix."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Indepotence-Key": str(uuid.uuid4()),  # Para evitar duplicidade
        }
        payload = {
            "transaction_amount": float(valor),
            "payment_method_id": "pix",
            "description": "Pagamento de jóias - Vê Jóias",
            "payer": {
                "email": " ",
                "first_name": " ",
                "last_name": " ",  # Exemplo, deve ser o email do comprador
                "identification": {
                    "type": "CPF",
                    "number": " ",  # Exemplo, deve ser o CPF do comprador
                }
            },
        }
        
        try:
            # Esta é uma chamada de API fictícia.
            response = requests.post(f"{self.api_base_url}/v1/payments", json=payload, headers=headers)
            response.raise_for_status()  # Levanta um erro para códigos de status HTTP 4xx/5xx
            
            data = response.json()
            # Lógica para verificar o status e obter o ID da transação
            if data.get("status") == "approved":
                return data.get("id")
            else:
                raise PagamentoFalhouError(f"Pagamento Pix recusado. Status: {data.get('status')}")

        except requests.exceptions.RequestException as e:
            raise PagamentoFalhouError(f"Erro de conexão com a API do Mercado Pago: {e}")
        except Exception as e:
            raise PagamentoFalhouError(f"Falha inesperada no processamento de Pix: {e}")
        
    def processar_pagamento_boleto(self, valor: Decimal, usuario: Usuario, endereco: Endereco) -> tuple[str, str]:
        """Processa um pagamento via Boleto."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Indepotence-Key": str(uuid.uuid4()),  # Para evitar duplicidade
        }
        payload = {
            "transaction_amount": float(valor),
            "payment_method_id": "bolbradesco",
            "description": "Pagamento de jóias - Vê Jóias",
            "payer": {
                # Preencha com os dados do Usuário (Assumindo que o nome completo está no model)
                "first_name": usuario.nome.split()[0] if usuario.nome else "Comprador",
                "last_name": usuario.nome.split()[-1] if usuario.nome and len(usuario.nome.split()) > 1 else "Vê Jóias", 
                "email": usuario.email,
                "identification": {
                    "type": "CPF",
                    # O CPF DEVE VIR NO MODELO DE USUÁRIO. Assumimos que existe 'usuario.cpf'.
                    "number": usuario.cpf if hasattr(usuario, 'cpf') else "11111111111", 
                },
                "address": {
                    "zip_code": endereco.cep.replace('-', ''),
                    "street_name": endereco.linha1,
                    "street_number": "s/n", # Pode ser melhorado
                    "neighborhood": endereco.bairro if hasattr(endereco, 'bairro') else "Centro",
                    "city": endereco.cidade,
                    "federal_unit": endereco.estado
                },
            },
        }
        
        try:
            response = requests.post(f"{self.api_base_url}/v1/payments", json=payload, headers=headers)
            response.raise_for_status()  
            
            data = response.json()
            
            # 1. Confirma se o Boleto foi criado (status PENDENTE)
            if data.get("status") in ["pending", "in_process"]:
                transacao_id = data.get("id")
                
                # 2. Extrai a URL do Boleto/Pix
                # O link de pagamento do Boleto/Pix geralmente está em 'external_resource_url' ou 'ticket_url'
                url_pagamento = data.get("transaction_details", {}).get("external_resource_url", "")
                
                if not url_pagamento:
                    # Segunda tentativa, caso o campo mude dependendo da conta
                    url_pagamento = data.get("point_of_interaction", {}).get("transaction_data", {}).get("ticket_url", "")
                    
                if not url_pagamento:
                    # ESSENCIAL: Se não há link, a transação não pode ser concluída pelo cliente
                    raise PagamentoFalhouError("Boleto/Pix gerado, mas o link de pagamento não foi encontrado na resposta do Mercado Pago.")

                # RETORNA A TUPLA DE ID E URL
                return transacao_id, url_pagamento 
            else:
                raise PagamentoFalhouError(f"Criação do pagamento recusada. Status: {data.get('status')}")

        except requests.exceptions.RequestException as e:
            raise PagamentoFalhouError(f"Erro de conexão com a API do Mercado Pago: {e}")
        except Exception as e:
            raise PagamentoFalhouError(f"Falha inesperada no processamento de Boleto/Pix: {e}")

    def processar_pagamento_cartao(self, valor: Decimal) -> str:
        """
        Processa um pagamento via cartão de crédito.
        Atenção: A lógica real envolve tokenização de cartão no frontend.
        """
        headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.MERCADO_PAGO_ACCESS_TOKEN}",
                }
        card_data = {
            "card_number": " ",
            "expiration_month": " ",
            "expiration_year": " ",
            "security_code": " ",
            "cardholder": {
                "name": "name_exemple",
                "identification": {
                    "type": "CPF",
                    "number": " ",  # Exemplo, deve ser o CPF do comprador
                }
            },
        }  

        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            
        }
        payload = {
            "transaction_amount": float(valor),
            "description": "Pagamento de jóias - Vê Jóias",
            "token": card_data,  # Token do cartão obtido no frontend
            "installments": 1,
            "payer": {
                "email": " ",
                "identification": {
                    "type": "CPF",
                    "number": " ",  # Exemplo, deve ser o CPF do comprador
                },  
            }
        }

        try:
            # Esta é uma chamada de API fictícia.
            response = requests.post(f"{self.api_base_url}/v1/card_tokens", json=payload, headers=headers)
            response.raise_for_status()
            
            data = response.json()
            if data.get("status") == "approved":
                return data.get("id")
            else:
                raise PagamentoFalhouError(f"Pagamento Cartão recusado. Status: {data.get('status')}")

        except requests.exceptions.RequestException as e:
            raise PagamentoFalhouError(f"Erro de conexão com a API do Mercado Pago: {e}")
        except Exception as e:
            raise PagamentoFalhouError(f"Falha inesperada no processamento de Cartão: {e}")
        
    def buscar_status_transacao(self, transacao_id: str) -> str:
        """
        Busca o status atual de uma transação (pagamento) no Mercado Pago.
        """
        headers = {
            "Authorization": f"Bearer {self.access_token}",
        }
        
        # O Mercado Pago usa /v1/payments/{id} para buscar o status de um pagamento
        url = f"{self.api_base_url}/v1/payments/{transacao_id}"
        
        try:
            response = requests.get(url, headers=headers)
            response.raise_for_status() 
            
            data = response.json()
            # Retorna o status da transação (ex: 'approved', 'pending', 'rejected')
            return data.get("status")
            
        except requests.exceptions.RequestException as e:
            # Levanta uma exceção para ser capturada pelo Use Case
            raise Exception("Falha ao buscar status da transação.")


class GroqGateway:
    """Gateway para comunicação com a API da Groq para o chatbot."""
    def __init__(self):
        self.api_key = os.environ.get("GROQ_API_KEY")
        self.base_url = "https://api.groq.com/openai/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def perguntar_ao_chatbot(self, prompt: str) -> str:
        """Envia um prompt para o chatbot e retorna a resposta."""
        payload = {
            "model": "llama3-8b-8192",  # Exemplo de modelo
            "messages": [{"role": "user", "content": prompt}],
            # ... outros parâmetros
        }
        
        try:
            response = requests.post(f"{self.base_url}/chat/completions", json=payload, headers=self.headers)
            response.raise_for_status()
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
        except requests.exceptions.RequestException as e:
            # Adicionar exceção customizada para falha de IA se necessário
            raise Exception(f"Erro de conexão com a API da Groq: {e}")


class EvolutionAPIGateway:
    """Gateway para automação de mensagens no WhatsApp via EvolutionAPI."""
    
    def __init__(self):
        # Lendo configurações do settings.py
        self.api_key = settings.EVOLUTION_API_KEY
        self.instance_name = settings.EVOLUTION_INSTANCE_NAME
        self.base_url = settings.EVOLUTION_API_URL
        
        # O self.headers deve ser definido aqui, usando o api_key lido
        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }

    def enviar_confirmacao_pedido(self, pedido: Pedido, numero_telefone: str) -> bool:
        """Envia uma mensagem de confirmação de pedido via WhatsApp."""

        if not self.api_key or not self.instance_name:
            print("AVISO: Chave da Evolution-API ou nome da instância não configurados.")
            return False

        mensagem = (
            f"🎉 Pedido {pedido.id} confirmado na Vê Jóias! 🎉\n\n"
            f"Total: R$ {pedido.total:.2f}\n"
            f"Obrigado por comprar conosco!"
        )

        payload = {
            "number": numero_telefone,
            "options": {"delay": 1200, "presence": "typing"},
            "textMessage": {"text": mensagem}
        }
        
        try:
            # Endpoint corrigido para o padrão Evolution: {base_url}/{instance}/message/sendText
            response = requests.post(
                f"{self.base_url}/{self.instance_name}/message/sendText",
                json=payload,
                headers=self.headers,
                timeout=5
            )
            response.raise_for_status() # Levanta erro para 4xx e 5xx
            
            # Retorna True se a API retornar sucesso (geralmente 200/201)
            return response.status_code in [200, 201]
            
        except requests.exceptions.RequestException as e:
            # É bom registrar o erro, mas retornar False para não quebrar o fluxo de checkout
            print(f"ERRO EvolutionAPI: Falha ao enviar mensagem de pedido {pedido.id}: {e}")
            return False


class EmailServiceGateway:
    """Gateway para envio de e-mails usando o sistema de e-mail do Django."""

    def enviar_confirmacao_pedido(self, pedido: Pedido) -> bool:
        """
        Envia um e-mail de confirmação do pedido para o cliente.
        
        :param pedido: Entidade Pedido com os dados necessários.
        :return: True se o envio for bem-sucedido (ou aceito pelo backend), False caso contrário.
        """
        
        # O destinatário deve ser o e-mail do usuário no pedido
        destinatario = pedido.usuario.email 
        
        assunto = f"Confirmação do Pedido #{pedido.id} na Vê Jóias"
        
        # Corpo do E-mail (versão texto simples)
        mensagem = (
            f"Olá {pedido.usuario.email},\n\n"
            f"Seu pedido #{pedido.id} foi recebido e está sendo processado.\n"
            f"O valor total é de R$ {pedido.total:.2f}.\n\n"
            f"Você pode acompanhar o status do seu pedido em nosso site.\n\n"
            f"Obrigado por comprar na Vê Joias!"
        )
        
        # Remetente padrão (definido no settings.py ou variável de ambiente)
        remetente = settings.DEFAULT_FROM_EMAIL if hasattr(settings, 'DEFAULT_FROM_EMAIL') else 'noreply@vejoias.com'

        try:
            # send_mail é uma função síncrona, mas o uso do backend de console ou
            # de um backend real (ex: SendGrid, SMTP) é definido no settings.py.
            
            # Nota: O Django envia o e-mail para o console no modo de desenvolvimento.
            send_mail(
                assunto,
                mensagem,
                remetente,
                [destinatario],
                fail_silently=False, # Levanta exceção em caso de falha no envio
            )
            return True
            
        except Exception as e:
            # O Use Case já tem um try/except, mas é bom logar aqui também.
            print(f"ERRO: Falha ao enviar e-mail de confirmação do pedido {pedido.id}: {e}")
            return False
