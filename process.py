'''
CREATE DATABASE wof;
CREATE EXTENSION postgis;
CREATE EXTENSION hstore;

CREATE TABLE places (
  wof_id integer NOT NULL PRIMARY KEY, /* wof:id */
  name text NOT NULL, /* wof:name */
  name_formal text /* ne:formal_en */,
  placetype text, /* wof:placetype */
  iso2 text, /* wof:country */
  iso3 text, /* wof:country_alpha3 */
  continent integer, /* wof:hierarchy -> continent_id */
  country integer,  /* wof:hierarchy -> country_id */
  region integer, /* wof:hierarchy -> region_id */
  county integer, /* wof:hierarchy -> county_id */
  locality integer, /* wof:hierarchy -> locality_id */
  other_names hstore, /* name:lng_x_preferred */
  geom geometry
);

CREATE INDEX ON places (name);
CREATE INDEX ON places (continent);
CREATE INDEX ON places (country);
CREATE INDEX ON places (region);
CREATE INDEX ON places (county);
CREATE INDEX ON places (locality);
CREATE INDEX ON places USING GiST (geom);

'''
import os, sys
import csv
import json
from subprocess import call
import requests
import psycopg2
import psycopg2.extras

connection = psycopg2.connect(dbname='wof', user='john', host='localhost', port=5432)
cursor = connection.cursor()

psycopg2.extras.register_hstore(connection)


# via http://stackoverflow.com/a/16695277/1956065
def download(url):
    local_filename = url.split('/')[-1]
    r = requests.get(url)
    with open(local_filename, 'wb') as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:
                f.write(chunk)

    # Untar and unzip the downloaded file, and then delete the tarball
    call(['tar -xjf %(name)s && rm %(name)s' % {'name': local_filename}], shell='True')
    return


sources = [
    {
        'name': 'continents',
        'url': 'https://whosonfirst.mapzen.com/bundles/wof-continent-latest-bundle.tar.bz2'
    }, {
        'name': 'countries',
        'url': 'https://whosonfirst.mapzen.com/bundles/wof-country-latest-bundle.tar.bz2'
    }, {
        'name': 'regions',
        'url': 'https://whosonfirst.mapzen.com/bundles/wof-region-latest-bundle.tar.bz2'
    }, {
        'name': 'counties',
        'url': 'https://whosonfirst.mapzen.com/bundles/wof-county-latest-bundle.tar.bz2'
    }, {
        'name': 'localities',
        'url': 'https://whosonfirst.mapzen.com/bundles/wof-locality-latest-bundle.tar.bz2'
    }
]

for source in sources:
    print 'Downloading %s' % source['name']
    # Download and extract the data
    download(source['url'])

    folder = source['url'].split('/')[-1].split('.')[0]
    metadata_name = folder.replace('-bundle', '') + '.csv'

    print 'Processing %s' % source['name']
    with open(folder + '/' + metadata_name, 'rb') as meta:
        reader = csv.DictReader(meta)
        # Iterate on each feature in the CSV
        for feature in reader:
            if feature['deprecated'] != '':
                continue
            with open(folder + '/data/' + feature['path']) as raw_json:
                geojson = json.load(raw_json)

                data = {
                    'wof_id': geojson['properties']['wof:id'] if 'wof:id' in geojson['properties'] else '',
                    'name': geojson['properties']['wof:name'] if 'wof:name' in geojson['properties'] else '',
                    'name_formal': geojson['properties']['ne:formal_en'] if 'ne:formal_en' in geojson['properties'] else '',
                    'placetype': geojson['properties']['wof:placetype'] if 'wof:placetype' in geojson['properties'] else '',
                    'abbrev': geojson['properties']['wof:country'] if 'wof:country' in geojson['properties'] else '',
                    'abbrev3': geojson['properties']['wof:country_alpha3'] if 'wof:country_alpha3' in geojson['properties'] else '',
                    'continent': geojson['properties']['wof:hierarchy'][0]['continent_id'] if 'wof:hierarchy' in geojson['properties'] and len(geojson['properties']['wof:hierarchy']) == 1 and 'continent_id' in geojson['properties']['wof:hierarchy'][0] else None,
                    'country': geojson['properties']['wof:hierarchy'][0]['country_id'] if 'wof:hierarchy' in geojson['properties'] and len(geojson['properties']['wof:hierarchy']) == 1 and 'country_id' in geojson['properties']['wof:hierarchy'][0] else None,
                    'region': geojson['properties']['wof:hierarchy'][0]['region_id'] if 'wof:hierarchy' in geojson['properties'] and len(geojson['properties']['wof:hierarchy']) == 1 and 'region_id' in geojson['properties']['wof:hierarchy'][0] else None,
                    'county': geojson['properties']['wof:hierarchy'][0]['county_id'] if 'wof:hierarchy' in geojson['properties'] and len(geojson['properties']['wof:hierarchy']) == 1 and 'county_id' in geojson['properties']['wof:hierarchy'][0] else None,
                    'locality': geojson['properties']['wof:hierarchy'][0]['locality_id'] if 'wof:hierarchy' in geojson['properties'] and len(geojson['properties']['wof:hierarchy']) == 1 and 'locality_id' in geojson['properties']['wof:hierarchy'][0] else None,
                    'other_names': {},
                    'geom': json.dumps(geojson['geometry']),
                }

                for prop in geojson['properties']:
                    if prop[0:4] == 'name' and 'preferred' in prop:
                        language = prop.split('_')[0].replace('name:', '')
                        data['other_names'][language] = geojson['properties'][prop][0]

                cursor.execute("""
                INSERT INTO places (wof_id, name, name_formal, placetype, iso2, iso3, continent, country, region, county, locality, other_names, geom) VALUES (%(wof_id)s, %(name)s, %(name_formal)s, %(placetype)s, %(abbrev)s, %(abbrev3)s, %(continent)s, %(country)s, %(region)s, %(county)s, %(locality)s, %(other_names)s, ST_GeomFromGeoJSON(%(geom)s))
                """, data)
                connection.commit()
