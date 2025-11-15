"""
Módulo de acesso à API do BNDES
"""

from ckanapi import RemoteCKAN
import pandas as pd
from libs.config_manager import ConfigYml


def connect_bndes_api():
    """Estabelece conexão com a API do BNDES"""
    config = ConfigYml.load_config()
    base_url = config['api']['base_url'].split('/api')[0]
    return RemoteCKAN(base_url)


def fetch_data(resource_id, limit=1000, query=None, filters=None):
    """
    Busca dados de um recurso específico do BNDES
    
    Args:
        resource_id: ID do recurso/tabela
        limit: número máximo de registros
        query: texto para busca em todos os campos
        filters: dicionário com filtros específicos por campo
    
    Returns:
        pandas.DataFrame: Dados do recurso
    """
    try:
        api = connect_bndes_api()
        result = api.action.datastore_search(
            resource_id=resource_id,
            limit=limit,
            q=query,
            filters=filters
        )
        return pd.DataFrame(result['records'])
    except Exception as e:
        print(f"Erro ao buscar dados: {str(e)}")
        return None

