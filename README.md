# BNDES Data Pipeline

Pipeline de dados automatizado para extração, transformação e visualização de dados do BNDES (Banco Nacional de Desenvolvimento Econômico e Social).

## 📋 Visão Geral

Este projeto implementa um pipeline de dados completo que:
- **Extrai** dados da API do BNDES
- **Armazena** no MinIO (Data Lake)
- **Transforma** os dados usando Airflow
- **Carrega** no PostgreSQL
- **Visualiza** através do Metabase

## 🏗️ Arquitetura

```
API BNDES → Airflow → MinIO (Data Lake) → PostgreSQL → Metabase (BI)
```

### Componentes:
- **Airflow**: Orquestração dos pipelines de dados
- **PostgreSQL**: Banco de dados para dados processados
- **MinIO**: Data Lake para armazenamento de dados brutos
- **Metabase**: Interface de BI para dashboards e visualizações

## Início Rápido

### Pré-requisitos
- Docker & Docker Compose
- Make (presente na maioria dos sistemas Linux/Mac)

### 1. Subir toda a infraestrutura
```bash
make bndes-start
```
Este comando irá:
- Subir todos os containers necessários
- Configurar automaticamente o Airflow
- Configurar o Metabase
- Deixar tudo pronto para uso

### 2. Executar pipeline de dados
```bash
make bndes-pipeline
```
Este comando extrai dados do BNDES e carrega no PostgreSQL.

### 3. Acessar os serviços
- **Metabase**: http://localhost:3000
  - Email: `bndes_data@student.com`
  - Senha: `bndes_data123`
  - **Conexão PostgreSQL BNDES** (adicionar como fonte de dados):
    - Host: `bndes_postgres`
    - Porta: `5432`
    - Database: `bndes_data`
    - User: `bndes_user`
    - Password: `bndes_password`
- **Airflow**: http://localhost:8080
  - Usuário: `airflow`
  - Senha: `airflow`
- **MinIO**: http://localhost:9001
  - Usuário: `minioadmin`
  - Senha: `minioadmin123`

## 📋 Comandos Disponíveis

Execute `make help` para ver todos os comandos:

### Comandos Principais
- `make bndes-start` - Inicia infraestrutura completa
- `make bndes-stop` - Para toda a infraestrutura
- `make bndes-pipeline` - Executa pipeline de dados completo
- `make bndes-status` - Status dos serviços
- `make bndes-restart` - Reinicia toda a infraestrutura
- `make bndes-data` - Verifica dados carregados no PostgreSQL

### Comandos de Desenvolvimento
- `make logs` - Logs em tempo real dos serviços
- `make clean` - Remove tudo (reset completo)
- `make dev` - Modo desenvolvimento (logs em tempo real)
- `make build` - Reconstrói imagens do Airflow
- `make entrypoint-logs` - Logs específicos do sistema de inicialização

### Atalhos Úteis
- `make airflow` - Acessa bash do container Airflow
- `make postgres` - Acessa psql do PostgreSQL
- `make minio` - Informações do MinIO

## 📊 Dados Disponíveis

Após executar o pipeline, você terá acesso à tabela `desembolsos_por_uf` com:
- **~9.751 registros** de desembolsos por UF
- **Período**: 1995-2025
- **Granularidade**: Mensal por estado brasileiro
- **Campos**: ano, mês, período, UF, valor_desembolso

## 🔧 Desenvolvimento

### Estrutura do Projeto
```
bndes_project/
├── dags/                     # DAGs do Airflow
│   ├── bndes_extraction_dag.py
│   └── bndes_transformation_dag.py
├── config/                   # Configurações
├── libs/                     # Bibliotecas compartilhadas
├── docker compose.yml        # Infraestrutura
├── Dockerfile                # Imagem customizada do Airflow
├── entrypoint.py             # Script de inicialização automática
├── Makefile                  # Automação
└── README.md
```

### Modificar DAGs
As DAGs estão em `dags/`:
- `bndes_extraction_dag.py` - Extração da API
- `bndes_transformation_dag.py` - Transformação e carga

Após modificar, execute:
```bash
make bndes-restart
```

### Debug
```bash
# Ver logs em tempo real
make logs

# Verificar status dos serviços
make bndes-status

# Verificar dados carregados
make bndes-data

# Acessar PostgreSQL diretamente
make postgres

# Ver logs do sistema de inicialização
make entrypoint-logs
```

## 🐛 Solução de Problemas

### Metabase formata nomes de tabelas e colunas automaticamente

**Problema**: O Metabase converte automaticamente nomes em snake_case (ex: `desembolsos_por_uf`) para formato "Title Case" com espaços (ex: "Desembolsos Por Uf").

**Solução**:
1. Acesse o Metabase: http://localhost:3000
2. Vá em **Configurações** → **Admin** → **Tabelas, Raios X e Domínios**
3. Desabilite a flag **"Nomes amigáveis de tabelas e campos"**
4. Altere o valor de **"Substitua sublinhados e traços por espaços"** para **"Desabilitado"**

Isso manterá os nomes originais das tabelas e colunas em snake_case.

### Metabase não mostra dados
```bash
make bndes-setup
```

### DAGs com erro
```bash
make logs
# Verifique os logs do Airflow
```

### Reset completo
```bash
make clean
make bndes-start
```

### Portas em uso
Certifique-se que as portas estão livres:
- 3000 (Metabase)
- 8080 (Airflow)
- 5432 (PostgreSQL)
- 9000/9001 (MinIO)

## 🔧 Configuração do Airflow

### DAGs Disponíveis

#### bndes_data_extraction
- **Frequência**: Diária (`@daily`)
- **Horário**: 00:00 UTC
- **Retry**: 2 tentativas com 5min de intervalo
- **Tasks**:
  1. `extract_bndes_data`: Extrai dados da API
  2. `validate_data_quality`: Valida qualidade dos dados

### Personalizar DAGs
Edite: `dags/bndes_extraction_dag.py`

```python
# Alterar frequência
schedule_interval='@weekly'  # ou '0 6 * * *' para 6h da manhã

# Adicionar mais validações
def validate_data_quality(**context):
    # Suas validações customizadas aqui
    pass
```

### Troubleshooting

#### DAG não aparece:
```bash
# Verificar erros de sintaxe
docker compose exec airflow-webserver airflow dags list

# Verificar logs do scheduler
docker compose logs airflow-scheduler
```

#### Logs não aparecem no MinIO:
```bash
# Verificar conexão minio_s3
docker compose exec airflow-webserver airflow connections list

# Testar conexão manualmente
docker compose exec airflow-webserver python -c "
import boto3
s3 = boto3.client('s3', endpoint_url='http://minio:9000', 
                  aws_access_key_id='minioadmin', 
                  aws_secret_access_key='minioadmin123')
print(s3.list_buckets())
"
```

#### Erro de extração:
1. Verificar se MinIO está rodando
2. Verificar configuração em `config/config.yml`
3. Testar script manualmente: `python bndes_data_explorer.py`

#### Problemas de inicialização:
```bash
# Ver logs do sistema de inicialização
make entrypoint-logs

# Verificar health checks
docker compose ps

# Rebuild se necessário
docker compose down -v
docker compose build
docker compose up
```

### Logs e Monitoramento

#### Logs Remotos no MinIO:
- **Logs do Airflow** salvos em: `s3://airflow-logs`
- **Dados BNDES** salvos em: `s3://bndes-data`
- **Interface MinIO**: http://localhost:9001

#### Comandos úteis para monitoramento:
```bash
# Ver logs em tempo real
docker compose logs -f airflow-scheduler
docker compose logs -f airflow-worker

# Reiniciar serviços específicos
docker compose restart airflow-webserver
docker compose restart airflow-scheduler

# Acessar container para debug
docker compose exec airflow-webserver bash
```

## 📈 Roadmap

- [ ] Dashboards pré-configurados no Metabase
- [ ] Alertas automáticos por email/Slack
- [ ] API para consulta de dados
- [ ] Testes automatizados
- [ ] CI/CD pipeline

## 🤝 Contribuição

1. Fork o projeto
2. Crie uma branch (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -m 'Add nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

## 📄 Licença

Este projeto está sob a licença MIT. Veja o arquivo `LICENSE` para detalhes.

## 🆘 Suporte

- **Issues**: Use o GitHub Issues para reportar bugs
- **Email**: lucasbrandao.finance@gmail.com
- **Documentação**: Este README e comentários no código 