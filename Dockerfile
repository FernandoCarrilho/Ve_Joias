# --- ESTÁGIO 1: O Construtor (Builder) ---
# Usamos 'AS builder' para nomear este estágio.
# Ele terá todas as ferramentas de build pesadas (gcc, etc).
FROM python:3.11-slim AS builder

# Define o diretório de trabalho
WORKDIR /app

# Define o Python para não armazenar logs em buffer
ENV PYTHONUNBUFFERED 1
# Desativa a criação de arquivos .pyc
ENV PYTHONDONTWRITEBYTECODE 1

# Instala as dependências de build do sistema operacional
# libpq-dev e gcc são necessários para compilar psycopg2
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copia apenas o requirements.txt para aproveitar o cache do Docker
COPY requirements.txt .

# Cria um ambiente virtual dentro do builder
RUN python -m venv /opt/venv

# Ativa o venv para os próximos comandos RUN
ENV PATH="/opt/venv/bin:$PATH"

# Instala as dependências Python dentro do venv
# Usamos --no-cache-dir para reduzir o tamanho
RUN pip install --no-cache-dir -r requirements.txt


# --- ESTÁGIO 2: A Imagem Final (Final) ---
# Começamos de uma imagem limpa. Ela não terá gcc ou libpq-dev.
FROM python:3.11-slim

# Define o diretório de trabalho
WORKDIR /app

# Define as mesmas ENVs
ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1

# Instala APENAS as dependências de RUNTIME do sistema
# libpq5 é a biblioteca de cliente do Postgres, necessária para rodar psycopg2.
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

# Copia o ambiente virtual que foi construído no estágio 'builder'
COPY --from=builder /opt/venv /opt/venv

# Ativa o venv para a imagem final
ENV PATH="/opt/venv/bin:$PATH"

# Cria um usuário não-root para rodar a aplicação (Boa prática de segurança)
RUN groupadd -r appgroup && useradd -r -g appgroup appuser

# Cria e configura os diretórios necessários
RUN mkdir -p /app/staticfiles /app/media
RUN chown -R appuser:appgroup /app /app/staticfiles /app/media
RUN chmod -R 755 /app/staticfiles /app/media

USER appuser

# Copia o código da aplicação (a última coisa, para otimizar o cache)
COPY . /app

# Expõe a porta que o Gunicorn vai usar
EXPOSE 8000

# Comando de inicialização do servidor Gunicorn
# Nota: 'vejoias' é o nome da pasta do seu projeto Django que contém o wsgi.py
# (Verifique se o nome "Ve_Joias" com 'V' maiúsculo está correto, Python é case-sensitive)
# Assumindo que o nome correto do módulo seja 'vejoias'.
CMD ["gunicorn", "vejoias.wsgi:application", "--bind", "0.0.0.0:8000"]
