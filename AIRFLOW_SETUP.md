# 🚀 AIRFLOW - PIPELINE BNDES

## 📋 O que foi implementado

### ✅ **Infraestrutura Completa**
- **Airflow 2.8.1** com executor Celery (produção-ready)
- **PostgreSQL** dedicado para metadados do Airflow
- **Redis** para broker de mensagens
- **MinIO** integrado para logs remotos
- **Remote logging** configurado (logs salvos no MinIO, não local)

### ✅ **DAGs Implementadas**
- **bndes_data_extraction**: Pipeline diário de extração de dados do BNDES

### ✅ **Conexões Configuradas**
- **minio_s3**: Conexão com MinIO para logs e dados
- **bndes_postgres**: Conexão com PostgreSQL (para futura integração)

## 🏗️ **Arquitetura Atual**

```
API BNDES → Airflow DAGs → MinIO (Data Lake + Logs) → [Futuro: PostgreSQL + Metabase]
```

### **Componentes:**
- **airflow-webserver**: Interface web (http://localhost:8080)
- **airflow-scheduler**: Agendador de DAGs
- **airflow-worker**: Executor de tasks
- **airflow-postgres**: Banco de metadados
- **redis**: Broker para Celery

## 🚀 **Como usar**

### **1. Subir toda a infraestrutura:**
```bash
# Build da imagem customizada e inicialização
docker-compose up -d

# Verificar logs da inicialização (importante!)
docker-compose logs airflow-init

# Aguardar todos os serviços subirem (~2-3 minutos)
docker-compose ps
```

### **2. Acessar o Airflow:**
- **URL**: http://localhost:8080
- **Usuário**: `admin`
- **Senha**: `admin`

### **3. Verificar se a DAG apareceu:**
1. Na interface, procure por "**bndes_data_extraction**"
2. Ative a DAG (toggle ON)
3. Clique em "Trigger DAG" para executar manualmente

### **4. Monitorar execução:**
- **Graph View**: Visualizar pipeline
- **Logs**: Ver detalhes de cada task
- **Grid View**: Histórico de execuções

## 📊 **Logs e Monitoramento**

### **Logs Remotos no MinIO:**
- ✅ **Logs do Airflow** salvos em: `s3://airflow-logs`
- ✅ **Dados BNDES** salvos em: `s3://bndes-data`
- ✅ **Interface MinIO**: http://localhost:9001

### **Comandos úteis:**
```bash
# Ver logs em tempo real
docker-compose logs -f airflow-scheduler
docker-compose logs -f airflow-worker

# Reiniciar serviços específicos
docker-compose restart airflow-webserver
docker-compose restart airflow-scheduler

# Acessar container para debug
docker-compose exec airflow-webserver bash
```

## 🔧 **Configuração da DAG**

### **bndes_data_extraction**
- **Frequência**: Diária (`@daily`)
- **Horário**: 00:00 UTC
- **Retry**: 2 tentativas com 5min de intervalo
- **Tasks**:
  1. `extract_bndes_data`: Extrai dados da API
  2. `validate_data_quality`: Valida qualidade dos dados

### **Personalizar DAG:**
Edite: `dags/bndes_extraction_dag.py`

```python
# Alterar frequência
schedule_interval='@weekly'  # ou '0 6 * * *' para 6h da manhã

# Adicionar mais validações
def validate_data_quality(**context):
    # Suas validações customizadas aqui
    pass
```

## 🛠️ **Troubleshooting**

### **DAG não aparece:**
```bash
# Verificar erros de sintaxe
docker-compose exec airflow-webserver airflow dags list

# Verificar logs do scheduler
docker-compose logs airflow-scheduler
```

### **Logs não aparecem no MinIO:**
```bash
# Verificar conexão minio_s3
docker-compose exec airflow-webserver airflow connections list

# Testar conexão manualmente
docker-compose exec airflow-webserver python -c "
import boto3
s3 = boto3.client('s3', endpoint_url='http://minio:9000', 
                  aws_access_key_id='minioadmin', 
                  aws_secret_access_key='minioadmin123')
print(s3.list_buckets())
"
```

### **Erro de extração:**
1. Verificar se MinIO está rodando
2. Verificar configuração em `config/config.yml`
3. Testar script manualmente: `python bndes_data_explorer.py`

## 🎯 **Próximos Passos**

1. **Incremental Loading**: Implementar updates incrementais
2. **Data Transformation**: DAGs para transformação de dados  
3. **PostgreSQL Integration**: Pipeline MinIO → PostgreSQL
4. **Metabase**: Dashboards automáticos
5. **Monitoring & Alerts**: Email/Slack notifications

## 📞 **Suporte**

- **Interface Airflow**: http://localhost:8080
- **Interface MinIO**: http://localhost:9001  
- **PostgreSQL**: localhost:5432
- **Logs**: `docker-compose logs [service-name]` 