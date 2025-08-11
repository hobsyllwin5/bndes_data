# 🚀 BNDES Data Pipeline

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

## 🚀 Início Rápido

### Pré-requisitos
- Docker & Docker Compose
- Make (presente na maioria dos sistemas Linux/Mac)

### 1. Subir toda a infraestrutura
```bash
make bndes-start
```
Este comando irá:
- Subir todos os containers BNDES
- Configurar o Metabase automaticamente
- Conectar ao banco BNDES
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
- **Airflow**: http://localhost:8080
  - Usuário: `admin`
  - Senha: `admin`
- **MinIO**: http://localhost:9001
  - Usuário: `minioadmin`
  - Senha: `minioadmin123`

## 📋 Comandos Disponíveis

Execute `make help` para ver todos os comandos:

### Comandos Principais BNDES
- `make bndes-start` - Inicia infraestrutura BNDES completa
- `make bndes-stop` - Para toda a infraestrutura BNDES
- `make bndes-pipeline` - Executa pipeline de dados completo
- `make bndes-status` - Status dos serviços BNDES
- `make bndes-restart` - Reinicia toda a infraestrutura
- `make bndes-data` - Verifica dados carregados no PostgreSQL

### Comandos de Desenvolvimento
- `make logs` - Logs em tempo real dos serviços
- `make clean` - Remove tudo (reset completo)
- `make dev` - Modo desenvolvimento (logs em tempo real)
- `make build` - Reconstrói imagens do Airflow

### Atalhos Úteis
- `make airflow` - Acessa bash do container Airflow
- `make postgres` - Acessa psql do PostgreSQL BNDES
- `make minio` - Informações do MinIO BNDES

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
├── docker-compose.yml        # Infraestrutura
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
```

## 🐛 Solução de Problemas

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
- **Email**: bndes_data@student.com
- **Documentação**: Este README e comentários no código 