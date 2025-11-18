import sys
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from sources.bndes_transformer import extract_and_transform
from sources.bndes_loader import load_to_postgres
from sources.helper_state_info import create_estados_table

sys.path.append('/opt/airflow')


default_args = {
    'owner': 'data-student',
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
    description='Transforma dados BNDES: MinIO → PostgreSQL',
    schedule_interval=None,
    catchup=False,
    tags=['bndes', 'transformation', 'etl'],
)


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


create_estados_task = PythonOperator(
    task_id='create_estados_table',
    python_callable=lambda **context: create_estados_table(postgres_conn_id='bndes_postgres'),
    dag=dag,
)


extract_transform_task >> [load_task, create_estados_task]
