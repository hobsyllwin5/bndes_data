#!/usr/bin/env python3
"""
Entrypoint script para inicialização automática do Airflow
Adaptado para o projeto BNDES com CeleryExecutor
"""

import os
import sys
import time
import subprocess
import psycopg2
import yaml
from pathlib import Path
from psycopg2 import OperationalError


def wait_for_postgres():
    """Aguardar PostgreSQL estar pronto."""
    print("⏳ Aguardando PostgreSQL...")
    
    host = os.getenv('AIRFLOW__DATABASE__SQL_ALCHEMY_HOST', 'airflow-postgres')
    database = os.getenv('AIRFLOW__DATABASE__SQL_ALCHEMY_DATABASE', 'airflow')
    user = os.getenv('AIRFLOW__DATABASE__SQL_ALCHEMY_USER', 'airflow')
    password = os.getenv('AIRFLOW__DATABASE__SQL_ALCHEMY_PASSWORD', 'airflow')
    
    max_retries = 30
    for attempt in range(max_retries):
        try:
            conn = psycopg2.connect(
                host=host,
                database=database,
                user=user,
                password=password
            )
            conn.close()
            print("✅ PostgreSQL está pronto!")
            return True
        except OperationalError:
            print(f"⏳ PostgreSQL não está pronto, aguardando... (tentativa {attempt + 1}/{max_retries})")
            time.sleep(2)
    
    print("❌ PostgreSQL falhou ao inicializar")
    return False


def wait_for_redis():
    """Aguardar Redis estar pronto."""
    print("⏳ Aguardando Redis...")
    
    host = os.getenv('AIRFLOW__CELERY__BROKER_HOST', 'redis')
    port = os.getenv('AIRFLOW__CELERY__BROKER_PORT', '6379')
    
    max_retries = 30
    for attempt in range(max_retries):
        try:
            result = subprocess.run(
                ['nc', '-z', host, port],
                capture_output=True,
                text=True
            )
            if result.returncode == 0:
                print("✅ Redis está pronto!")
                return True
        except:
            pass
        
        print(f"⏳ Redis não está pronto, aguardando... (tentativa {attempt + 1}/{max_retries})")
        time.sleep(2)
    
    print("❌ Redis falhou ao inicializar")
    return False


def check_database_initialized():
    """Verificar se o banco do Airflow está inicializado."""
    print("🔍 Verificando se o banco do Airflow está inicializado...")
    
    host = os.getenv('AIRFLOW__DATABASE__SQL_ALCHEMY_HOST', 'airflow-postgres')
    database = os.getenv('AIRFLOW__DATABASE__SQL_ALCHEMY_DATABASE', 'airflow')
    user = os.getenv('AIRFLOW__DATABASE__SQL_ALCHEMY_USER', 'airflow')
    password = os.getenv('AIRFLOW__DATABASE__SQL_ALCHEMY_PASSWORD', 'airflow')
    
    try:
        conn = psycopg2.connect(
            host=host,
            database=database,
            user=user,
            password=password
        )
        cursor = conn.cursor()
        
        # Verificar se a tabela log existe (criada pelo airflow db init)
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'log'
            );
        """)
        
        log_table_exists = cursor.fetchone()[0]
        
        # Verificar se a tabela slot_pool existe (para pools)
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'slot_pool'
            );
        """)
        
        pool_table_exists = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        if log_table_exists and pool_table_exists:
            print("✅ Banco já inicializado com todas as tabelas necessárias")
            return True
        else:
            print(f"⚠️ Banco não totalmente inicializado - log: {log_table_exists}, pool: {pool_table_exists}")
            return False
            
    except Exception as e:
        print(f"❌ Erro ao verificar banco: {e}")
        return False


def initialize_database():
    """Inicializar banco do Airflow usando airflow db migrate."""
    print("🗄️ Inicializando banco do Airflow...")
    
    try:
        result = subprocess.run(
            ["airflow", "db", "migrate"],
            check=True,
            capture_output=True,
            text=True
        )
        print("✅ Banco inicializado com sucesso")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Falha ao inicializar banco: {e}")
        print(f"Erro: {e.stderr}")
        return False


def load_airflow_config():
    """Carrega configurações do Airflow do config.yml"""
    try:
        # Tentar diferentes caminhos (Docker e local)
        possible_paths = [
            '/opt/airflow/config/config.yml',  # Docker
            'config/config.yml',  # Local
            Path(__file__).parent / 'config' / 'config.yml'  # Relativo
        ]
        
        for path in possible_paths:
            path_obj = Path(path) if isinstance(path, str) else path
            if path_obj.exists():
                with open(path_obj, 'r', encoding='utf-8') as file:
                    config = yaml.safe_load(file)
                    return config.get('airflow', {})
        
        # Fallback para valores padrão
        print("⚠️ config.yml não encontrado, usando valores padrão")
        return {
            'admin_username': 'airflow',
            'admin_password': 'airflow',
            'admin_email': 'admin@example.com'
        }
    except Exception as e:
        print(f"⚠️ Erro ao carregar config.yml: {e}, usando valores padrão")
        return {
            'admin_username': 'airflow',
            'admin_password': 'airflow',
            'admin_email': 'admin@example.com'
        }


def create_admin_user():
    """Criar usuário admin se não existir."""
    print("👤 Criando usuário admin...")
    
    # Carregar configurações
    airflow_config = load_airflow_config()
    username = airflow_config.get('admin_username', 'airflow')
    password = airflow_config.get('admin_password', 'airflow')
    email = airflow_config.get('admin_email', 'admin@example.com')
    
    # Verificar se usuário já existe
    try:
        result = subprocess.run(
            ["airflow", "users", "list"],
            capture_output=True,
            text=True,
            check=True
        )
        if username in result.stdout:
            print(f"✅ Usuário '{username}' já existe")
            # Atualizar senha do usuário existente
            try:
                subprocess.run([
                    "airflow", "users", "reset-password",
                    "--username", username,
                    "--password", password
                ], check=True, capture_output=True)
                print(f"✅ Senha do usuário '{username}' atualizada")
            except subprocess.CalledProcessError as e:
                print(f"⚠️ Falha ao atualizar senha: {e.stderr}")
            return
    except subprocess.CalledProcessError:
        pass
    
    # Criar novo usuário
    try:
        subprocess.run([
            "airflow", "users", "create",
            "--username", username,
            "--firstname", "Admin",
            "--lastname", "User",
            "--role", "Admin",
            "--email", email,
            "--password", password
        ], check=True, capture_output=True, text=True)
        print(f"✅ Usuário '{username}' criado com sucesso")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Falha ao criar usuário: {e.stderr}")
        # Tentar resetar senha se usuário existir mas com senha diferente
        try:
            subprocess.run([
                "airflow", "users", "reset-password",
                "--username", username,
                "--password", password
            ], check=True, capture_output=True, text=True)
            print(f"✅ Senha do usuário '{username}' resetada")
        except subprocess.CalledProcessError:
            print("⚠️ Não foi possível criar ou atualizar usuário")


def ensure_default_pool():
    """Garantir que o pool padrão existe."""
    print("🏊 Garantindo que o pool padrão existe...")
    
    try:
        subprocess.run([
            "airflow", "pools", "set",
            "default_pool",
            "32",
            "Pool padrão para tarefas"
        ], check=True, capture_output=True)
        print("✅ Pool padrão criado/atualizado com sucesso")
    except subprocess.CalledProcessError:
        print("⚠️ Pool padrão já existe ou criação falhou")


def run_airflow_setup():
    """Executar script de setup personalizado."""
    print("🔧 Executando setup personalizado...")
    
    try:
        subprocess.run([
            "python", "/opt/airflow/airflow_setup.py"
        ], check=True)
        print("✅ Setup personalizado executado com sucesso")
    except subprocess.CalledProcessError as e:
        print(f"⚠️ Setup personalizado falhou: {e}")


def main():
    """Função principal."""
    print("Iniciando setup do Airflow...")
    
    # Aguardar dependências
    if not wait_for_postgres():
        sys.exit(1)
    
    if not wait_for_redis():
        sys.exit(1)
    
    # Detectar qual comando está sendo executado
    command = sys.argv[1] if len(sys.argv) > 1 else None
    is_worker = command == "celery" and len(sys.argv) > 2 and sys.argv[2] == "worker"
    
    # Apenas webserver inicializa banco e cria usuário
    # Scheduler e worker apenas aguardam banco estar pronto
    if command == "webserver":
        # Verificar e inicializar banco se necessário
        if not check_database_initialized():
            if not initialize_database():
                sys.exit(1)
        
        # Criar usuário admin apenas no webserver
        create_admin_user()
        
        # Garantir pool padrão
        ensure_default_pool()
        
        # Executar setup personalizado
        run_airflow_setup()
        
        print("✅ Setup do Airflow concluído!")
    elif command in ["scheduler"] or is_worker:
        # Para scheduler e worker, apenas aguardar banco estar pronto
        # Não inicializar banco nem criar usuário
        print("⏳ Aguardando banco estar totalmente inicializado...")
        max_wait = 60
        for i in range(max_wait):
            if check_database_initialized():
                print("✅ Banco está pronto!")
                break
            time.sleep(1)
        else:
            print("⚠️ Banco pode não estar totalmente inicializado, mas continuando...")
    
    # Executar o comando principal
    if len(sys.argv) > 1:
        arguments = sys.argv[1:]
        airflow_command = ["airflow"] + arguments
        print(f"Executando: {' '.join(airflow_command)}")
        os.execvp("airflow", airflow_command)
    else:
        print("⚠️ Nenhum comando especificado")


if __name__ == "__main__":
    main() 