# airflow-spark

### Start containers
Navigate to docker directory and execute

`sudo docker compose up`

### Useful : Clean existing docker files

#### Stop all running containers
`sudo docker stop $(sudo docker ps -aq)`
#### Remove all containers
`sudo docker rm $(sudo docker ps -aq)`
#### Remove all images
`sudo docker rmi $(sudo docker images -q)`
