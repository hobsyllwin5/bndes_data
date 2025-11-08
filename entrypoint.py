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


def create_admin_user():
    """Criar usuário admin se não existir."""
    print("👤 Criando usuário admin...")
    
    try:
        # Tentar criar usuário
        subprocess.run([
            "airflow", "users", "create",
            "--username", "airflow",
            "--firstname", "Admin",
            "--lastname", "User",
            "--role", "Admin",
            "--email", "admin@example.com",
            "--password", "airflow"
        ], check=True, capture_output=True)
        print("✅ Usuário admin criado com sucesso")
    except subprocess.CalledProcessError:
        try:
            # Se falhar, tentar substituir
            subprocess.run([
                "airflow", "users", "create",
                "--username", "airflow",
                "--firstname", "Admin",
                "--lastname", "User",
                "--role", "Admin",
                "--email", "admin@example.com",
                "--password", "airflow",
                "--replace"
            ], check=True, capture_output=True)
            print("✅ Usuário admin atualizado com sucesso")
        except subprocess.CalledProcessError:
            print("⚠️ Usuário admin já existe ou criação falhou")


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
    
    # Verificar e inicializar banco se necessário
    if not check_database_initialized():
        if not initialize_database():
            sys.exit(1)
    
    # Criar usuário admin
    create_admin_user()
    
    # Garantir pool padrão
    ensure_default_pool()
    
    # Executar setup personalizado
    run_airflow_setup()
    
    print("✅ Setup do Airflow concluído!")
    
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