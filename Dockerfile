# vejoias/Dockerfile

# === ETAPA 1: BUILDER (Para instalar as dependências) ===
# Usa uma imagem Python oficial para garantir a consistência
FROM python:3.11-slim AS builder

# Define o diretório de trabalho dentro do contêiner
WORKDIR /app

# Copia o arquivo de dependências primeiro para aproveitar o cache do Docker
COPY requirements.txt .

# Instala as dependências do Python. O --no-cache-dir reduz o tamanho da imagem
RUN pip install --no-cache-dir -r requirements.txt

# === ETAPA 2: PRODUÇÃO (Para a imagem final) ===
# Usa a mesma imagem base para a consistência
FROM python:3.11-slim

# Define o mesmo diretório de trabalho
WORKDIR /app

# Copia as dependências já instaladas da etapa 'builder'
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Copia o código-fonte da aplicação para o contêiner
COPY . .

# Expõe a porta 8000 para a aplicação web
EXPOSE 8000

# Comando padrão para iniciar o servidor de desenvolvimento
# O CMD pode ser sobrescrito pelo docker-compose.yml
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
