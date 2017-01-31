# Creating an OSM-based Gazetteer for TDM

What if you could click on any point on Earth, and have direct access to all of humanity's knowledge of that location?

While this is hardly a novel concept (see EarthCube, UW version of EarthCube), it is an idea being explored by [GeoDeepDive](https://geodeepdive.org). In addition to functioning as a TDM-ready library of the future, GeoDeepDive seeks to expand knowledge by "tagging" published literature with known entities -- for example, by ingesting roughly 350,000 names from the taxonomic hierarchy of the [Paleobiology Database](https://paleobiodb.org), we can quickly identify all documents that discuss _Felis_. Conversely, if you are reading a paper and come across _Dimerocrinites cf. pentangularis_, we can immediately inform you that it is indeed a taxonomic name and belongs to _Crinoidea_.

In contrast to the [named-entity recognition](https://en.wikipedia.org/wiki/Named-entity_recognition) done by [Stanford CoreNLP](http://stanfordnlp.github.io/CoreNLP/), these entity tags come with hierarchies and links to authoritative databases for further exploration. This hierarchy allows us to increase precision of tags by leveraging hierarchy to remove ambiguity. For example, if the place "Springfield" is present and there are 50 matches, we can use the presence of other terms in the text to disambiguate which Springfield is being referenced.


http://planet.osm.org
http://planet.osm.org/pbf/planet-170116.osm.pbf

md5 - eaedcb7528c9130846fa0f40fa718e93  planet-170116.osm.pbf

````shell
sudo apt-get update
sudo apt-get upgrade

sudo apt-get install osm2pgsql

sudo sh -c 'echo "deb http://apt.postgresql.org/pub/repos/apt trusty-pgdg main" >> /etc/apt/sources.list'
wget --quiet -O - http://apt.postgresql.org/pub/repos/apt/ACCC4CF8.asc | sudo apt-key add -
sudo apt-get update
sudo apt-get install postgresql-9.5-postgis-2.2 postgresql-contrib-9.5
````

vi /etc/postgresql/9.5/main/pg_hba.conf
< trust everything>

vi /etc/postgresql/9.5/main/postgresql.conf

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

mkdir /data/postgresql/main
mv -f /var/lib/postgresql/9.5/main /data/postgresql/main
sudo chown -R postgres:postgres /data/postgresql/main

sudo service postgresql restart

mkdir /data/osm
cd /data/osm
curl -o planet.osm.pbf http://planet.osm.org/pbf/planet-latest.osm.pbf

createdb -U postgres gill
psql -U postgres fill -c "CREATE EXTENSION postgis; CREATE EXTENSION hstore;"

osm2pgsql -d osm -U postgres -k -s -C 22000 planet.osm.pbf

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


pg_dump -x -c -O -t places_polygons -t places_points -t places_lines -U postgres osm | gzip > osm_subset.sql.gz
scp -p 2200 osm_subset.sql.gz jczaplewski@teststrata.geology.wisc.edu:/Users/jczaplewski
gunzip < osm_subset.sql.gz | psql -U john gill

UPDATE places_polygons SET geom = ST_Transform(ST_Union(geom), 4326) GROUP BY osm_id;

CREATE TABLE place_polygons_grouped AS
SELECT osm_id,
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
GROUP BY osm_id, name,
boundary,
admin_level,
"natural",
tourism,
waterway,
leisure,
geological,
tags;

create index on place_polygons_grouped using gist (geom);


CREATE TABLES places (
  place_id uuid primary key default uuid_generate_v4(),
  osm_id bigint,
  name text,
  type text,
  admin-1 uuid,
  admin-2 uuid,
  admin-3 uuid,
  admin-4 uuid,
  admin-5 uuid,
  admin-6 uuid,
  admin-7 uuid,
  admin-8 uuid,
  admin-9 uuid,
  admin-10 uuid,
  tags hstore,
  geom geometry
);

CREATE TABLE places (
  place_id uuid primary key default uuid_generate_v4(),
  osm_id bigint,
  name text,
  abbrev text,
  boundary text,
  geom geometry
)

CREATE TABLE names (
  place_id integer not null primary key,
  type text,
  lang text,
  name text
);

# DROP TABLE planet_osm_roads
# tags wanted:
#    - anything that starts with 'name:'
#    - iata (airport code)
#    - short_name
#    - alt_name
#    - official_name
#    - old_name
#    - ref (abbreviation for state/province)
#    - ISO3166-1 (country abbreviation)



# Ignore all admin_level = '0' and '1'

# If 'name' contains 'Town/Village/City of' and no official name, set official_name = name and replace the bullshit
# Create new name column with Replace of 'Town/Village/City of' with nothing

# natural IN ['water', 'bay', 'lagoon', 'lake', 'marsh', 'natural', 'reservoir', 'river', 'glacier', 'beach', 'coastline', 'spring', 'hot_spring', 'geyser', 'peak', 'volcano', 'valley', 'ridge', 'arete', 'cliff', 'saddle', 'rock', 'stone', 'sinkhole'] OR IS NULL

# tourism = 'viewpoint' OR IS NULL

# shop is NULL
# building is null

# waterway IN ['river', 'stream', 'canal', 'dam', 'waterfall'] OR IS NULL

# boundary IN ['administrative', 'historic', 'national_park', 'protected_area'] OR IS NULL

# geological IN ['moraine', 'outcrop', 'paleontological_site'] OR IS NULL


# For each,

````sql
CREATE TABLE places AS
SELECT *
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

CREATE TABLE place_names (
    place_id integer not null,
    name text not null,
    lang text
);
CREATE INDEX ON place_names (place_id);
````
