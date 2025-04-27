import sys
import requests
import json
from pyspark import SparkConf, SparkContext
from pyspark.sql import SparkSession, DataFrame, Row
from pyspark.sql.functions import explode, col, lit, collect_list, udf
from pyspark.sql.types import ArrayType, StringType
import itertools
from itertools import combinations
from dotenv import load_dotenv
import os

##########################
# You can configure master here if you do not pass the spark.master paramenter in conf
##########################
#master = "spark://spark:7077"
#conf = SparkConf().setAppName("Spark Hello World").setMaster(master)
#sc = SparkContext(conf=conf)
#spark = SparkSession.builder.config(conf=conf).getOrCreate()



spark = SparkSession.builder.config("spark.jars", "/opt/jars/postgresql-42.7.3.jar").getOrCreate()
# Create spark context
#sc = SparkContext()
sc = SparkContext.getOrCreate()

# Charger les variables du fichier .env
load_dotenv()

# Accéder aux variables
api_url = os.getenv("API_URL")
api_username = os.getenv("API_USERNAME")
api_password = os.getenv("API_PASSWORD")
db_url = os.getenv("DB_URL")
db_username = os.getenv("DB_USERNAME")
db_password = os.getenv("DB_PASSWORD")

# Print result
print("---------------------------")
print("Début Script")
print("---------------------------")

headers = {"Content-Type": "application/json"}

print("---------------------------")
print("Request Token")
print("---------------------------")

identifiants = {'identifier': api_username,'password': api_password}
response = requests.post(api_url+"auth/login", json=identifiants, headers=headers)

#Retrieve response in json (dict)
response_json=response.json()
token=response_json['accessToken']
userId=response_json['id']

print("---------------------------")
print("Token récupéré")
print("---------------------------")

headers = {"Authorization": "Bearer "+token}

responseCommunity = requests.get(api_url+"user/communities?UserId="+userId, headers=headers)
responseCommunity_json=responseCommunity.json()

# Récupérer l'id de la communauté Foot 5X5 Origins
community = [community["id"] for community in responseCommunity_json if community["name"] == 'Foot 5x5 Origins']
communityId=community[0]

print("---------------------------")
print("Community Id récupéré")
print("---------------------------")

# Récupérer les saisons
responseSeasons= requests.get(api_url+"community/"+communityId+"/seasons", headers=headers)
responseSeasons_json=responseSeasons.json()
seasonsId = [season['id'] for season in responseSeasons_json['seasons'] if season["name"].startswith("Annuel")]

print("---------------------------")
print("Saisons Id récupérés")
print("---------------------------")

# Initialiser la liste pour stocker les réponses
responseGamesAll = []

for seasonId in seasonsId:
    responseGames = requests.get(api_url+"community/"+communityId+"/season/"+seasonId+"/games", headers=headers)
    responseGamesAll.append(responseGames.json())
    #print("iteration")
    #break
#data = responseGames.json()

print("---------------------------")
print("Games récupérés")
print("---------------------------")

responseGamesString=json.dumps(responseGamesAll)
rdd = sc.parallelize([responseGamesString])

df = spark.read.json(rdd)

print("---------------------------")
print("Transformation en Dataframe et calculs")
print("---------------------------")

#df.printSchema()
#df.show(truncate=False)

# Exploser `games`
df_games = df.withColumn("game", explode(col("games")))

# Joueurs équipe A
df_team_a = df_games.withColumn("player", explode(col("game.playersTeamA"))).select(
    col("game.id").alias("game_id"),
    col("game.startDate").alias("game_date"),
    lit("A").alias("team"),
    col("player.id").alias("player_id"),
    col("player.name").alias("player_name"),
    col("game.scoreTeamA").alias("score")
    # ... ajoute d'autres colonnes selon ce que tu veux
)

# Joueurs équipe B
df_team_b = df_games.withColumn("player", explode(col("game.playersTeamB"))).select(
    col("game.id").alias("game_id"),
    col("game.startDate").alias("game_date"),
    lit("B").alias("team"),
    col("player.id").alias("player_id"),
    col("player.name").alias("player_name"),
    col("game.scoreTeamB").alias("score")
)

# Unionner les deux DataFrames pour avoir tous les joueurs (une ligne chacun)
df_resultats_player = df_team_a.unionByName(df_team_b)

#df_resultats_player.show(truncate=False)

#df_view=df_resultats_player.createOrReplaceTempView("v_games")
#spark.sql("select game_date,team,score,player_name from v_games order by game_date,team").show(50)

# 1. UDF pour générer les combinaisons de joueurs
def generate_combos(players):
    all_combos = []
    for r in range(1, len(players) + 1):
        for combo in combinations(sorted(players), r):
            all_combos.append(", ".join(combo))
    return all_combos

combo_udf = udf(generate_combos, ArrayType(StringType()))

# 2. Création de la vue intermédiaire avec toutes les combinaisons
df_combos = df_resultats_player.groupBy("game_date", "team", "score") \
    .agg(collect_list("player_name").alias("players")) \
    .withColumn("combinations", combo_udf("players"))

df_combos.createOrReplaceTempView("teams_raw_combos")

# 3. Création des vues pour l'équipe A et B avec les combos
spark.sql("""
CREATE OR REPLACE TEMP VIEW teamA_combos AS
SELECT game_date, score AS scoreA, explode(combinations) AS comboA
FROM teams_raw_combos
WHERE team = 'A'
""")

spark.sql("""
CREATE OR REPLACE TEMP VIEW teamB_combos AS
SELECT game_date, score AS scoreB, explode(combinations) AS comboB
FROM teams_raw_combos
WHERE team = 'B'
""")

# 4. Comparaison entre combo A et combo B par date
spark.sql("""
CREATE OR REPLACE TEMP VIEW combo_results AS
SELECT
  a.comboA,
  b.comboB,
  a.scoreA,
  b.scoreB,
  a.game_date,
  CASE
    WHEN a.scoreA > b.scoreB THEN 'victoire'
    WHEN a.scoreA = b.scoreB THEN 'nul'
    ELSE 'defaite'
  END AS resultA,
  CASE
    WHEN a.scoreA < b.scoreB THEN 'victoire'
    WHEN a.scoreA = b.scoreB THEN 'nul'
    ELSE 'defaite'
  END AS resultB
FROM teamA_combos a
JOIN teamB_combos b ON a.game_date = b.game_date
""")

# 5. Union de tous les résultats des combos A et B
spark.sql("""
CREATE OR REPLACE TEMP VIEW all_results AS
SELECT 
    DISTINCT size(split(comboA, ', ')) AS nb_joueurs,
    comboA AS combo,
    resultA as result,
    CASE WHEN resultA = 'victoire' THEN 1 ELSE 0 END AS victoires,
    CASE WHEN resultA = 'nul' THEN 1 ELSE 0 END AS nuls,
    CASE WHEN resultA = 'defaite' THEN 1 ELSE 0 END AS defaites,
    game_date 
FROM combo_results
UNION ALL
SELECT 
    DISTINCT size(split(comboB, ', ')) AS nb_joueurs,
    comboB AS combo,
    resultB as result,
    CASE WHEN resultB = 'victoire' THEN 1 ELSE 0 END AS victoires,
    CASE WHEN resultB = 'nul' THEN 1 ELSE 0  END AS nuls,
    CASE WHEN resultB = 'defaite' THEN 1 ELSE 0 END AS defaites,
    game_date 
FROM combo_results
""")

df_combo_all_results=spark.sql("""
SELECT
*
FROM all_results
""")

# 6. Agrégation des résultats : nombre de victoires, nuls, défaites
df_combo_stats = spark.sql("""
SELECT
  nb_joueurs,
  combo,
  SUM(victoires) as victoires,
  SUM(nuls) as nuls,
  SUM(defaites) as defaites,
  COUNT(*) as matches,
  ROUND(SUM(victoires) * 100.0 / COUNT(*), 1) AS tx_victoires,
  ROUND(SUM(nuls) * 100.0 / COUNT(*), 1) AS tx_nuls,
  ROUND(SUM(defaites) * 100.0 / COUNT(*), 1) AS tx_defaites
FROM all_results
GROUP BY combo,nb_joueurs
""")



# Calcul série
df_series = spark.sql("""
WITH ordered_games AS (
    SELECT
        nb_joueurs,
        combo,
        game_date,
        result,
        ROW_NUMBER() OVER (PARTITION BY combo ORDER BY game_date) AS rn,
        SUM(
            CASE 
                WHEN LAG(result) OVER (PARTITION BY combo ORDER BY game_date) = result THEN 0
                ELSE 1
            END
        ) OVER (PARTITION BY combo ORDER BY game_date ROWS UNBOUNDED PRECEDING) AS group_id
    FROM all_results
),
grouped_streaks AS (
    SELECT
        nb_joueurs,
        combo,
        COUNT(*) AS nb_matches,
        CASE result
            WHEN 'victoire' THEN 'Victoires'
            WHEN 'nul' THEN 'Nuls'
            WHEN 'defaite' THEN 'Défaites'
        END AS resultat,
        MIN(game_date) AS debut,
        MAX(game_date) AS fin
    FROM ordered_games
    GROUP BY nb_joueurs,combo, result, group_id
)
SELECT g.*, case when g.fin=d.last_game_date then 'Oui' else 'Non' end as en_cours
FROM grouped_streaks g
INNER JOIN (SELECT combo,MAX(game_date) as last_game_date FROM all_results GROUP BY combo) d
ON g.combo=d.combo
ORDER BY combo, debut;
""")

# confrontations
df_combo_confrontations = spark.sql("""

SELECT
  nb_joueurs,
  combo,
  nb_joueurs_opposant,
  opposant,
  SUM(victoires) as victoires,
  SUM(nuls) as nuls,
  SUM(defaites) as defaites,
  CAST(SUM(nb_matches) AS INTEGER) as nb_matches,
  ROUND(SUM(victoires) * 100.0 / SUM(nb_matches), 1) AS tx_victoires,
  ROUND(SUM(nuls) * 100.0 / SUM(nb_matches), 1) AS tx_nuls,
  ROUND(SUM(defaites) * 100.0 / SUM(nb_matches), 1) AS tx_defaites
FROM
(
SELECT
  size(split(comboA, ', ')) AS nb_joueurs,
  comboA AS combo,
  size(split(comboB, ', ')) AS nb_joueurs_opposant,
  comboB AS opposant,
  COUNT(*) FILTER (WHERE resultA = 'victoire') AS victoires,
  COUNT(*) FILTER (WHERE resultA = 'nul') AS nuls,
  COUNT(*) FILTER (WHERE resultA = 'defaite') AS defaites,
  COUNT(*) AS nb_matches
FROM combo_results
GROUP BY nb_joueurs,comboA,nb_joueurs_opposant,comboB
UNION ALL
SELECT
  size(split(comboB,', ')) AS nb_joueurs,
  comboB AS combo,
  size(split(comboA, ', ')) AS nb_joueurs_opposant,
  comboA AS opposant,
  COUNT(*) FILTER (WHERE resultB = 'victoire') AS victoires,
  COUNT(*) FILTER (WHERE resultB = 'nul') AS nuls,
  COUNT(*) FILTER (WHERE resultB = 'defaite') AS defaites,
  COUNT(*) AS nb_matches
FROM combo_results
GROUP BY nb_joueurs,comboB,nb_joueurs_opposant,comboA
)A
GROUP BY nb_joueurs,nb_joueurs_opposant,combo, opposant;
""")


# Paramètres de connexion
jdbc_url = "jdbc:postgresql://db_url/buddies?ssl=require"
properties = {
    "user": "db_user",
    "password": "db_password",
    "driver": "org.postgresql.Driver"
}

# Ajout d'une colonne date_insert
from pyspark.sql.functions import current_timestamp

df_combo_stats_with_date = df_combo_stats.withColumn("date_insert", current_timestamp())
df_combo_all_results_with_date=df_combo_all_results.withColumn("date_insert", current_timestamp())
df_series_with_date=df_series.withColumn("date_insert", current_timestamp())
df_combo_confrontations_with_date=df_combo_confrontations.withColumn("date_insert", current_timestamp())

print("---------------------------")
print("Ecriture dans Postgres")
print("---------------------------")

# Écriture dans la table Postgres
df_combo_all_results_with_date.write \
    .jdbc(url=jdbc_url, table="combo_all_results", mode="overwrite",properties=properties)

df_combo_stats_with_date.write \
    .jdbc(url=jdbc_url, table="combo_stats", mode="overwrite",properties=properties)

df_series_with_date.write \
    .jdbc(url=jdbc_url, table="series", mode="overwrite",properties=properties)

df_combo_confrontations_with_date.write \
    .jdbc(url=jdbc_url, table="combo_confrontations", mode="overwrite",properties=properties)

print("---------------------------")
print("Fin du script")
print("---------------------------")
