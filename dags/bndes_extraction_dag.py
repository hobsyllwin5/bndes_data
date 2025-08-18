from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys

sys.path.append('/opt/airflow')

from bndes_data_explorer import fetch_data, save_to_minio
from libs.config_manager import ConfigYml


default_args = {
    'owner': 'data-student',
    'depends_on_past': False,
    'start_date': datetime(2025, 6, 30),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5)
}


dag = DAG(
    'bndes_data_extraction',
    default_args=default_args,
    description='Pipeline de extração de dados do BNDES para MinIO',
    schedule_interval=None,
    catchup=False,
    max_active_runs=1,
    tags=['bndes', 'data-extraction', 'minio', 'manual']
)


def extract_bndes_data(**context):
    print("Iniciando extração de dados do BNDES...")
    
    resources = ConfigYml.get_resources()
    if not resources:
        raise ValueError("Nenhum recurso encontrado no config.yml")
    
    resource_info = resources[0]
    resource_id = resource_info['id']
    resource_name = resource_info['name']
    
    print(f"📋 Extraindo recurso: {resource_name} (ID: {resource_id})")
    
    try:
        df = fetch_data(resource_id, limit=50000)
        
        if df is not None and not df.empty:
            print(f"✅ Dados extraídos com sucesso: {len(df)} registros")
            
            csv_result = save_to_minio(df, resource_name, 'csv')
            print(f"📁 CSV salvo: {csv_result}")
            
            json_result = save_to_minio(df, resource_name, 'json') 
            print(f"📁 JSON salvo: {json_result}")
            
            print(f"📊 Estatísticas dos dados:")
            print(f"   - Total de registros: {len(df)}")
            print(f"   - Colunas: {len(df.columns)}")
            if 'ano' in df.columns:
                print(f"   - Período: {df['ano'].min()} - {df['ano'].max()}")
            
            return {
                'status': 'success',
                'records_count': len(df),
                'columns_count': len(df.columns),
                'files_saved': [csv_result, json_result]
            }
        else:
            raise ValueError("Nenhum dado foi extraído da API")
            
    except Exception as e:
        print(f"❌ Erro na extração: {str(e)}")
        raise


extract_task = PythonOperator(
    task_id='extract_bndes_data',
    python_callable=extract_bndes_data,
    dag=dag
)
