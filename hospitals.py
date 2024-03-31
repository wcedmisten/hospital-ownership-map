import psycopg2
import psycopg2.extras
import json
from shapely.geometry import Point
import os

def get_hospital_records():
    conn = psycopg2.connect("host=localhost dbname=postgres user=postgres port=15432 password=password")

    # Open a cursor to perform database operations
    cur = conn.cursor(cursor_factory = psycopg2.extras.RealDictCursor)

    where_clause = """ WHERE amenity='hospital' 
    AND ("healthcare:speciality" IS DISTINCT FROM 'psychiatry')
    AND (healthcare IS DISTINCT FROM 'rehabilitation')
    AND ("healthcare:speciality" IS DISTINCT FROM 'rehabilitation')
    AND (operator IS DISTINCT FROM 'Veterans Health Administration')
    AND (name NOT ILIKE '%veterans affairs%' OR name IS NULL)"""

    osm_query = """SELECT ST_AsText(ST_Transform(ST_Centroid(way),4326)) AS centroid,osm_id,name,operator FROM planet_osm_polygon """ + where_clause
    cur.execute(osm_query)

    polygon_records = cur.fetchall()

    osm_query = """SELECT ST_AsText(ST_Transform(way,4326)) AS centroid,osm_id,name,operator FROM planet_osm_point """ + where_clause

    cur.execute(osm_query)

    point_records = cur.fetchall()

    return polygon_records + point_records

def structure_record(record):
    name = record["name"]
    center = record["centroid"]
    lon, lat = center.replace("POINT(", "").replace(")", "").split(" ")
    lon = float(lon)
    lat = float(lat)

    return {"name": name, "lon": lon, "lat": lat, "osm_id": record["osm_id"], "operator": record["operator"]}

if os.path.isfile("hospitals.json"):
    with open("hospitals.json", "r") as f:
        all_records = json.load(f)
        structured_records = [structure_record(record) for record in all_records]
else:
    all_records = get_hospital_records()
    structured_records = [structure_record(record) for record in all_records]
    with open("hospitals.json", "w") as f:
        json.dump(all_records, f)
    with open("hospitals-structured.json", "w") as f:
        json.dump(structured_records, f)
