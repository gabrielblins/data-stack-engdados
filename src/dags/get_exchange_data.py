import os
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta


def get_exchange_and_save():
    import sys
    import subprocess

    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'minio'])

    import json, requests, io
    from minio import Minio

    client = Minio('minio1:9000',
                access_key='airflow',
                secret_key='sample_key',
                secure=False)

    object_data = client.get_object('raw', 'symbol_exchanges_dict.json')
    json_data = object_data.data.decode('utf-8')
    symbol_exchanges_dict=eval(json_data)

    
    for exchange_name in symbol_exchanges_dict['btcbrl']:
        base_url = f"https://api.cryptowat.ch/markets/{exchange_name}/btcbrl/summary"
        response = requests.get(base_url)
        if response.status_code == 200:
            data = response.json()
            data['exchange_name'] = exchange_name
            # current_datetime = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
            file_obj = io.BytesIO(str(data).encode())
            client.put_object('raw',f'exchanges/{exchange_name}.json',file_obj, file_obj.getbuffer().nbytes)
        else:
            print("Não foi possível obter o exchange")

now = datetime.now()

default_args = {
    "owner": "airflow",
    "depends_on_past": False,
    "start_date": datetime(now.year, now.month, now.day),
    "email": ["airflow@airflow.com"],
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=1)
}

dag = DAG(
    dag_id="get-exchanges",
    description="This DAG get the exchanges from cryptowatch api.",
    default_args=default_args,
    schedule_interval= timedelta(minutes=2),
    catchup = False,
    max_active_runs=1,
)

start = DummyOperator(task_id="start", dag=dag)

get_exchanges = PythonOperator(
        task_id='get_exchanges_and_save',
        python_callable=get_exchange_and_save,
        dag=dag
    )

end = DummyOperator(task_id="end", dag=dag)

start >> get_exchanges >> end