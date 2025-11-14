.PHONY: help bndes-start bndes-stop bndes-pipeline bndes-setup bndes-status bndes-restart clean logs dev

# Variáveis
COMPOSE_FILE = docker-compose.yml
PROJECT_NAME = bndes_project

# Cores para output
RED = \033[0;31m
GREEN = \033[0;32m
YELLOW = \033[1;33m
BLUE = \033[0;34m
NC = \033[0m # No Color

# Comando padrão
help: ## Mostra esta ajuda
	@echo "$(BLUE)BNDES Data Pipeline Project$(NC)"
	@echo ""
	@echo "$(YELLOW)Comandos principais:$(NC)"
	@echo "  $(GREEN)bndes-start$(NC)     Inicia infraestrutura BNDES completa"
	@echo "  $(GREEN)bndes-pipeline$(NC)  Executa pipeline de dados (extração + transformação)"
	@echo "  $(GREEN)bndes-stop$(NC)      Para toda a infraestrutura"
	@echo "  $(GREEN)bndes-status$(NC)    Status dos serviços BNDES"
	@echo "  $(GREEN)entrypoint-logs$(NC) Logs específicos do entrypoint (nova funcionalidade)"
	@echo ""
	@echo "$(YELLOW)Todos os comandos:$(NC)"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-18s$(NC) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Uso típico:$(NC)"
	@echo "  1. $(GREEN)make bndes-start$(NC)    # Sobe infraestrutura + configura automático"
	@echo "  2. $(GREEN)make bndes-pipeline$(NC) # Executa pipeline de dados"
	@echo "  3. Acesse http://localhost:3000 (Metabase)"

bndes-start: ## Inicia infraestrutura BNDES completa (recomendado)
	@echo "$(BLUE)Iniciando infraestrutura BNDES...$(NC)"
	@docker compose -f $(COMPOSE_FILE) down 2>/dev/null || true
	@echo "$(YELLOW)📦 Subindo containers BNDES...$(NC)"
	@docker compose -f $(COMPOSE_FILE) up -d
	@echo "$(YELLOW)⏳ Aguardando serviços inicializarem...$(NC)"
	@sleep 30
	@$(MAKE) bndes-setup
	@echo ""
	@echo "$(GREEN)✅ Infraestrutura BNDES pronta!$(NC)"
	@echo "$(YELLOW)🌐 Serviços disponíveis:$(NC)"
	@echo "  • Airflow:  http://localhost:8080 (airflow/airflow)"
	@echo "  • Metabase: http://localhost:3000 (bndes_data@student.com/bndes_data123)"
	@echo "  • MinIO:    http://localhost:9001 (minioadmin/minioadmin123)"

bndes-stop: ## Para toda a infraestrutura BNDES
	@echo "$(YELLOW)🛑 Parando infraestrutura BNDES...$(NC)"
	@docker compose -f $(COMPOSE_FILE) down
	@echo "$(YELLOW)Parando containers Metabase e MinIO restantes...$(NC)"
	@docker stop $$(docker ps -q --filter "name=metabase" 2>/dev/null) $$(docker ps -q --filter "name=minio" 2>/dev/null) 2>/dev/null || true
	@docker rm $$(docker ps -aq --filter "name=metabase" 2>/dev/null) $$(docker ps -aq --filter "name=minio" 2>/dev/null) 2>/dev/null || true
	@echo "$(GREEN)✅ Infraestrutura BNDES parada$(NC)"

bndes-pipeline: ## Executa pipeline completo de dados BNDES
	@echo "$(BLUE)🔄 Executando pipeline de dados BNDES...$(NC)"
	@echo "$(YELLOW)1. Executando extração de dados BNDES...$(NC)"
	@curl -s -X POST -u airflow:airflow "http://localhost:8080/api/v1/dags/bndes_extraction/dagRuns" \
		-H "Content-Type: application/json" \
		-d '{"dag_run_id":"manual_$$(date +%Y%m%d_%H%M%S)", "conf":{}}' > /dev/null || echo "$(RED)Erro na extração$(NC)"
	@sleep 10
	@echo "$(YELLOW)2. Executando transformação e carga...$(NC)"
	@curl -s -X POST -u airflow:airflow "http://localhost:8080/api/v1/dags/bndes_transformation/dagRuns" \
		-H "Content-Type: application/json" \
		-d '{"dag_run_id":"manual_$$(date +%Y%m%d_%H%M%S)", "conf":{}}' > /dev/null || echo "$(RED)Erro na transformação$(NC)"
	@echo "$(GREEN)✅ Pipeline BNDES executado! Acompanhe em http://localhost:8080$(NC)"

bndes-setup: ## Configura Metabase automaticamente para BNDES
	@echo "$(BLUE)🔧 Configurando Metabase para BNDES...$(NC)"
	@echo "$(YELLOW)⏳ Aguardando Metabase estar disponível...$(NC)"
	@timeout=120; \
	while [ $$timeout -gt 0 ] && ! curl -s http://localhost:3000/api/health > /dev/null 2>&1; do \
		sleep 5; \
		timeout=$$((timeout-5)); \
	done
	@if ! curl -s http://localhost:3000/api/health > /dev/null 2>&1; then \
		echo "$(RED)❌ Metabase não está disponível$(NC)"; \
		exit 1; \
	fi
	@echo "$(GREEN)✅ Metabase está rodando!$(NC)"
	@echo "$(YELLOW)Configuração manual necessária:$(NC)"
	@echo "  • Acesse: http://localhost:3000"
	@echo "  • Email: bndes_data@student.com"
	@echo "  • Senha: bndes_data123"
	@echo "  • Adicione banco PostgreSQL:"
	@echo "    - Host: bndes_postgres"
	@echo "    - Porta: 5432"
	@echo "    - Database: bndes_data"
	@echo "    - User: bndes_user"
	@echo "    - Senha: bndes_password"

bndes-status: ## Status completo da infraestrutura BNDES
	@echo "$(BLUE)📊 Status da infraestrutura BNDES:$(NC)"
	@docker compose -f $(COMPOSE_FILE) ps
	@echo ""
	@echo "$(BLUE)🌐 Status dos serviços BNDES:$(NC)"
	@echo -n "  Airflow:  "
	@curl -s http://localhost:8080/health > /dev/null && echo "$(GREEN)✅ Online$(NC)" || echo "$(RED)❌ Offline$(NC)"
	@echo -n "  Metabase: "
	@curl -s http://localhost:3000/api/health > /dev/null && echo "$(GREEN)✅ Online$(NC)" || echo "$(RED)❌ Offline$(NC)"
	@echo -n "  MinIO:    "
	@curl -s http://localhost:9001 > /dev/null && echo "$(GREEN)✅ Online$(NC)" || echo "$(RED)❌ Offline$(NC)"

bndes-restart: ## Reinicia toda a infraestrutura BNDES
	@echo "$(YELLOW)🔄 Reiniciando infraestrutura BNDES...$(NC)"
	@$(MAKE) bndes-stop
	@sleep 5
	@$(MAKE) bndes-start

bndes-data: ## Verifica dados BNDES carregados no PostgreSQL
	@echo "$(BLUE)📊 Verificando dados BNDES no PostgreSQL:$(NC)"
	@docker exec bndes_postgres psql -U bndes_user -d bndes_data -c "SELECT COUNT(*) as total_registros FROM desembolsos_por_uf;" 2>/dev/null || echo "$(RED)❌ Tabela não encontrada$(NC)"
	@docker exec bndes_postgres psql -U bndes_user -d bndes_data -c "SELECT uf, COUNT(*) as registros FROM desembolsos_por_uf GROUP BY uf ORDER BY uf LIMIT 10;" 2>/dev/null || true

# Comandos genéricos
clean: ## Remove tudo - reset completo do projeto
	@echo "$(RED)🧹 Limpeza completa do projeto BNDES...$(NC)"
	@docker compose -f $(COMPOSE_FILE) down -v --remove-orphans
	@docker volume rm $(PROJECT_NAME)_metabase_data $(PROJECT_NAME)_metabase_postgres_data 2>/dev/null || true
	@docker volume rm $(PROJECT_NAME)_postgres_data $(PROJECT_NAME)_airflow_postgres_data 2>/dev/null || true
	@docker volume rm $(PROJECT_NAME)_minio_data $(PROJECT_NAME)_airflow_logs 2>/dev/null || true
	@docker image rm metabase/metabase:latest 2>/dev/null || true
	@echo "$(GREEN)✅ Limpeza concluída$(NC)"

logs: ## Logs em tempo real dos serviços principais
	@echo "$(BLUE)📋 Logs da infraestrutura BNDES:$(NC)"
	@docker compose -f $(COMPOSE_FILE) logs --tail=50 -f airflow-webserver airflow-scheduler bndes_metabase bndes_postgres

entrypoint-logs: ## Logs específicos do entrypoint (nova funcionalidade)
	@echo "$(BLUE)Logs do entrypoint do Airflow:$(NC)"
	@docker compose -f $(COMPOSE_FILE) logs airflow-webserver | grep "✅\|❌\|⏳\|🔍\|🗄️\|👤\|🏊\|🔧"

dev: ## Modo desenvolvimento - sobe com logs em tempo real
	@echo "$(BLUE)🛠️ Modo desenvolvimento BNDES - logs em tempo real$(NC)"
	@docker compose -f $(COMPOSE_FILE) up

build: ## Reconstrói imagens do Airflow (desenvolvimento)
	@echo "$(YELLOW)🔨 Reconstruindo imagem do Airflow...$(NC)"
	@docker compose -f $(COMPOSE_FILE) build --no-cache

reset: clean bndes-start ## Reset completo - limpa tudo e reinicia

# Atalhos para desenvolvimento
airflow: ## Acessa bash do container Airflow
	@docker exec -it airflow_webserver bash

postgres: ## Acessa psql do PostgreSQL BNDES
	@docker exec -it bndes_postgres psql -U bndes_user -d bndes_data

minio: ## Informações do MinIO BNDES
	@echo "$(BLUE)MinIO Console BNDES: http://localhost:9001$(NC)"
	@echo "$(YELLOW)User: minioadmin | Password: minioadmin123$(NC)"

 