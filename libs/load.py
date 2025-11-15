"""
Módulo genérico de carga de dados
Orquestra o processo: validate -> create_table -> delete_old -> insert -> verify
"""

import pandas as pd
import io
from typing import Dict, Any, Optional
from airflow.providers.postgres.hooks.postgres import PostgresHook
from psycopg2.extras import execute_values


def load_data(
    data_json: str,
    table_config: Dict[str, Any],
    postgres_conn_id: str,
    delete_condition: Optional[str] = None
) -> Dict[str, Any]:
    """
    Função genérica de carga de dados no PostgreSQL
    
    Args:
        data_json: Dados serializados em JSON (orient='records')
        table_config: Configuração da tabela (columns, indexes, table_name)
        postgres_conn_id: ID da conexão PostgreSQL no Airflow
        delete_condition: Condição SQL para deletar dados antigos (opcional)
    
    Returns:
        dict: Estatísticas da carga
    """
    # Parse dados
    df = pd.read_json(io.StringIO(data_json))
    
    if df.empty:
        raise ValueError("Nenhum dado para carregar")
    
    # Converter período se existir (vem como string do JSON)
    if 'periodo' in df.columns:
        df['periodo'] = pd.to_datetime(df['periodo']).dt.date
    
    # Conectar
    postgres_hook = PostgresHook(postgres_conn_id=postgres_conn_id)
    
    # Criar tabela
    _create_table(postgres_hook, table_config)
    
    # Deletar dados antigos se necessário
    if delete_condition:
        postgres_hook.run(f"DELETE FROM {table_config['table_name']} WHERE {delete_condition}")
    
    # Inserir dados
    _insert_data(postgres_hook, df, table_config)
    
    # Verificar resultado
    total_count = postgres_hook.get_first(
        f"SELECT COUNT(*) FROM {table_config['table_name']}"
    )[0]
    
    return {
        'registros_inseridos': len(df),
        'total_na_tabela': total_count
    }


def _create_table(postgres_hook: PostgresHook, table_config: Dict[str, Any]):
    """Cria tabela e índices se não existirem"""
    # Colunas
    columns_sql = []
    for col_name, col_config in table_config['columns'].items():
        col_def = f"{col_name} {col_config['type']}"
        if col_config.get('constraints'):
            col_def += f" {col_config['constraints']}"
        columns_sql.append(col_def)
    
    create_table_sql = f"""
    CREATE TABLE IF NOT EXISTS {table_config['table_name']} (
        {', '.join(columns_sql)}
    );
    """
    
    postgres_hook.run(create_table_sql)
    
    # Índices
    for index in table_config.get('indexes', []):
        cols = ", ".join(index['columns'])
        index_sql = f"CREATE INDEX IF NOT EXISTS {index['name']} ON {table_config['table_name']}({cols});"
        postgres_hook.run(index_sql)


def _insert_data(postgres_hook: PostgresHook, df: pd.DataFrame, table_config: Dict[str, Any]):
    """Insere dados em lote"""
    # Preparar valores
    column_names = list(table_config['columns'].keys())
    # Remover colunas que não estão no DataFrame (ex: id, updated_at)
    column_names = [col for col in column_names if col in df.columns]
    
    values_list = [tuple(row[col] for col in column_names) for _, row in df.iterrows()]
    
    # SQL de inserção
    cols_str = ", ".join(column_names)
    placeholders = ", ".join(["%s"] * len(column_names))
    insert_sql = f"""
        INSERT INTO {table_config['table_name']} ({cols_str})
        VALUES %s
    """
    
    # Inserção em lote
    with postgres_hook.get_conn() as conn:
        with conn.cursor() as cursor:
            execute_values(cursor, insert_sql, values_list, page_size=1000)
        conn.commit()

