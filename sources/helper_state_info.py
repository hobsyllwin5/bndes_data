"""
Helper para gerenciar informações geográficas dos estados brasileiros
Lê dados do schema.yml e fornece funções para criar/popular tabela no PostgreSQL
"""

import pandas as pd
from airflow.providers.postgres.hooks.postgres import PostgresHook
import logging
from libs.schema_loader import load_schema_config


def get_estados_data():
    """
    Retorna dicionário com dados dos estados lidos do schema.yml
    
    Returns:
        dict: Dicionário com dados dos estados {UF: {nome, capital, lat, lng, regiao, area}}
    """
    config = load_schema_config()
    return config.get('dados_estados', {})


def get_estados_dataframe():
    """
    Retorna DataFrame pandas com dados de todos os estados lidos do schema.yml
    
    Returns:
        pandas.DataFrame: DataFrame com colunas [uf, nome_estado, nome_capital, 
                                                   latitude, longitude, regiao, area_km2]
    """
    estados_data = get_estados_data()
    dados = []
    for uf, info in estados_data.items():
        dados.append({
            'uf': uf,
            'nome_estado': info['nome'],
            'nome_capital': info['capital'],
            'latitude': float(info['lat']),
            'longitude': float(info['lng']),
            'regiao': info['regiao'],
            'area_km2': int(info['area'])
        })
    
    return pd.DataFrame(dados)


def get_estado_info(uf):
    """
    Retorna informações de um estado específico lidas do schema.yml
    
    Args:
        uf (str): Código UF (ex: 'SP', 'RJ')
    
    Returns:
        dict: Dicionário com informações do estado ou None se não encontrado
    """
    uf = uf.upper()
    estados_data = get_estados_data()
    if uf in estados_data:
        info = estados_data[uf]
        return {
            'uf': uf,
            'nome': info['nome'],
            'capital': info['capital'],
            'latitude': float(info['lat']),
            'longitude': float(info['lng']),
            'regiao': info['regiao'],
            'area_km2': int(info['area'])
        }
    return None




def create_estados_table(postgres_conn_id='bndes_postgres', force_recreate=False):
    """
    Cria e popula tabela de estados no PostgreSQL
    
    Args:
        postgres_conn_id (str): ID da conexão PostgreSQL no Airflow
        force_recreate (bool): Se True, recria tabela mesmo se já existir
    
    Returns:
        dict: Estatísticas da operação
    """
    try:
        # Carregar configurações
        config = load_schema_config()
        estados_config = config['estados_info']
        
        logging.info("🗺️ Criando tabela de estados...")
        
        # Conectar ao PostgreSQL
        postgres_hook = PostgresHook(postgres_conn_id=postgres_conn_id)
        
        # Se force_recreate, dropar tabela existente
        if force_recreate:
            drop_sql = f"DROP TABLE IF EXISTS {estados_config['table_name']} CASCADE;"
            postgres_hook.run(drop_sql)
            logging.info(f"🗑️ Tabela {estados_config['table_name']} removida")
        
        # Criar tabela de estados
        columns_sql = []
        for col_name, col_config in estados_config['columns'].items():
            col_def = f"{col_name} {col_config['type']}"
            if col_config['constraints']:
                col_def += f" {col_config['constraints']}"
            columns_sql.append(col_def)
        
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {estados_config['table_name']} (
            {', '.join(columns_sql)}
        );
        """
        
        # Criar índices
        indexes_sql = []
        for index in estados_config['indexes']:
            cols = ", ".join(index['columns'])
            indexes_sql.append(f"CREATE INDEX IF NOT EXISTS {index['name']} ON {estados_config['table_name']}({cols});")
        
        # Executar criação
        postgres_hook.run(create_table_sql)
        for index_sql in indexes_sql:
            postgres_hook.run(index_sql)
        
        logging.info("✅ Tabela estados_info criada")
        
        # Verificar se já tem dados
        count_result = postgres_hook.get_first(
            f"SELECT COUNT(*) FROM {estados_config['table_name']}"
        )
        existing_count = count_result[0] if count_result else 0
        
        if existing_count > 0 and not force_recreate:
            logging.info(f"⚠️ Tabela já possui {existing_count} registros, pulando inserção")
            return {
                'status': 'skipped',
                'registros_existentes': existing_count
            }
        
        # Limpar dados existentes se force_recreate
        if existing_count > 0:
            delete_sql = f"DELETE FROM {estados_config['table_name']};"
            postgres_hook.run(delete_sql)
            logging.info(f"🗑️ {existing_count} registros antigos removidos")
        
        # Preparar dados para inserção (lendo do schema.yml)
        estados_data = get_estados_data()
        values_list = []
        for uf, info in estados_data.items():
            values_list.append((
                uf,
                info['nome'],
                info['capital'],
                float(info['lat']),
                float(info['lng']),
                info['regiao'],
                int(info['area'])
            ))
        
        # Inserção em lote usando execute_values (mais eficiente)
        insert_sql = f"""
            INSERT INTO {estados_config['table_name']} 
            (uf, nome_estado, nome_capital, latitude, longitude, regiao, area_km2)
            VALUES %s
        """
        
        from psycopg2.extras import execute_values
        with postgres_hook.get_conn() as conn:
            with conn.cursor() as cursor:
                execute_values(cursor, insert_sql, values_list, page_size=100)
            conn.commit()
        
        # Verificar resultado
        total_count = postgres_hook.get_first(
            f"SELECT COUNT(*) FROM {estados_config['table_name']}"
        )[0]
        
        logging.info(f"✅ Tabela estados_info populada: {total_count} estados inseridos")
        
        return {
            'status': 'success',
            'registros_inseridos': len(values_list),
            'total_na_tabela': total_count
        }
        
    except Exception as e:
        logging.error(f"❌ Erro ao criar tabela de estados: {str(e)}")
        raise


if __name__ == "__main__":
    # Teste básico
    print("=== Teste helper_state_info.py ===")
    
    # Testar get_estados_dataframe
    df = get_estados_dataframe()
    print(f"\n✅ DataFrame criado: {df.shape[0]} estados")
    print(df.head())
    
    # Testar get_estado_info
    print("\n=== Informações de SP ===")
    sp_info = get_estado_info('SP')
    print(sp_info)
    
    print("\n✅ Testes concluídos!")

