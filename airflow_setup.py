#!/usr/bin/env python3
"""
Script para configurar conexões iniciais do Airflow
Deve ser executado após a inicialização do Airflow
"""

import os
import sys
from airflow.models import Connection
from airflow.utils.db import provide_session

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
    
    # Criar nova conexão
    new_conn = Connection(
        conn_id=conn_id,
        conn_type='aws',
        host='minio:9000',  # Nome do serviço no Docker
        login='minioadmin',
        password='minioadmin123',
        extra={
            "aws_access_key_id": "minioadmin",
            "aws_secret_access_key": "minioadmin123",
            "endpoint_url": "http://minio:9000",
            "region_name": "us-east-1"
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
    
    # Criar nova conexão
    new_conn = Connection(
        conn_id=conn_id,
        conn_type='postgres',
        host='postgres',  # Nome do serviço no Docker
        port=5432,
        schema='bndes_data',
        login='bndes_user',
        password='bndes_password'
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