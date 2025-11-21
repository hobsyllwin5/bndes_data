"""
Transformador específico de dados BNDES
Reutiliza funções genéricas de transformação
"""

import pandas as pd
import io
import logging
from minio import Minio
from libs.config_manager import ConfigYml
from libs.schema_loader import load_schema_config


def _load_schema_config():
    """Carrega configurações do schema.yml"""
    return load_schema_config()


def _extract_from_minio(bucket_name: str, prefixes: list) -> pd.DataFrame:
    """Extrai CSV mais recente do MinIO"""
    config = ConfigYml.load_config()
    minio_config = config['minio']
    
    minio_client = Minio(
        'minio:9000',
        access_key=minio_config['access_key'],
        secret_key=minio_config['secret_key'],
        secure=False
    )
    
    csv_objects = []
    for prefix in prefixes:
        objects = list(minio_client.list_objects(bucket_name, prefix=prefix, recursive=True))
        csv_objects.extend([obj for obj in objects if obj.object_name.endswith('.csv')])
    
    if not csv_objects:
        raise ValueError("Nenhum arquivo CSV encontrado no MinIO")
    
    latest_csv = max(csv_objects, key=lambda x: x.last_modified)
    logging.info(f"📄 Processando: {latest_csv.object_name}")
    
    csv_data = minio_client.get_object(bucket_name, latest_csv.object_name)
    df = pd.read_csv(io.BytesIO(csv_data.read()))
    
    return df, latest_csv.object_name


def _transform_bndes_data(df: pd.DataFrame, config: dict) -> pd.DataFrame:
    """Transforma dados BNDES: horizontal -> vertical"""
    estado_uf_map = config['estado_para_uf']
    colunas_controle = config['transformacao']['colunas_controle']
    validacao = config['transformacao']['validacao']
    
    # Identificar colunas de UF
    uf_columns = [
        col for col in df.columns 
        if col not in colunas_controle and col in estado_uf_map
    ]
    
    logging.info(f"🗺️ UFs identificadas: {len(uf_columns)} estados")
    
    # Verticalização
    dados_verticalizados = []
    
    for _, row in df.iterrows():
        ano_int = int(row['ano'])
        mes = int(row['mes'])
        periodo = pd.to_datetime(f"{ano_int}-{mes:02d}-01").date()
        
        for estado_nome in uf_columns:
            valor = row[estado_nome]
            uf_codigo = estado_uf_map[estado_nome]
            
            if pd.notna(valor):
                try:
                    valor_float = float(valor)                    
                    valor_unidades = valor_float * 1_000_000
                    
                    if validacao['valor_minimo'] <= valor_float <= validacao['valor_maximo']:
                        dados_verticalizados.append({
                            'ano': ano_int,
                            'mes': mes,
                            'periodo': periodo,
                            'uf': uf_codigo,
                            'valor_desembolso': round(valor_unidades, validacao['casas_decimais'])
                        })
                except (ValueError, TypeError):
                    continue
    
    return pd.DataFrame(dados_verticalizados)


def extract_and_transform(**context):
    """Extrai do MinIO e transforma dados BNDES"""
    try:
        logging.info("🔄 Iniciando extração e transformação...")
        
        config = _load_schema_config()
        
        bucket_name = ConfigYml.load_config()['minio']['bucket_name']
        prefixes = ['desembolsos_por_uf/', 'bndes/desembolsos_por_uf/']
        df_raw, arquivo_origem = _extract_from_minio(bucket_name, prefixes)
        
        logging.info(f"📊 Dados originais: {len(df_raw)} linhas, {len(df_raw.columns)} colunas")
        
        df_transformed = _transform_bndes_data(df_raw, config)
        logging.info(f"✅ Verticalização concluída: {len(df_transformed)} registros")
        
        result = {
            'data': df_transformed.to_json(orient='records', date_format='iso'),
            'total_registros': len(df_transformed),
            'arquivo_origem': arquivo_origem
        }
        
        return result
        
    except Exception as e:
        logging.error(f"❌ Erro na extração/transformação: {str(e)}")
        raise

