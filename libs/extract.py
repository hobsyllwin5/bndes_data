"""
Módulo genérico de extração de dados
Orquestra o processo: fetch -> validate -> save -> stats
"""

import pandas as pd
from typing import Callable, Dict, Any, Optional


def extract_data(
    fetch_func: Callable,
    save_func: Callable,
    resource_id: str,
    resource_name: str,
    fetch_kwargs: Optional[Dict[str, Any]] = None,
    save_formats: list = None
) -> Dict[str, Any]:
    """
    Função genérica de extração de dados
    
    Args:
        fetch_func: Função que busca dados (retorna DataFrame)
        save_func: Função que salva dados (recebe df, name, format)
        resource_id: Identificador do recurso
        resource_name: Nome do recurso
        fetch_kwargs: Argumentos adicionais para fetch_func
        save_formats: Formatos para salvar (padrão: ['csv', 'json'])
    
    Returns:
        dict: Status da extração com estatísticas
    """
    if fetch_kwargs is None:
        fetch_kwargs = {}
    
    if save_formats is None:
        save_formats = ['csv', 'json']
    
    # Fetch
    df = fetch_func(resource_id, **fetch_kwargs)
    
    # Validate
    if df is None or df.empty:
        raise ValueError("Nenhum dado foi extraído")
    
    # Save
    saved_files = []
    for fmt in save_formats:
        result = save_func(df, resource_name, fmt)
        if result:
            saved_files.append(result)
    
    # Stats
    stats = {
        'status': 'success',
        'records_count': len(df),
        'columns_count': len(df.columns),
        'files_saved': saved_files
    }
    
    # Adicionar stats específicos se houver coluna 'ano'
    if 'ano' in df.columns:
        stats['period'] = {
            'min': int(df['ano'].min()),
            'max': int(df['ano'].max())
        }
    
    return stats

