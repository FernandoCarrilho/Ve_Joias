# vejoias/infrastructure/email_service.py

from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

class EmailService:
    def enviar_confirmacao_pedido(self, pedido):
        """
        Envia um e-mail de confirmação de pedido.
        Recebe a entidade Pedido.
        """
        subject = f"Confirmação de Pedido #{pedido.id} | Vê Jóias"
        to = pedido.usuario.email
        
        # Renderiza o conteúdo HTML do e-mail
        html_content = render_to_string('email/confirmacao_pedido.html', {'pedido': pedido})
        # Cria a versão de texto puro do e-mail para clientes que não suportam HTML
        text_content = strip_tags(html_content)
        
        # Cria e envia a mensagem
        email = EmailMultiAlternatives(subject, text_content, to=[to])
        email.attach_alternative(html_content, "text/html")
        email.send()

# Cria uma instância global do serviço para ser usada no use case
email_service = EmailService()
