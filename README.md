# 💎 Vê Joias: E-commerce com Arquitetura Limpa e API RESTful

## 1. Sobre o Projeto

O **Vê Joias** é um sistema completo de e-commerce construído com Django, focado em demonstrar a aplicação prática da **Arquitetura Limpa (Clean Architecture)** e o desenvolvimento de uma **API RESTful** robusta. O projeto é totalmente contentorizado (Docker) e possui uma suíte completa de testes de unidade e integração.

## 2. Arquitetura

O projeto segue a **Arquitetura Limpa**, dividida em três camadas principais:

* **`core/` (Lógica de Negócio)**: Contém as **Entities** (Joia, Carrinho, Pedido) e os **Use Cases** (CriarPedido, AdicionarItemAoCarrinho). Esta camada é independente de frameworks e do banco de dados, sendo 100% testável com *Mocks*.
* **`infrastructure/` (Infraestrutura)**: Lida com a persistência de dados. Contém as implementações dos **Repositories** (JoiaRepository, CarrinhoRepository) usando Django ORM, Gateways de Pagamento (mocks) e serviços de e-mail.
* **`presentation/` (Apresentação)**: Contém as interfaces de usuário. Inclui as **Views** (web e API), **URLs**, **Serializers** e **Forms**. O front-end web é refatorado para consumir a própria API.

## 3. Tecnologias Utilizadas

* **Backend:** Python 3.11+
* **Framework:** Django 5.x
* **API:** Django REST Framework (DRF)
* **Autenticação API:** Simple JWT
* **Documentação API:** DRF Spectacular (Swagger/OpenAPI)
* **Database:** SQLite (Default, via Docker Volume)
* **Contêiner:** Docker e Docker Compose

## 4. Pré-requisitos

Para rodar o projeto, você precisa ter o **Docker** e o **Docker Compose** instalados na sua máquina.

## 5. Como Rodar o Projeto

Siga os passos abaixo para configurar e iniciar o ambiente de desenvolvimento:

1.  **Construir e Iniciar os Contêineres:**
    ```bash
    docker-compose up --build -d
    ```

2.  **Criar as Migrações do Banco de Dados:**
    ```bash
    docker-compose exec web python manage.py migrate
    ```

3.  **Criar um Superusuário (Admin):**
    É necessário um usuário administrador para acessar o painel e testar a API.
    ```bash
    docker-compose exec web python manage.py createsuperuser
    ```

4.  **Acesso:** O servidor estará disponível em:
    * **Loja:** `http://localhost:8000/`
    * **Admin Django:** `http://localhost:8000/admin/`

## 6. Testes Automatizados

O projeto possui uma suíte de testes dividida em Unitários e de Integração.

* **Rodar Todos os Testes:**
    ```bash
    docker-compose exec web python manage.py test
    ```

* **Rodar Apenas os Testes de Unidade (`core`):**
    ```bash
    docker-compose exec web python manage.py test vejoias.core.tests
    ```

* **Rodar Apenas os Testes de Integração (`infrastructure`):**
    ```bash
    docker-compose exec web python manage.py test vejoias.infrastructure.tests
    ```

## 7. Documentação da API

A documentação interativa da API está disponível nos seguintes endpoints:

* **Swagger UI:** `http://localhost:8000/api/schema/swagger-ui/`
* **Redoc:** `http://localhost:8000/api/schema/redoc/`

### Endpoints Chave da API:

| Rota | Método | Descrição | Permissão |
| :--- | :--- | :--- | :--- |
| `/api/joias/` | `GET` | Lista todos os produtos | Pública |
| `/api/carrinho/` | `GET`, `POST`, `DELETE` | Manipula o carrinho do usuário | Autenticado (JWT) |
| `/api/checkout/` | `POST` | Finaliza o pedido | Autenticado (JWT) |
| `/api/token/` | `POST` | Obtém o token JWT | Pública |

pip install pre-commit
pre-commit install
# testar em todos os arquivos (opcional)
pre-commit run --all-files

## Variáveis de Ambiente

O projeto usa variáveis de ambiente para segredos e configurações. Copie o arquivo de exemplo e ajuste:

```bash
cp .env.example .env
# edite .env conforme necessário


