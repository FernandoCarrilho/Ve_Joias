# vejoias/infrastructure/gateways.py

import os
import requests
from decimal import Decimal
from typing import Protocol, List

from core.exceptions import PagamentoFalhouError

# ====================================================================
# PROTOCOLOS: As interfaces que os gateways devem implementar.
# Reutilizamos as interfaces definidas na camada de 'use_cases'.
# ====================================================================

# Definido em vejoias/core/use_cases.py
class IGatewayPagamento(Protocol):
    def processar_pagamento_pix(self, valor: Decimal) -> str: ...
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
            raise ValueError("MERCADO_PAGO_ACCESS_TOKEN não configurado no .env")

    def processar_pagamento_pix(self, valor: Decimal) -> str:
        """Processa um pagamento via Pix."""
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "transaction_amount": float(valor),
            "payment_method_id": "pix",
            "description": "Pagamento de jóias - Vê Jóias",
            # ... outros campos necessários pela API do Mercado Pago
        }
        
        try:
            # Esta é uma chamada de API fictícia.
            response = requests.post(f"{self.api_base_url}/payments", json=payload, headers=headers)
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

    def processar_pagamento_cartao(self, valor: Decimal) -> str:
        """
        Processa um pagamento via cartão de crédito.
        Atenção: A lógica real envolve tokenização de cartão no frontend.
        """
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
        payload = {
            "transaction_amount": float(valor),
            "payment_method_id": "visa", # Exemplo
            "description": "Pagamento de jóias - Vê Jóias",
            # ... campos de tokenização de cartão
        }

        try:
            # Esta é uma chamada de API fictícia.
            response = requests.post(f"{self.api_base_url}/payments", json=payload, headers=headers)
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
        self.api_key = os.environ.get("EVOLUTION_API_KEY")
        self.instance_name = os.environ.get("EVOLUTION_INSTANCE_NAME")
        self.base_url = "https://api.evolution.com"
        
        self.headers = {
            "apikey": self.api_key,
            "Content-Type": "application/json"
        }

    def enviar_mensagem_whatsapp(self, numero_telefone: str, mensagem: str) -> bool:
        """Envia uma mensagem de texto para um número de WhatsApp."""
        payload = {
            "number": numero_telefone,
            "options": {"delay": 1200},
            "textMessage": {"text": mensagem}
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/message/sendText/{self.instance_name}",
                json=payload,
                headers=self.headers
            )
            response.raise_for_status()
            
            return response.status_code == 200
        except requests.exceptions.RequestException as e:
            raise Exception(f"Erro ao enviar mensagem via EvolutionAPI: {e}")
