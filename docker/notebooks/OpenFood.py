import sys
import requests
import json
import psutil
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

#Initialize empty list
List=[]

#Loop to browse result page per page
for i in range(1,15):
    print("Traitement de la page: ",i)
    params = {"page" : i, "page_size" : 100}
    response = requests.get(url, headers=headers, params=params)

    #Retrieve response in json (dict)
    response_json=response.json()
    #We only want products and we convert to string because spark.read.json only accept RDD of strings
    products_string=json.dumps(response_json["products"])

    #Add to the List
    List+=[products_string]

#Creation of RDD
RDD=sc.parallelize(List)

#Dataframe creation
df = spark.read.json(RDD).repartition(10)
df_view=df.createOrReplaceTempView("v_products")
spark.sql("select count(*) from v_products").show()

#df_view=df.createOrReplaceTempView("view")
#df.select("_id").show()
