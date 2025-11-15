"""
Extrator específico de dados BNDES
Reutiliza a função genérica de extração
"""

from libs.extract import extract_data
from libs.config_manager import ConfigYml
from sources.bndes_api import fetch_data
from libs.storage import save_to_minio


def extract_bndes_data(**context):
    """
    Extrai dados do BNDES e salva no MinIO
    
    Returns:
        dict: Status da extração com estatísticas
    """
    print("Iniciando extração de dados do BNDES...")
    
    # Configuração
    resources = ConfigYml.get_resources()
    if not resources:
        raise ValueError("Nenhum recurso encontrado no config.yml")
    
    resource_info = resources[0]
    resource_id = resource_info['id']
    resource_name = resource_info['name']
    
    print(f"📋 Extraindo recurso: {resource_name} (ID: {resource_id})")
    
    try:
        # Extração genérica
        result = extract_data(
            fetch_func=fetch_data,
            save_func=save_to_minio,
            resource_id=resource_id,
            resource_name=resource_name,
            fetch_kwargs={'limit': 50000},
            save_formats=['csv', 'json']
        )
        
        # Log de sucesso
        print(f"✅ Dados extraídos com sucesso: {result['records_count']} registros")
        print(f"📁 Arquivos salvos: {len(result['files_saved'])}")
        print(f"📊 Colunas: {result['columns_count']}")
        
        if 'period' in result:
            period = result['period']
            print(f"📅 Período: {period['min']} - {period['max']}")
        
        return result
        
    except Exception as e:
        print(f"❌ Erro na extração: {str(e)}")
        raise
