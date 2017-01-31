# Creating an OSM-based Gazetteer for TDM

What if you could click on any point on Earth, and have direct access to all of humanity's knowledge of that location?

While this is hardly a novel concept (see EarthCube, UW version of EarthCube), it is an idea being explored by [GeoDeepDive](https://geodeepdive.org). In addition to functioning as a TDM-ready library of the future, GeoDeepDive seeks to expand knowledge by "tagging" published literature with known entities -- for example, by ingesting roughly 350,000 names from the taxonomic hierarchy of the [Paleobiology Database](https://paleobiodb.org), we can quickly identify all documents that discuss _Felis_. Conversely, if you are reading a paper and come across _Dimerocrinites cf. pentangularis_, we can immediately inform you that it is indeed a taxonomic name and belongs to _Crinoidea_.

In contrast to the [named-entity recognition](https://en.wikipedia.org/wiki/Named-entity_recognition) done by [Stanford CoreNLP](http://stanfordnlp.github.io/CoreNLP/), these entity tags come with hierarchies and links to authoritative databases for further exploration. This hierarchy allows us to increase precision of tags by leveraging hierarchy to remove ambiguity. For example, if the place "Springfield" is present and there are 50 matches, we can use the presence of other terms in the text to disambiguate which Springfield is being referenced.

[The data](http://planet.osm.org/pbf/planet-170116.osm.pbf) (`md5 - eaedcb7528c9130846fa0f40fa718e93 `) was downloaded on 2017-01-23 from http://planet.osm.org.

````shell
sudo apt-get update
sudo apt-get upgrade

sudo apt-get install osm2pgsql

sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt trusty-pgdg main" >> /etc/apt/sources.list'
wget --quiet -O - http://apt.postgresql.org/pub/repos/apt/ACCC4CF8.asc | sudo apt-key add -
sudo apt-get update
sudo apt-get install postgresql-9.5-postgis-2.2 postgresql-contrib-9.5
````

````shell
vi /etc/postgresql/9.5/main/pg_hba.conf
````

trust everything (safe for our purposes....)

````shell
vi /etc/postgresql/9.5/main/postgresql.conf
````

Update the follow configuration parameters. Your specific values may differ depending on the system configuration. Enter your system information in to [pgtune](http://pgtune.leopard.in.ua) for an estimate of proper values for your system.

```
data_directory = '/var/lib/postgresql/9.5/main'
data_directory = '/data/postgresql/main'
max_connections = 20
shared_buffers = 11GB
work_mem = 288MB
maintenance_work_mem = 2GB
wal_buffers = 16MB
min_wal_size = 4GB
max_wal_size = 8GB
checkpoint_completion_target = 0.9
effective_cache_size = 10GB
default_statistics_target = 500
````

On CCI we need to move Postgres's data directory to the large attached volume.

````shell
mkdir /data/postgresql/main
mv -f /var/lib/postgresql/9.5/main /data/postgresql/main
sudo chown -R postgres:postgres /data/postgresql/main

sudo service postgresql restart
````

Time to download the data! It will be about 36GB and take anywhere for 10 minutes to 3 hours to download.

````shell
mkdir /data/osm
cd /data/osm
curl -o planet.osm.pbf http://planet.osm.org/pbf/planet-latest.osm.pbf
````

Next, create a database to hold the data and import it. `osm2pgsql` took 58 hours to complete this task.

````shell
createdb -U postgres gill
psql -U postgres gill -c "CREATE EXTENSION postgis; CREATE EXTENSION hstore;"

osm2pgsql -d osm -U postgres -k -s -C 22000 planet.osm.pbf
````

Once imported, create subsets of the data that we are interested in. The following criteria must be met:

+ `name` is not `NULL`
+ `shop` is `NULL`
+ `building` is `NULL`

Additionally, at least one of the following conditions must be met:

+ `admin_level` in ['2', '3', '4', '5', '6', '7', '8', '9', '10']
+ natural IN ['water', 'bay', 'lagoon', 'lake', 'marsh', 'natural', 'reservoir', 'river', 'glacier', 'beach', 'coastline', 'spring', 'hot_spring', 'geyser', 'peak', 'volcano', 'valley', 'ridge', 'arete', 'cliff', 'saddle', 'rock', 'stone', 'sinkhole'] OR IS NULL
+ `tourism` = 'viewpoint' or is `NULL`
+ `waterway` in ['river', 'stream', 'canal', 'dam', 'waterfall']
+ `boundary` IN ['administrative', 'historic', 'national_park', 'protected_area']
+ `geological` IN ['moraine', 'outcrop', 'paleontological_site']



````sql
CREATE TABLE places_polygons AS
SELECT
  osm_id,
  name,
  boundary,
  admin_level,
  "natural",
  tourism,
  waterway,
  leisure,
  tags->'geological' AS geological,
  tags,
  way AS geom
FROM planet_osm_polygon
WHERE
  name IS NOT NULL AND
  shop IS NULL AND
  building IS NULL AND
  ("natural" IN ('water', 'bay', 'lagoon', 'lake', 'marsh', 'natural', 'reservoir', 'river', 'glacier', 'beach', 'coastline', 'spring', 'hot_spring', 'geyser', 'peak', 'volcano', 'valley', 'ridge', 'arete', 'cliff', 'saddle', 'rock', 'stone', 'sinkhole') OR
  tourism = 'viewpoint' OR
  waterway IN ('river', 'stream', 'canal', 'dam', 'waterfall') OR
  boundary IN ('administrative', 'historic', 'national_park', 'protected_area') OR
  tags->'geological' IS NOT NULL OR
  leisure = 'park' OR
  admin_level IN ('2', '3', '4', '5', '6', '7', '8', '9', '10', NULL));

CREATE TABLE places_points AS
SELECT
  osm_id,
  name,
  boundary,
  admin_level,
  "natural",
  tourism,
  waterway,
  leisure,
  tags->'geological' AS geological,
  tags,
  way AS geom
FROM planet_osm_point
WHERE
  name IS NOT NULL AND
  shop IS NULL AND
  building IS NULL AND
  ("natural" IN ('water', 'bay', 'lagoon', 'lake', 'marsh', 'natural', 'reservoir', 'river', 'glacier', 'beach', 'coastline', 'spring', 'hot_spring', 'geyser', 'peak', 'volcano', 'valley', 'ridge', 'arete', 'cliff', 'saddle', 'rock', 'stone', 'sinkhole') OR
  tourism = 'viewpoint' OR
  waterway IN ('river', 'stream', 'canal', 'dam', 'waterfall') OR
  boundary IN ('administrative', 'historic', 'national_park', 'protected_area') OR
  tags->'geological' IS NOT NULL OR
  leisure = 'park' OR
  admin_level IN ('2', '3', '4', '5', '6', '7', '8', '9', '10', NULL));

CREATE TABLE places_lines AS
SELECT
  osm_id,
  name,
  boundary,
  admin_level,
  "natural",
  tourism,
  waterway,
  leisure,
  tags->'geological' AS geological,
  tags,
  way AS geom
FROM planet_osm_line
WHERE
  name IS NOT NULL AND
  shop IS NULL AND
  building IS NULL AND
  ("natural" IN ('water', 'bay', 'lagoon', 'lake', 'marsh', 'natural', 'reservoir', 'river', 'glacier', 'beach', 'coastline', 'spring', 'hot_spring', 'geyser', 'peak', 'volcano', 'valley', 'ridge', 'arete', 'cliff', 'saddle', 'rock', 'stone', 'sinkhole') OR
  tourism = 'viewpoint' OR
  waterway IN ('river', 'stream', 'canal', 'dam', 'waterfall') OR
  boundary IN ('administrative', 'historic', 'national_park', 'protected_area') OR
  tags->'geological' IS NOT NULL OR
  leisure = 'park' OR
  admin_level IN ('2', '3', '4', '5', '6', '7', '8', '9', '10', NULL));
````

If you want to move this extract to a different machine for further processing, you can dump it as so:

````shell
pg_dump -x -c -O -t places_polygons -t places_points -t places_lines -U postgres gill | gzip > osm_subset.sql.gz
````

Next, condense the polygon layer

````sql
CREATE TABLE place_polygons_grouped AS
SELECT
  osm_id,
  name,
  boundary,
  admin_level,
  "natural",
  tourism,
  waterway,
  leisure,
  geological,
  tags,
  ST_Transform(ST_Union(geom), 4326) AS geom
FROM places_polygons
GROUP BY
  osm_id,
  name,
  boundary,
  admin_level,
  "natural",
  tourism,
  waterway,
  leisure,
  geological,
  tags;

CREATE INDEX ON place_polygons_grouped USING gist (geom);
````

Create tables to store processed data:

````sql
CREATE TABLES lookup_places (
  place_id integer not null,
  name text,
  type text,
  admin1 integer,
  admin2 integer,
  admin3 integer,
  admin4 integer,
  admin5 integer,
  admin6 integer,
  admin7 integer,
  admin8 integer,
  admin9 integer,
  admin10 integer,
  tags hstore,
  geom geometry
);

CREATE TABLE places (
  place_id serial primary key not null,
  osm_id bigint not null,
  name text not null,
  admin_level integer,
  boundary text,
  nature text,
  tourism text,
  waterway text,
  leisure text,
  geological text,
  names hstore,
  geom geometry not null
);

CREATE TABLE names (
  place_id integer not null,
  type text,
  lang text,
  name text
);
````

tags wanted:
  + anything that starts with `name:`
  + `iata` (airport code)
  + `short_name`
  + `alt_name`
  + `official_name`
  + `old_name`
  + `ref` (abbreviation for state/province)
  + `ISO3166-1` (country abbreviation)
