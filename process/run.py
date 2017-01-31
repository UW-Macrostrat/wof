import psycopg2
from psycopg2.extensions import AsIs
import psycopg2.extras
import sys
import os
import yaml

with open(os.path.join(os.path.dirname(__file__), './credentials.yml'), 'r') as f:
    credentials = yaml.load(f)

try:
  connection = psycopg2.connect(dbname=credentials['pg_db'], user=credentials['pg_user'], host=credentials['pg_host'], port=credentials['pg_port'], cursor_factory=psycopg2.extras.DictCursor)
  psycopg2.extras.register_hstore(connection)
except:
  print "Could not connect to database: ", sys.exc_info()[1]
  sys.exit()

cursor = connection.cursor()
update_cursor = connection.cursor()

good_tags = ['iata', 'short_name', 'alt_name', 'official_name', 'old_name', 'ref', 'ISO3166-1']

tag_map = {
    'iata': 'abbrev',
    'short_name': 'abbrev',
    'ref': 'abbrev',
    'ISO3166-1': 'abbrev',
    'alt_name': 'alt_name',
    'official_name': 'official_name',
    'old_name': 'old_name'
}

def is_valid_tag(tag):
    if tag[0:4] == 'name' or tag in good_tags:
        return True

    return False


cursor.execute('SELECT osm_id, name, tags FROM place_polygons_grouped LIMIT 50')

for place in cursor:
    new_tags = {}
    for key, val in place['tags'].iteritems():
        if is_valid_tag(key):
            new_tags[key] = val

    if 'Village of' in place['name'] or 'Town of' in place['name'] or 'City of' in place['name']:
        new_tags['official_name'] = place['name']
        new_name = place['name'].replace('Village of ', '').replace('Town of ', '').replace('City of ', '')
    else:
        new_name = place['name']

    print place, new_tags
    update_cursor.execute("""
        INSERT INTO places (osm_id, name, admin_level, boundary, nature, tourism, waterway, leisure, geological, names, geom)
        SELECT osm_id, %(name)s, admin_level::int, boundary, \"natural\", tourism, waterway, leisure, geological, %(hstore)s, geom
        FROM place_polygons_grouped
        WHERE osm_id = %(osm_id)s
        RETURNING place_id
    """, {
        "osm_id": place["osm_id"],
        "name": new_name,
        "hstore": new_tags
    })

    place_id = update_cursor.fetchone()["place_id"]

    for tag, value in new_tags.iteritems():
        if tag[0:4] == 'name':
            name_type = 'translation'
            lang = key[5:len(key)]
        else:
            name_type = tag_map[tag]
            lang = None

        update_cursor.execute("""
            INSERT INTO names (place_id, lang, type, name)
            VALUES (%(place_id)s, %(lang)s, %(type)s, %(name)s)
        """, {
            "place_id": place_id,
            "type": name_type,
            "lang": lang,
            "name": value
        })
    connection.commit()


connection.commit()
