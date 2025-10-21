# Use a imagem oficial do Python como base para o ambiente de construção
FROM python:3.11-slim AS builder

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Define o Python para não armazenar logs em buffer, tornando-os visíveis imediatamente
ENV PYTHONUNBUFFERED 1

# Instala ferramentas essenciais
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copia o arquivo de dependências
COPY requirements.txt .

# Instala as dependências do Python. O --no-cache-dir reduz o tamanho da imagem.
# Linha 18: Removida a instrução "&& pip install -e ."
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código da aplicação para o container
COPY . /app

# Comando de inicialização do servidor Gunicorn
# Nota: 'Ve_Joias' é o nome da pasta do seu projeto Django que contém o wsgi.py
CMD ["gunicorn", "Ve_Joias.wsgi:application", "--bind", "0.0.0.0:8000"]
