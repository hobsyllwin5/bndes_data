FROM apache/airflow:2.8.1-python3.11

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV PIP_NO_CACHE_DIR=1

USER root

# Instalar dependências do sistema
RUN apt-get update && apt-get install -y \
    netcat-traditional \
    gcc \
    g++ \
    libpq-dev \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Copiar requirements
COPY requirements.txt ./

# Instalar dependências Python
RUN pip install --no-cache-dir -r requirements.txt

# Instalar providers do Airflow
RUN pip install --no-cache-dir \
    apache-airflow-providers-amazon==8.17.0 \
    apache-airflow-providers-postgres==5.10.0

# Copiar arquivos do projeto
COPY . .

# Configurar PYTHONPATH
ENV PYTHONPATH="/opt/airflow:${PYTHONPATH}"

# Definir entrypoint
ENTRYPOINT ["python", "entrypoint.py"] 