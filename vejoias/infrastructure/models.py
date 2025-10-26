# Define os modelos do banco de dados para a camada de infraestrutura (apenas autenticação).

from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.conf import settings
# Removido: importação de EnderecoEntity

# ====================================================================
# GERENCIADOR DE USUÁRIOS PERSONALIZADO (Para usar email como login)
# ====================================================================

class CustomUserManager(BaseUserManager):
    """
    Gerenciador de modelos de usuário onde o email é o identificador único
    para autenticação, em vez dos nomes de usuário.
    """
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('O e-mail deve ser definido')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Cria e salva um Superusuário com o e-mail e senha fornecidos.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        
        return self.create_user(email, password, **extra_fields)


# ====================================================================
# MODELO DE USUÁRIO
# ====================================================================

class Usuario(AbstractUser):
    """
    Modelo de Usuário Personalizado que utiliza o campo 'email' como identificador
    principal para login, em vez de 'username'.
    """
    # Remove o campo username padrão
    username = None 

    # Define o email como único e obrigatório
    email = models.EmailField('Endereço de E-mail', unique=True)
    
    # Campos adicionais do perfil
    telefone = models.CharField(max_length=15, blank=True, null=True)
    cpf = models.CharField('CPF', max_length=14, unique=True, blank=True, null=True)
    is_admin = models.BooleanField(default=False) 

    # Campos necessários para login/autenticação
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']

    # Utiliza o gerenciador de usuários personalizado
    objects = CustomUserManager()

    # Define related_name para grupos e permissões
    groups = models.ManyToManyField(
        'auth.Group',
        verbose_name='groups',
        blank=True,
        help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.',
        related_name="infra_user_set",
        related_query_name="infra_user",
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        verbose_name='user permissions',
        blank=True,
        help_text='Specific permissions for this user.',
        related_name="infra_user_set",
        related_query_name="infra_user",
    )

    class Meta:
        verbose_name = 'Usuário'
        verbose_name_plural = 'Usuários'
        db_table = 'infra_usuario' # Alterado o nome da tabela para especificidade

    def __str__(self):
        return self.email


class Endereco(models.Model):
    """
    Modelo para armazenar endereços de entrega e faturamento do usuário.
    Ligado a um usuário.
    """
    # Usamos settings.AUTH_USER_MODEL que será o modelo Usuario
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='infra_enderecos')
    apelido = models.CharField(max_length=50, help_text="Ex: Casa, Trabalho")
    cep = models.CharField(max_length=10, verbose_name="CEP")
    rua = models.CharField(max_length=255, verbose_name="Rua")
    numero = models.CharField(max_length=10, verbose_name="Número")
    complemento = models.CharField(max_length=100, blank=True, null=True, verbose_name="Complemento")
    bairro = models.CharField(max_length=100, verbose_name="Bairro")
    cidade = models.CharField(max_length=100, verbose_name="Cidade")
    estado = models.CharField(max_length=50, verbose_name="Estado")
    is_principal = models.BooleanField(default=False, verbose_name="Endereço Principal")

    class Meta:
        verbose_name = 'Endereço do Usuário'
        verbose_name_plural = 'Endereços do Usuário'
        db_table = 'usuario_endereco' # Tabela renomeada para refletir o domínio
        ordering = ['-is_principal', 'apelido']
        unique_together = ('usuario', 'apelido') # Garante apelidos únicos por usuário

    def __str__(self):
        # Assumindo que o settings.AUTH_USER_MODEL tem um método __str__ ou campo email
        user_info = str(self.usuario) if self.usuario else 'Usuário Desconhecido'
        return f"{user_info} - {self.apelido}"
    
    def formatar_endereco_texto(self):
        """Retorna o endereço completo como string."""
        complemento_str = f", {self.complemento}" if self.complemento else ""
        return f"{self.rua}, {self.numero}{complemento_str} - {self.bairro} - {self.cidade}/{self.estado} - CEP: {self.cep}"
