import sys
import subprocess

subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'minio', 'findspark'])

import os
import pyspark
from pyspark.sql import SparkSession
from pyspark import SparkContext, SparkConf
from pyspark.sql.functions import *
from pyspark.sql.types import *
from minio import Minio

os.environ['PYARROW_IGNORE_TIMEZONE'] = str(1)

spark = SparkSession.builder \
    .appName("elt_raw_silver_exchanges") \
    .getOrCreate()
    # .config("spark.hadoop.fs.s3.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
    # .config("spark.hadoop.fs.s3a.aws.credentials.provider", "org.apache.hadoop.fs.s3a.SimpleAWSCredentialsProvider") \
    # .config("spark.hadoop.fs.s3a.access.key", 'airflow') \
    # .config("spark.hadoop.fs.s3a.secret.key", 'sample_key') \
    # .config("spark.hadoop.fs.s3a.proxy.host", "minio1") \
    # .config("spark.hadoop.fs.s3a.endpoint", "minio1") \
    # .config("spark.hadoop.fs.s3a.proxy.port", "9000") \
    # .config("spark.hadoop.fs.s3a.path.style.access", "true") \
    # .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
    

    

# def load_config(spark_context: SparkContext):
#     spark_context._jsc.hadoopConfiguration().set("fs.s3a.access.key", "airflow")
#     spark_context._jsc.hadoopConfiguration().set("fs.s3a.secret.key", "sample_key")
#     spark_context._jsc.hadoopConfiguration().set("fs.s3a.endpoint", "minio1:9000")
#     spark_context._jsc.hadoopConfiguration().set("fs.s3a.connection.ssl.enabled", "true")
#     spark_context._jsc.hadoopConfiguration().set("fs.s3a.path.style.access", "true")
#     spark_context._jsc.hadoopConfiguration().set("fs.s3a.attempts.maximum", "1")
#     spark_context._jsc.hadoopConfiguration().set("fs.s3a.connection.establish.timeout", "5000")
#     spark_context._jsc.hadoopConfiguration().set("fs.s3a.connection.timeout", "10000")

# load_config(spark.sparkContext)

client = Minio('minio1:9000',
               access_key='airflow',
               secret_key='sample_key',
               secure=False)
print("++++++++++++++++++++++++ CHEGOU AQUI UHUUUU CLIENTE MINIO +++++++++++++++++++++++++++++++")
def flatten_test(df, field, sep="_"):

    # compute Complex Fields (Arrays, Structs and Maptypes) in Schema
    complex_fields = dict(
        [
            (field.name, field.dataType)
            for field in df.schema.fields
            if type(field.dataType) == ArrayType
            or type(field.dataType) == StructType
            or type(field.dataType) == MapType
        ]
    )

    while len(complex_fields) != 0:
        col_name = list(complex_fields.keys())[0]
        # print ("Processing :"+col_name+" Type : "+str(type(complex_fields[col_name])))

        # if StructType then convert all sub element to columns.
        # i.e. flatten structs
        if type(complex_fields[col_name]) == StructType:
            expanded = [
                col(col_name + "." + k).alias(col_name + sep + k)
                for k in [n.name for n in complex_fields[col_name]]
            ]
            df = df.select("*", *expanded).drop(col_name)

        # if ArrayType then add the Array Elements as Rows using the explode function
        # i.e. explode Arrays
        elif type(complex_fields[col_name]) == ArrayType:
            df = df.withColumn(col_name, explode_outer(col_name))

        # if MapType then convert all sub element to columns.
        # i.e. flatten
        elif type(complex_fields[col_name]) == MapType:
            keys_df = df.select(explode_outer(map_keys(col(col_name)))).distinct()
            keys = list(map(lambda row: row[0], keys_df.collect()))
            key_cols = list(
                map(
                    lambda f: col(col_name).getItem(f).alias(str(col_name + sep + f)),
                    keys,
                )
            )
            drop_column_list = [col_name]
            df = df.select(
                [
                    col_name
                    for col_name in df.columns
                    if col_name not in drop_column_list
                ]
                + key_cols
            )

        # recompute remaining Complex Fields in Schema
        complex_fields = dict(
            [
                (field.name, field.dataType)
                for field in df.schema.fields
                if type(field.dataType) == ArrayType
                or type(field.dataType) == StructType
                or type(field.dataType) == MapType
            ]
        )

    return df

print("++++++++++++++++++++++++ CHEGOU AQUI UHUUUU CARREGOU FUNCAO +++++++++++++++++++++++++++++++")


for obj in client.list_objects('raw', prefix=f'exchanges/'):
    print(f"++++++++++++++++++++++++ CHEGOU AQUI UHUUUU {obj.object_name} +++++++++++++++++++++++++++++++")
    # exch = spark.read.json(f"s3a://raw/{obj.object_name}")
    response = client.get_object('raw', obj.object_name)
    json_data = response.read().decode('utf-8')
    print(f"++++++++++++++++++++++++ CHEGOU AQUI UHUUUU LEU +++++++++++++++++++++++++++++++")
    print(json_data)
    exch = spark.read.json(spark.sparkContext.parallelize([json_data]))
    print(f"++++++++++++++++++++++++ CHEGOU AQUI UHUUUU LEU COM SPARK +++++++++++++++++++++++++++++++")
    exch = exch.drop('allowance')
    fields = exch.select("result").schema.fields
    df_flat = flatten_test(exch,fields)
    df_flat = df_flat.withColumn('datetime', lit(obj.last_modified))
    print(f"++++++++++++++++++++++++ CHEGOU AQUI UHUUUU FLAT +++++++++++++++++++++++++++++++")
    pandas_df = df_flat.toPandas()

    # Save Pandas DataFrame as CSV file
    csv_data = pandas_df.to_csv(index=False)

    # Set MinIO bucket and object names
    bucket_name = "your_bucket_name"
    object_name = "your_file.csv"

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