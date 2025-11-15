"""
Módulo genérico de storage (MinIO/S3)
"""

import boto3
import pandas as pd
from io import StringIO
import os
from datetime import datetime
from libs.config_manager import ConfigYml


def connect_minio():
    """Estabelece conexão com o MinIO (S3)"""
    config = ConfigYml.load_config()
    
    if 'minio' not in config:
        print("Configurações do MinIO não encontradas no config.yml")
        return None
    
    minio_config = config['minio']
    
    # Detectar ambiente (Docker vs local)
    def is_running_in_docker():
        try:
            import socket
            socket.gethostbyname('minio')
            return True
        except:
            return False
    
    if is_running_in_docker():
        endpoint_url = minio_config['endpoint_url']
        print(f"🐳 Detectado ambiente Docker - usando MinIO: {endpoint_url}")
    else:
        endpoint_url = minio_config.get('endpoint_url_local', 'http://localhost:9000')
        print(f"💻 Detectado ambiente local - usando MinIO: {endpoint_url}")
    
    s3_client = boto3.client(
        's3',
        endpoint_url=endpoint_url,
        aws_access_key_id=minio_config['access_key'],
        aws_secret_access_key=minio_config['secret_key'],
        region_name=minio_config.get('region', 'us-east-1'),
        config=boto3.session.Config(signature_version='s3v4')
    )
    
    return s3_client


def save_to_minio(df, resource_name, format='csv'):
    """
    Salva o DataFrame no MinIO (S3)
    
    Args:
        df: DataFrame a ser salvo
        resource_name: Nome do recurso para usar no nome do arquivo
        format: Formato do arquivo (csv, parquet, json)
    
    Returns:
        str: URL do arquivo salvo ou None em caso de erro
    """
    if df is None or df.empty:
        print("Sem dados para salvar no MinIO")
        return None
    
    try:
        s3_client = connect_minio()
        if s3_client is None:
            return None
        
        config = ConfigYml.load_config()
        bucket_name = config['minio']['bucket_name']
        
        # Criar bucket se não existir
        try:
            s3_client.head_bucket(Bucket=bucket_name)
        except:
            s3_client.create_bucket(Bucket=bucket_name)
            print(f"Bucket '{bucket_name}' criado com sucesso")
        
        # Adicionar coluna updated_at
        df_to_save = df.copy()
        current_time = datetime.now()
        df_to_save['updated_at'] = current_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Salvar conforme formato
        if format.lower() == 'csv':
            csv_buffer = StringIO()
            df_to_save.to_csv(csv_buffer, index=False)
            file_key = f"{resource_name}/{resource_name}.csv"
            s3_client.put_object(
                Bucket=bucket_name,
                Key=file_key,
                Body=csv_buffer.getvalue()
            )
        
        elif format.lower() == 'parquet':
            temp_file = f"/tmp/{resource_name}.parquet"
            df_to_save.to_parquet(temp_file, index=False)
            file_key = f"{resource_name}/{resource_name}.parquet"
            with open(temp_file, 'rb') as data:
                s3_client.upload_fileobj(data, bucket_name, file_key)
            os.remove(temp_file)
        
        elif format.lower() == 'json':
            json_buffer = StringIO()
            df_to_save.to_json(json_buffer, orient='records')
            file_key = f"{resource_name}/{resource_name}.json"
            s3_client.put_object(
                Bucket=bucket_name,
                Key=file_key,
                Body=json_buffer.getvalue()
            )
        
        else:
            print(f"Formato não suportado: {format}")
            return None
        
        # Backup com timestamp
        backup_timestamp = current_time.strftime("%Y%m%d_%H%M%S")
        backup_key = f"{resource_name}/backups/{resource_name}_{backup_timestamp}.{format.lower()}"
        s3_client.copy_object(
            Bucket=bucket_name,
            CopySource={'Bucket': bucket_name, 'Key': file_key},
            Key=backup_key
        )
        
        endpoint = config['minio']['endpoint_url']
        url = f"{endpoint}/{bucket_name}/{file_key}"
        
        print(f"Arquivo salvo no MinIO: {url}")
        print(f"Timestamp: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        return url
    
    except Exception as e:
        print(f"Erro ao salvar no MinIO: {str(e)}")
        return None

