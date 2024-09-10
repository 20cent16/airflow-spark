# airflow-spark : if you want to use airflow with spark
## ready to use, enjoy ;-)

### Versions
Airflow : `2.10.1`

Spark : `bitnami/spark:latest`

### Initalize
Get source files

`git clone https://github.com/20cent16/airflow-spark.git`

Navigate to docker directory and execute

`mkdir -p ./apps ./dags ./logs ./plugins ./config`

**apps** = directory containing your programs

**dags** = directory containing your dags calling your programs

`echo -e "AIRFLOW_UID=$(id -u)" > .env`

We manually set AIRFLOW_UID to avoid warning during Airflow starting

### Start containers
Navigate to docker directory and execute

`docker compose up`

### Configure Airflow
UI : http://localhost:8080/connection/list/

Add a spark connection with following configuration:

**host** : spark://spark-master

**port** : 7077

### Useful and Optional : Clean existing docker files

#### Stop all running containers
`sudo docker stop $(sudo docker ps -aq)`
#### Remove all containers
`sudo docker rm $(sudo docker ps -aq)`
#### Remove all images
`sudo docker rmi $(sudo docker images -q)`
