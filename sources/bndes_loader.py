"""
Loader específico de dados BNDES
Reutiliza funções genéricas de carga
"""

import pandas as pd
import io
import logging
from libs.load import load_data
from libs.schema_loader import load_schema_config


def _load_schema_config():
    """Carrega configurações do schema.yml"""
    return load_schema_config()


def load_to_postgres(**context):
    """Carrega dados transformados no PostgreSQL"""
    try:
        # Recuperar dados da task anterior
        task_data = context['task_instance'].xcom_pull(task_ids='extract_and_transform')
        if not task_data:
            raise ValueError("Nenhum dado recebido da transformação")
        
        # Configuração
        config = _load_schema_config()
        table_config = config['desembolsos_por_uf']
        
        # Parse dados temporariamente para obter períodos (delete condition)
        df_temp = pd.read_json(io.StringIO(task_data['data']))
        df_temp['periodo'] = pd.to_datetime(df_temp['periodo']).dt.date
        
        logging.info(f"💾 Carregando {len(df_temp)} registros no PostgreSQL...")
        
        # Condição de delete: remover dados do mesmo período
        periodos = df_temp['periodo'].unique()
        if len(periodos) > 0:
            periodo_list = "','".join([str(p) for p in periodos])
            delete_condition = f"periodo IN ('{periodo_list}')"
        else:
            delete_condition = None
        
        # Load genérico (passa JSON serializado)
        result = load_data(
            data_json=task_data['data'],
            table_config=table_config,
            postgres_conn_id='bndes_postgres',
            delete_condition=delete_condition
        )
        
        logging.info(f"✅ Carga concluída: {result['registros_inseridos']} registros inseridos")
        logging.info(f"📊 Total na tabela: {result['total_na_tabela']} registros")
        
        return {
            'registros_inseridos': result['registros_inseridos'],
            'total_na_tabela': result['total_na_tabela'],
            'arquivo_origem': task_data['arquivo_origem']
        }
        
    except Exception as e:
        logging.error(f"❌ Erro ao carregar no PostgreSQL: {str(e)}")
        raise

