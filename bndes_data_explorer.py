from ckanapi import RemoteCKAN
import pandas as pd
import boto3
from io import StringIO
import os
from datetime import datetime
from libs.config_manager import ConfigYml

def connect_bndes_api():
    """Estabelece conexão com a API do BNDES"""
    config = ConfigYml.load_config()
    base_url = config['api']['base_url'].split('/api')[0]  # Remover '/api/3/action' se presente
    return RemoteCKAN(base_url)

def connect_minio():
    """Estabelece conexão com o MinIO (S3)"""
    config = ConfigYml.load_config()
    
    # Verificar se as configurações do MinIO existem
    if 'minio' not in config:
        print("Configurações do MinIO não encontradas no config.yml")
        return None
    
    minio_config = config['minio']
    
    # Detectar se está rodando no Docker verificando se pode resolver o hostname 'minio'
    def is_running_in_docker():
        """Verifica se está rodando no ambiente Docker"""
        try:
            import socket
            # Tenta resolver o hostname 'minio' - só funciona no Docker
            socket.gethostbyname('minio')
            return True
        except:
            # Se não conseguir resolver 'minio', está rodando localmente
            return False
    
    if is_running_in_docker():
        # No Docker, usar sempre a URL do container
        endpoint_url = minio_config['endpoint_url']  # http://minio:9000
        print(f"🐳 Detectado ambiente Docker - usando MinIO: {endpoint_url}")
    else:
        # Localmente, usar localhost
        endpoint_url = minio_config.get('endpoint_url_local', 'http://localhost:9000')
        print(f"💻 Detectado ambiente local - usando MinIO: {endpoint_url}")
    
    # Criar cliente S3 (compatível com MinIO)
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
    Salva o DataFrame no MinIO (S3), sobrescrevendo arquivos existentes
    e adicionando uma coluna updated_at
    
    Args:
        df (pandas.DataFrame): DataFrame a ser salvo
        resource_name (str): Nome do recurso para usar no nome do arquivo
        format (str): Formato do arquivo (csv, parquet, json)
    
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
        
        # Verificar se o bucket existe, se não, criar
        try:
            s3_client.head_bucket(Bucket=bucket_name)
        except:
            s3_client.create_bucket(Bucket=bucket_name)
            print(f"Bucket '{bucket_name}' criado com sucesso")
        
        # Adicionar coluna updated_at com timestamp atual
        df_to_save = df.copy()
        current_time = datetime.now()
        df_to_save['updated_at'] = current_time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Usar nomes de arquivo fixos (sem timestamp)
        if format.lower() == 'csv':
            # Converter DataFrame para CSV
            csv_buffer = StringIO()
            df_to_save.to_csv(csv_buffer, index=False)
            file_key = f"{resource_name}/{resource_name}.csv"
            s3_client.put_object(
                Bucket=bucket_name,
                Key=file_key,
                Body=csv_buffer.getvalue()
            )
        
        elif format.lower() == 'parquet':
            # Para Parquet, precisamos salvar localmente primeiro e depois fazer upload
            temp_file = f"/tmp/{resource_name}.parquet"
            df_to_save.to_parquet(temp_file, index=False)
            
            file_key = f"{resource_name}/{resource_name}.parquet"
            with open(temp_file, 'rb') as data:
                s3_client.upload_fileobj(data, bucket_name, file_key)
            
            # Remover arquivo temporário
            os.remove(temp_file)
        
        elif format.lower() == 'json':
            # Converter DataFrame para JSON
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
        
        # Construir URL do arquivo
        endpoint = config['minio']['endpoint_url']
        url = f"{endpoint}/{bucket_name}/{file_key}"
        
        print(f"Arquivo sobrescrito com sucesso no MinIO: {url}")
        print(f"Timestamp de atualização: {current_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Antes de sobrescrever, copiar para um arquivo de backup com timestamp
        backup_timestamp = current_time.strftime("%Y%m%d_%H%M%S")
        backup_key = f"{resource_name}/backups/{resource_name}_{backup_timestamp}.{format.lower()}"
        s3_client.copy_object(
            Bucket=bucket_name,
            CopySource={'Bucket': bucket_name, 'Key': file_key},
            Key=backup_key
        )
        
        return url
    
    except Exception as e:
        print(f"Erro ao salvar no MinIO: {str(e)}")
        return None

def fetch_data(resource_id, limit=1000, query=None, filters=None):
    """
    Busca dados de um recurso específico do BNDES
    
    Parâmetros:
    - resource_id: ID do recurso/tabela que deseja consultar
    - limit: número máximo de registros (padrão: 1000)
    - query: texto para busca em todos os campos
    - filters: dicionário com filtros específicos por campo
    """
    try:
        api = connect_bndes_api()
        result = api.action.datastore_search(
            resource_id=resource_id,
            limit=limit,
            q=query,
            filters=filters
        )
        # Converte para DataFrame do pandas para facilitar análise
        return pd.DataFrame(result['records'])
    except Exception as e:
        print(f"Erro ao buscar dados: {str(e)}")
        return None

def list_datasets():
    """Lista todos os datasets disponíveis na API do BNDES"""
    try:
        api = connect_bndes_api()
        result = api.action.package_list()
        return result
    except Exception as e:
        print(f"Erro ao listar datasets: {str(e)}")
        return None

def get_dataset_resources(dataset_name):
    """Obtém os recursos disponíveis em um dataset específico"""
    try:
        api = connect_bndes_api()
        result = api.action.package_show(id=dataset_name)
        return result['resources']
    except Exception as e:
        print(f"Erro ao obter recursos do dataset {dataset_name}: {str(e)}")
        return None

def get_resource_fields(resource_id):
    """Obtém a estrutura de campos de um recurso específico"""
    try:
        api = connect_bndes_api()
        result = api.action.datastore_search(resource_id=resource_id, limit=0)
        return result['fields']
    except Exception as e:
        print(f"Erro ao obter campos do recurso {resource_id}: {str(e)}")
        return None

def analyze_dataframe(df, title="Análise do DataFrame"):
    """Realiza análise exploratória básica em um DataFrame"""
    if df is None or df.empty:
        print("Sem dados para analisar")
        return
    
    print(f"\n{title}")
    print(f"Dimensões: {df.shape[0]} linhas x {df.shape[1]} colunas")
    print("\nPrimeiras 5 linhas:")
    print(df.head())
    print("\nTipos de dados:")
    print(df.dtypes)
    print("\nEstatísticas básicas para colunas numéricas:")
    print(df.describe())
    
    # Verificar valores ausentes
    missing = df.isnull().sum()
    if missing.sum() > 0:
        print("\nValores ausentes por coluna:")
        print(missing[missing > 0])

if __name__ == "__main__":
    # Verificar se as configurações do MinIO estão presentes
    config = ConfigYml.load_config()
    if 'minio' not in config:
        print("AVISO: Configurações do MinIO não encontradas no config.yml")
        print("Os dados não serão salvos no MinIO/S3")
        minio_enabled = False
    else:
        minio_enabled = True
        print("MinIO configurado. Os dados serão salvos no bucket S3.")
    
    # Obter o resource_id padrão do config.yml
    resources = ConfigYml.get_resources()
    if not resources:
        print("ERRO: Nenhum recurso encontrado no config.yml")
        exit(1)
    
    RESOURCE_ID = resources[0]['id']  # Usar o primeiro recurso
    resource_name = resources[0]['name']
    
    print(f"Usando resource_id do config.yml: {RESOURCE_ID}")
    
    # Listar datasets disponíveis
    print("\n=== Datasets disponíveis no BNDES ===")
    datasets = list_datasets()
    if datasets:
        for i, dataset in enumerate(datasets[:5]):  # Mostrar apenas os 5 primeiros
            print(f"{i+1}. {dataset}")
        print(f"... e mais {len(datasets)-5} datasets")
        
        # Mostrar recursos do primeiro dataset como exemplo
        if datasets:
            print(f"\n=== Recursos do dataset '{datasets[0]}' ===")
            resources = get_dataset_resources(datasets[0])
            if resources:
                for i, resource in enumerate(resources):
                    print(f"{i+1}. {resource['name']} (ID: {resource['id']})")
    
    # Explorar estrutura da tabela
    print(f"\n=== Estrutura da tabela (ID: {RESOURCE_ID}) ===")
    fields = get_resource_fields(RESOURCE_ID)
    if fields:
        for field in fields:
            print(f"- {field['id']} ({field['type']})")
    
    # Exemplo 1: Busca simples dos primeiros registros
    print("\n=== Amostra de dados ===")
    df = fetch_data(RESOURCE_ID, limit=5)
    if df is not None:
        print(df)
    
    # Exemplo 2: Busca com filtro de texto
    print("\n=== Busca por termo 'desenvolvimento' ===")
    df_filtered = fetch_data(RESOURCE_ID, limit=5, query="desenvolvimento")
    if df_filtered is not None:
        print(df_filtered)
    
    # Análise exploratória de um conjunto maior de dados
    print("\n=== Análise exploratória ===")
    
    # PRIMEIRO: Descobrir quantos registros existem no total
    print("Verificando total de registros disponíveis...")
    try:
        api = connect_bndes_api()
        result = api.action.datastore_search(resource_id=RESOURCE_ID, limit=1)
        total_records = result.get('total', 0)
        print(f"Total de registros disponíveis: {total_records}")
    except Exception as e:
        print(f"Erro ao verificar total: {e}")
        total_records = 10000  # Fallback para um número alto
    
    # EXTRAIR TODOS OS DADOS (ou pelo menos muito mais que 100)
    limit_to_use = min(total_records, 50000) if total_records > 0 else 10000
    print(f"Extraindo {limit_to_use} registros...")
    
    analysis_df = fetch_data(RESOURCE_ID, limit=limit_to_use)
    if analysis_df is not None:
        print(f"✅ Dados extraídos: {analysis_df.shape[0]} linhas x {analysis_df.shape[1]} colunas")                
        analyze_dataframe(analysis_df, "Análise dos dados do BNDES")
        
        # Salvar no MinIO se estiver configurado
        if minio_enabled:
            print("\n=== Salvando dados no MinIO ===")
            # Salvar em diferentes formatos
            save_to_minio(analysis_df, resource_name, format='csv')
            
            try:
                # Tentar salvar em Parquet se pyarrow estiver instalado
                import pyarrow
                save_to_minio(analysis_df, resource_name, format='parquet')
            except ImportError:
                print("Biblioteca pyarrow não instalada. Pulando salvamento em Parquet.")
            
            save_to_minio(analysis_df, resource_name, format='json')
