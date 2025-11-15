import sys
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from sources.bndes_extractor import extract_bndes_data

sys.path.append('/opt/airflow')


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


extract_task = PythonOperator(
    task_id='extract_bndes_data',
    python_callable=extract_bndes_data,
    dag=dag
)
