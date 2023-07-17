import os
from airflow import DAG
from airflow.operators.dummy_operator import DummyOperator
from airflow.sensors.external_task import ExternalTaskSensor
# from airflow.contrib.operators.spark_submit_operator import SparkSubmitOperator
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta

def etl_gold_exchanges():

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

    df = pd.DataFrame()

    for obj in client.list_objects('silver', prefix=f'exchanges/'):
        # exch = spark.read.json(f"s3a://raw/{obj.object_name}")
        response = client.get_object('silver', obj.object_name)
        csv_data = response.read().decode('utf-8')
        df_tmp = pd.read_csv(io.StringIO(csv_data))
        
        df = pd.concat([df, df_tmp])


    # Save Pandas DataFrame as CSV file
    csv_data = df.to_csv(index=False)
    fl = io.BytesIO(str(csv_data).encode())
    # Upload CSV data to MinIO
    client.put_object(
        bucket_name='gold',
        object_name=f'exchanges_btcbrl.csv',
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
    dag_id="elt_silver_gold_exchanges",
    description="This DAG runs a etl to transform and move exchanges data from silver to gold.", 
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
        task_id='etl_gold_exchanges',
        python_callable=etl_gold_exchanges,
        dag=dag
    )

end = DummyOperator(task_id="end", dag=dag)


# Configure as dependências entre as tarefas
start >> etl_exchanges >> end
