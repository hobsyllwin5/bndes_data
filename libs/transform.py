"""
Módulo genérico de transformação de dados
Orquestra o processo: extract -> transform -> validate
"""

import pandas as pd
from typing import Callable, Dict, Any, Optional


def transform_data(
    extract_func: Callable,
    transform_func: Callable,
    extract_kwargs: Optional[Dict[str, Any]] = None,
    transform_kwargs: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Função genérica de transformação de dados
    
    Args:
        extract_func: Função que extrai dados da fonte (retorna DataFrame)
        transform_func: Função que transforma os dados (recebe DataFrame, retorna DataFrame)
        extract_kwargs: Argumentos adicionais para extract_func
        transform_kwargs: Argumentos adicionais para transform_func
    
    Returns:
        dict: Dados transformados serializados e metadados
    """
    if extract_kwargs is None:
        extract_kwargs = {}
    
    if transform_kwargs is None:
        transform_kwargs = {}
    
    # Extract
    df_raw = extract_func(**extract_kwargs)
    
    if df_raw is None or df_raw.empty:
        raise ValueError("Nenhum dado extraído da fonte")
    
    # Transform
    df_transformed = transform_func(df_raw, **transform_kwargs)
    
    if df_transformed is None or df_transformed.empty:
        raise ValueError("Nenhum dado válido após transformação")
    
    # Serialize para passar entre tasks
    return {
        'data': df_transformed.to_json(orient='records', date_format='iso'),
        'total_registros': len(df_transformed),
        'columns': list(df_transformed.columns)
    }

