import os
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.sensors.external_task import ExternalTaskSensor
# from airflow.contrib.operators.spark_submit_operator import SparkSubmitOperator
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta

def etl_silver_exchanges():

    import sys
    import subprocess

    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'minio'])

    import os, io
    import pandas as pd
    from minio import Minio

    client = Minio('minio1:9000',
                access_key='airflow',
                secret_key='sample_key',
                secure=False)


    for obj in client.list_objects('raw', prefix=f'exchanges/'):
        # exch = spark.read.json(f"s3a://raw/{obj.object_name}")
        response = client.get_object('raw', obj.object_name)
        json_data = response.read().decode('utf-8')
        print(json_data)
        exch = pd.json_normalize(eval(json_data))
        exch = exch.drop(exch.columns[exch.columns.str.startswith('allowance')], axis=1)
        exch['datetime'] = obj.last_modified
        # Save Pandas DataFrame as CSV file
        csv_data = exch.to_csv(index=False)
        fl = io.BytesIO(str(csv_data).encode())
        # Upload CSV data to MinIO
        client.put_object(
            bucket_name='silver',
            object_name=f'{obj.object_name[:-5]}.csv',
            data=fl,
            length=fl.getbuffer().nbytes,
            content_type="text/csv",
        )

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
    dag_id="elt_raw_silver_exchanges",
    description="This DAG runs a etl to transform and move exchanges data from raw to silver.", 
    default_args=default_args,
    schedule_interval=timedelta(minutes=2),
    catchup = False,
    max_active_runs=1,
)
start = DummyOperator(task_id="start", dag=dag)
# Defina a tarefa inicial da segunda DAG
# spark_job = SparkSubmitOperator(
#     task_id="spark_job",
#     # Spark application path created in airflow and spark cluster
#     application="/usr/local/spark/applications/spark_elt_exchanges_silver.py",
#     name=spark_app_name,
#     conn_id=spark_conn,
#     verbose=1,
#     conf={"spark.master": spark_master},
#     packages="com.amazonaws:aws-java-sdk-bundle:1.11.819,org.apache.hadoop:hadoop-aws:3.2.0",
#     dag=dag)
etl_exchanges = PythonOperator(
        task_id='etl_silver_exchanges',
        python_callable=etl_silver_exchanges,
        dag=dag
    )

end = DummyOperator(task_id="end", dag=dag)


# Configure as dependências entre as tarefas
start >> etl_exchanges >> end
