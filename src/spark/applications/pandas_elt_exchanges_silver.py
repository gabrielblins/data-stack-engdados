import sys
import subprocess

subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'minio', 'findspark'])

import os
import pandas as pd
from minio import Minio

client = Minio('minio1:9000',
               access_key='airflow',
               secret_key='sample_key',
               secure=False)
print("++++++++++++++++++++++++ CHEGOU AQUI UHUUUU CLIENTE MINIO +++++++++++++++++++++++++++++++")


for obj in client.list_objects('raw', prefix=f'exchanges/'):
    print(f"++++++++++++++++++++++++ CHEGOU AQUI UHUUUU {obj.object_name} +++++++++++++++++++++++++++++++")
    # exch = spark.read.json(f"s3a://raw/{obj.object_name}")
    response = client.get_object('raw', obj.object_name)
    json_data = response.read().decode('utf-8')
    print(f"++++++++++++++++++++++++ CHEGOU AQUI UHUUUU LEU +++++++++++++++++++++++++++++++")
    print(json_data)
    exch = pd.json_normalize(eval(json_data))
    print(f"++++++++++++++++++++++++ CHEGOU AQUI UHUUUU LEU COM SPARK +++++++++++++++++++++++++++++++")
    exch = exch.drop(exch.columns[exch.columns.str.startswith('allowance')], axis=1)
    exch['datetime'] = obj.last_modified
    print(f"++++++++++++++++++++++++ CHEGOU AQUI UHUUUU FLAT +++++++++++++++++++++++++++++++")

    # Save Pandas DataFrame as CSV file
    csv_data = exch.to_csv(index=False)

    # Upload CSV data to MinIO
    client.put_object(
        bucket_name='raw',
        object_name=f'{obj.object_name[:-5]}.csv',
        data=csv_data,
        length=len(csv_data),
        content_type="text/csv",
    )
    # df_flat.write.parquet(f"s3a://silver/{obj.object_name[:-5]}.parquet")
    print(f"++++++++++++++++++++++++ CHEGOU AQUI UHUUUU ESCREVEU +++++++++++++++++++++++++++++++")