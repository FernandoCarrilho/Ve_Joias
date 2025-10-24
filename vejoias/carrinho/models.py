from django.db import models

class Carrinho(models.Model):
    """Modelo de Carrinho de Compras.
    Pode ser expandido para incluir campos como cliente, data_criacao, etc.
    """
    
    # Adicione campos aqui conforme o desenvolvimento da sua aplicação.
    # Exemplo:
    # cliente = models.ForeignKey('auth.User', on_delete=models.CASCADE)
    
    class Meta:
        verbose_name = "Carrinho"
        verbose_name_plural = "Carrinhos"
        
    def __str__(self):
        return f"Carrinho #{self.pk}"
