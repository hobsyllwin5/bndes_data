#!/usr/bin/env python3
"""
Script para configurar conexões iniciais do Airflow
Deve ser executado após a inicialização do Airflow
"""

import os
import sys
from airflow.models import Connection
from airflow.utils.db import provide_session
from libs.config_manager import ConfigYml

@provide_session
def create_minio_connection(session=None):
    """
    Criar conexão do MinIO/S3 para remote logging e tasks
    """
    conn_id = 'minio_s3'
    
    # Verificar se a conexão já existe
    existing_conn = session.query(Connection).filter(Connection.conn_id == conn_id).first()
    
    if existing_conn:
        print(f"✅ Conexão '{conn_id}' já existe")
        return
    
    # Carregar configurações do MinIO
    minio_config = ConfigYml.get_minio_config()
    
    # Criar nova conexão
    new_conn = Connection(
        conn_id=conn_id,
        conn_type='aws',
        host='minio:9000',  # Nome do serviço no Docker
        login=minio_config['access_key'],
        password=minio_config['secret_key'],
        extra={
            "aws_access_key_id": minio_config['access_key'],
            "aws_secret_access_key": minio_config['secret_key'],
            "endpoint_url": minio_config['endpoint_url'],
            "region_name": minio_config.get('region', 'us-east-1')
        }
    )
    
    session.add(new_conn)
    session.commit()
    print(f"✅ Conexão '{conn_id}' criada com sucesso")

@provide_session  
def create_postgres_connection(session=None):
    """
    Criar conexão do PostgreSQL para futura integração
    """
    conn_id = 'bndes_postgres'
    
    # Verificar se a conexão já existe
    existing_conn = session.query(Connection).filter(Connection.conn_id == conn_id).first()
    
    if existing_conn:
        print(f"✅ Conexão '{conn_id}' já existe")
        return
    
    # Carregar configurações do PostgreSQL
    db_config = ConfigYml.get_database_config()
    
    # Criar nova conexão
    new_conn = Connection(
        conn_id=conn_id,
        conn_type='postgres',
        host=db_config['host'],
        port=db_config['port'],
        schema=db_config['database'],
        login=db_config['user'],
        password=db_config['password']
    )
    
    session.add(new_conn)
    session.commit()
    print(f"✅ Conexão '{conn_id}' criada com sucesso")

def main():
    """
    Função principal para configurar todas as conexões
    """
    print("🔧 Configurando conexões do Airflow...")
    
    try:
        # Configurar conexões
        create_minio_connection()
        create_postgres_connection()
        
        print("✅ Todas as conexões foram configuradas com sucesso!")
        
    except Exception as e:
        print(f"❌ Erro ao configurar conexões: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main() 