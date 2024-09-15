import sys
from pyspark import SparkConf, SparkContext
from pyspark.sql import SparkSession, DataFrame

##########################
# You can configure master here if you do not pass the spark.master paramenter in conf
##########################
#master = "spark://spark:7077"
#conf = SparkConf().setAppName("Spark Hello World").setMaster(master)
#sc = SparkContext(conf=conf)
#spark = SparkSession.builder.config(conf=conf).getOrCreate()

# Create spark context
#sc = SparkContext()
spark = SparkSession.builder.getOrCreate()

print(spark)

# Print result
print("---------------------------")
print("Bonjour Louisa, tu es punie")
print("---------------------------")

from typing import List
from pyspark.sql.types import StructType, StructField, StringType

data: List = [("Diamant_1A","TopDiamant"),
              ("Diamant_2B","Diamants pour toujours"),
              ("Diamant_3C","Mes diamants préférés"),
              ("Diamant_4D","Diamants que j'aime"),
              ("Diamant_5E","TopDiamant")
]

schema: StructType = StructType([
    StructField("reference",StringType(),True),
    StructField("marque",StringType(),True),
    ])

dataframe: DataFrame = spark.createDataFrame(data=data,schema=schema)
