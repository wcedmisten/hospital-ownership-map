import psycopg2
import psycopg2.extras
import json
from shapely.geometry import Point
import os

# standardize operator names
operators_cleanup_map = {
    # "HCA": "HCA Virginia",
}


def get_hospital_records():
    conn = psycopg2.connect(
        "host=localhost dbname=postgres user=postgres port=15432 password=password"
    )

    # Open a cursor to perform database operations
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    where_clause = """ WHERE tags->>'amenity'='hospital' 
    AND (tags->>'healthcare:speciality' IS DISTINCT FROM 'psychiatry')
    AND (tags->>'healthcare:speciality' IS DISTINCT FROM 'behavior')
    AND (tags->>'healthcare:speciality' IS DISTINCT FROM 'child_psychiatry')
    AND (tags->>'healthcare' IS DISTINCT FROM 'rehabilitation')
    AND (tags->>'healthcare:speciality' IS DISTINCT FROM 'rehabilitation')
    AND (tags->>'operator' IS DISTINCT FROM 'Veterans Health Administration')
    AND (tags->>'operator' IS DISTINCT FROM 'United States Air Force')
    AND (tags->>'operator' IS DISTINCT FROM 'United States Navy')
    AND (tags->>'operator' IS DISTINCT FROM 'United States Army')
    AND (tags->>'temporary' IS DISTINCT FROM 'yes')
    AND (tags->>'name' NOT ILIKE '%veterans affairs%')
    AND (tags->>'name' IS NOT NULL)"""

    osm_query = (
        """SELECT ST_AsText(ST_Transform(geom,4326)) AS centroid, osm_id , name, tags->>'operator' as operator FROM hospitals """
        + where_clause
    )

    cur.execute(osm_query)

    all_records = cur.fetchall()

    # replace names in the cleanup map to standardize the data
    for record in all_records:
        record["operator"] = operators_cleanup_map.get(record["operator"], record["operator"])

    return all_records


def structure_record(record):
    name = record["name"]
    center = record["centroid"]
    lon, lat = center.replace("POINT(", "").replace(")", "").split(" ")
    lon = float(lon)
    lat = float(lat)

    return {
        "name": name,
        "lon": lon,
        "lat": lat,
        "osm_id": record["osm_id"],
        "operator": record["operator"],
    }


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
