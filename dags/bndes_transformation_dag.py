"""
DAG para transformação de dados BNDES: MinIO → PostgreSQL (Data Lake → Data Warehouse)
Versão simplificada e otimizada usando configurações do schema.yml
"""

from datetime import datetime, timedelta
import pandas as pd
import yaml
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from minio import Minio
import io
import logging
import sys
sys.path.append('/opt/airflow')
from libs.helper_state_info import create_estados_table

# Configurações do DAG
default_args = {
    'owner': 'bndes-team',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=3),
}

dag = DAG(
    'bndes_transformation',
    default_args=default_args,
    description='Transforma dados BNDES: MinIO → PostgreSQL (otimizado)',
    schedule_interval=None,  # Execução manual apenas
    catchup=False,
    tags=['bndes', 'transformation', 'etl'],
)

def load_schema_config():
    """Carrega configurações do schema.yml"""
    schema_path = '/opt/airflow/config/schema.yml'
    with open(schema_path, 'r', encoding='utf-8') as file:
        return yaml.safe_load(file)

def extract_and_transform(**context):
    """Extrai do MinIO e transforma os dados usando schema.yml"""
    try:
        # Carregar configurações
        config = load_schema_config()
        estado_uf_map = config['estado_para_uf']
        colunas_controle = config['transformacao']['colunas_controle']
        validacao = config['transformacao']['validacao']
        
        logging.info("🔄 Iniciando extração e transformação...")
        
        # Conectar ao MinIO
        minio_client = Minio(
            'minio:9000',
            access_key='minioadmin',
            secret_key='minioadmin123',
            secure=False
        )
        
        # Buscar arquivo CSV mais recente (compatível com estruturas antiga e nova)
        bucket_name = 'bndes-data'
        
        # Listar TODOS os objetos no bucket para debug
        logging.info("🔍 Listando todos os objetos no bucket...")
        all_objects = list(minio_client.list_objects(bucket_name, recursive=True))
        for obj in all_objects:
            logging.info(f"  📁 {obj.object_name}")
        
        # Procurar CSVs na estrutura nova (desembolsos_por_uf/)
        objects_new = list(minio_client.list_objects(bucket_name, prefix='desembolsos_por_uf/', recursive=True))
        csv_objects_new = [obj for obj in objects_new if obj.object_name.endswith('.csv')]
        
        # Procurar CSVs na estrutura antiga (bndes/desembolsos_por_uf/)  
        objects_old = list(minio_client.list_objects(bucket_name, prefix='bndes/desembolsos_por_uf/', recursive=True))
        csv_objects_old = [obj for obj in objects_old if obj.object_name.endswith('.csv')]
        
        # Combinar ambas as estruturas
        csv_objects = csv_objects_new + csv_objects_old
        
        logging.info(f"📊 CSVs encontrados - Nova estrutura: {len(csv_objects_new)}, Antiga: {len(csv_objects_old)}")
        
        if not csv_objects:
            raise ValueError("❌ Nenhum arquivo CSV encontrado no MinIO em nenhuma estrutura")
        
        latest_csv = max(csv_objects, key=lambda x: x.last_modified)
        logging.info(f"📄 Processando: {latest_csv.object_name}")
        
        # Baixar e ler dados
        csv_data = minio_client.get_object(bucket_name, latest_csv.object_name)
        df_original = pd.read_csv(io.BytesIO(csv_data.read()))
        
        logging.info(f"📊 Dados originais: {len(df_original)} linhas, {len(df_original.columns)} colunas")
        
        # Identificar colunas de UF (excluir colunas de controle)
        uf_columns = [col for col in df_original.columns 
                     if col not in colunas_controle and col in estado_uf_map]
        
        logging.info(f"🗺️ UFs identificadas: {len(uf_columns)} estados")
        
        # VERTICALIZAÇÃO: Transformar dados horizontais em verticais
        dados_verticalizados = []
        
        for _, row in df_original.iterrows():
            ano_int = int(row['ano'])
            mes = int(row['mes'])
            periodo = pd.to_datetime(f"{ano_int}-{mes:02d}-01").date()
            
            # Para cada UF, criar um registro
            for estado_nome in uf_columns:
                valor = row[estado_nome]
                uf_codigo = estado_uf_map[estado_nome]
                
                # Processar valor se não for nulo
                if pd.notna(valor):
                    try:
                        valor_float = float(valor)
                        
                        # Aplicar validações do schema (sem limpeza adicional)
                        if validacao['valor_minimo'] <= valor_float <= validacao['valor_maximo']:
                            dados_verticalizados.append({
                                'ano': ano_int,
                                'mes': mes,
                                'periodo': periodo,
                                'uf': uf_codigo,
                                'valor_desembolso': round(valor_float, validacao['casas_decimais'])
                            })
                    except (ValueError, TypeError):
                        continue
        
        if not dados_verticalizados:
            raise ValueError("❌ Nenhum dado válido após transformação")
        
        df_verticalizado = pd.DataFrame(dados_verticalizados)
        
        logging.info(f"✅ Verticalização concluída: {len(df_verticalizado)} registros")
        
        # Retornar dados para próxima task
        return {
            'data': df_verticalizado.to_json(orient='records', date_format='iso'),
            'total_registros': len(df_verticalizado),
            'arquivo_origem': latest_csv.object_name
        }
        
    except Exception as e:
        logging.error(f"❌ Erro na extração/transformação: {str(e)}")
        raise

def load_to_postgres(**context):
    """Carrega dados transformados no PostgreSQL"""
    try:
        # Recuperar dados da task anterior
        task_data = context['task_instance'].xcom_pull(task_ids='extract_and_transform')
        if not task_data:
            raise ValueError("❌ Nenhum dado recebido da transformação")
        
        # Carregar configurações e dados
        config = load_schema_config()
        table_config = config['desembolsos_por_uf']
        df = pd.read_json(io.StringIO(task_data['data']))
        df['periodo'] = pd.to_datetime(df['periodo']).dt.date
        
        logging.info(f"💾 Carregando {len(df)} registros no PostgreSQL...")
        
        # Conectar ao PostgreSQL
        postgres_hook = PostgresHook(postgres_conn_id='bndes_postgres')
        
        # Criar tabela se não existir (usando schema.yml)
        columns_sql = []
        for col_name, col_config in table_config['columns'].items():
            col_def = f"{col_name} {col_config['type']}"
            if col_config['constraints']:
                col_def += f" {col_config['constraints']}"
            columns_sql.append(col_def)
        
        create_table_sql = f"""
        CREATE TABLE IF NOT EXISTS {table_config['table_name']} (
            {', '.join(columns_sql)}
        );
        """
        
        # Criar índices
        indexes_sql = []
        for index in table_config['indexes']:
            cols = ", ".join(index['columns'])
            indexes_sql.append(f"CREATE INDEX IF NOT EXISTS {index['name']} ON {table_config['table_name']}({cols});")
        
        # Executar criação
        postgres_hook.run(create_table_sql)
        for index_sql in indexes_sql:
            postgres_hook.run(index_sql)
        
        logging.info("✅ Tabela e índices criados/verificados")
        
        # Limpar dados do mesmo período (para reprocessamento)
        periodos = df['periodo'].unique()
        if len(periodos) > 0:
            periodo_list = "','".join([str(p) for p in periodos])
            delete_sql = f"DELETE FROM {table_config['table_name']} WHERE periodo IN ('{periodo_list}')"
            postgres_hook.run(delete_sql)
            logging.info(f"🗑️ Dados antigos removidos para {len(periodos)} períodos")
        
        # Inserir novos dados em lote
        values_list = []
        for _, row in df.iterrows():
            values_list.append((
                int(row['ano']),
                int(row['mes']),
                row['periodo'],
                str(row['uf']),
                float(row['valor_desembolso'])
            ))
        
        # Inserção em lote usando execute_values (mais eficiente)
        insert_sql = f"""
            INSERT INTO {table_config['table_name']} (ano, mes, periodo, uf, valor_desembolso)
            VALUES %s
        """
        
        from psycopg2.extras import execute_values
        with postgres_hook.get_conn() as conn:
            with conn.cursor() as cursor:
                execute_values(cursor, insert_sql, values_list, page_size=1000)
            conn.commit()
        
        # Verificar resultado
        total_count = postgres_hook.get_first(f"SELECT COUNT(*) FROM {table_config['table_name']}")[0]
        
        logging.info(f"✅ Carga concluída: {len(df)} registros inseridos")
        logging.info(f"📊 Total na tabela: {total_count} registros")
        
        return {
            'registros_inseridos': len(df),
            'total_na_tabela': total_count,
            'arquivo_origem': task_data['arquivo_origem']
        }
        
    except Exception as e:
        logging.error(f"❌ Erro ao carregar no PostgreSQL: {str(e)}")
        raise

# Definir tasks
extract_transform_task = PythonOperator(
    task_id='extract_and_transform',
    python_callable=extract_and_transform,
    dag=dag,
)

load_task = PythonOperator(
    task_id='load_to_postgres',
    python_callable=load_to_postgres,
    dag=dag,
)

# Task para criar tabela de estados
create_estados_task = PythonOperator(
    task_id='create_estados_table',
    python_callable=lambda **context: create_estados_table(postgres_conn_id='bndes_postgres'),
    dag=dag,
)

extract_transform_task >> [load_task, create_estados_task] 