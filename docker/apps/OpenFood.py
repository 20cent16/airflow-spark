import sys
import requests
import json
from pyspark import SparkConf, SparkContext
from pyspark.sql import SparkSession, DataFrame, Row

##########################
# You can configure master here if you do not pass the spark.master paramenter in conf
##########################
#master = "spark://spark:7077"
#conf = SparkConf().setAppName("Spark Hello World").setMaster(master)
#sc = SparkContext(conf=conf)
#spark = SparkSession.builder.config(conf=conf).getOrCreate()



spark = SparkSession.builder.getOrCreate()
# Create spark context
#sc = SparkContext()
sc = SparkContext.getOrCreate()

# Print result
print("---------------------------")
print("Début Script")
print("---------------------------")

headers = {"Content-Type": "application/json"}
url = "https://world.openfoodfacts.org/api/v2/search"
response = requests.get(url, headers=headers)

print("---------------------------")
print("Request ok")
print("---------------------------")

#Retrieve response in json (dict)
response_json=response.json()
#We only want products and we convert to string because spark.read.json only accept RDD of strings
products_string=json.dumps(response_json["products"])
#Creation of RDD
responseRDD = sc.parallelize([products_string])
#Dataframe creation
df = spark.read.json(responseRDD)
#df_view=df.createOrReplaceTempView("view")
df.select("_id").show()
