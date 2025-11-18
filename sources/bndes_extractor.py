"""
Extrator específico de dados BNDES
Reutiliza a função genérica de extração
"""

import logging
from libs.extract import extract_data
from libs.config_manager import ConfigYml
from sources.bndes_api import fetch_data
from libs.storage import save_to_minio


def extract_bndes_data(**context):
    """Extrai dados do BNDES e salva no MinIO"""
    logging.info("🔄 Iniciando extração de dados do BNDES...")
    
    resources = ConfigYml.get_resources()
    if not resources:
        raise ValueError("Nenhum recurso encontrado no config.yml")
    
    resource_info = resources[0]
    resource_id = resource_info['id']
    resource_name = resource_info['name']
    
    logging.info(f"📋 Extraindo recurso: {resource_name} (ID: {resource_id})")
    
    try:
        result = extract_data(
            fetch_func=fetch_data,
            save_func=save_to_minio,
            resource_id=resource_id,
            resource_name=resource_name,
            fetch_kwargs={'limit': 50000},
            save_formats=['csv', 'json']
        )
        
        logging.info(f"✅ Dados extraídos com sucesso: {result['records_count']} registros")
        logging.info(f"📁 Arquivos salvos: {len(result['files_saved'])}")
        logging.info(f"📊 Colunas: {result['columns_count']}")
        
        if 'period' in result:
            period = result['period']
            logging.info(f"📅 Período: {period['min']} - {period['max']}")
        
        return result
        
    except Exception as e:
        logging.error(f"❌ Erro na extração: {str(e)}")
        raise
