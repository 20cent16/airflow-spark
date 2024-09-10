import sys
import requests
import json
from pyspark import SparkConf, SparkContext
from pyspark.sql import SparkSession

##########################
# You can configure master here if you do not pass the spark.master paramenter in conf
##########################
#master = "spark://spark:7077"
#conf = SparkConf().setAppName("Spark Hello World").setMaster(master)
#sc = SparkContext(conf=conf)
#spark = SparkSession.builder.config(conf=conf).getOrCreate()

# Create spark context
#ssc = SparkContext()

# Print result
print("---------------------------")
print("Bonjour Louisa, tu es punie")
print("---------------------------")

headers = {"Content-Type": "application/json"}
url = "https://world.openfoodfacts.org/api/v2/search"
response = requests.get(url, headers=headers)

print(response.content)