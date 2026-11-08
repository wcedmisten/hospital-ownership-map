import duckdb
import json
from shapely.geometry import Point
import os
import sys

PBF_PATH = "extract.osm.pbf"

# Reads amenity=hospital features directly from the OSM PBF with DuckDB spatial.
# Geometry rules (same as the previous osm2pgsql import):
#   nodes                  -> point
#   closed ways            -> centroid of polygon
#   multipolygon relations -> centroid of multipolygon assembled from member ways
HOSPITALS_QUERY = """
WITH osm AS (
    SELECT * FROM ST_ReadOSM($pbf_path)
),
nodes AS (
    SELECT id, lat, lon FROM osm WHERE kind = 'node'
),
-- every way's ordered node coordinates (needed both for hospital ways and relation members)
way_lines AS (
    SELECT w.id,
           ST_MakeLine(list(ST_Point(n.lon, n.lat) ORDER BY w.idx)) AS line
    FROM (
        SELECT id, len(refs) AS n_refs, unnest(refs) AS ref, generate_subscripts(refs, 1) AS idx
        FROM osm WHERE kind = 'way'
    ) w
    JOIN nodes n ON n.id = w.ref
    GROUP BY w.id
    -- drop ways with nodes missing from the extract (e.g. clipped at the boundary)
    HAVING count(*) = any_value(w.n_refs)
),
hospital_nodes AS (
    SELECT 'N' AS osm_type, id AS osm_id, tags, ST_Point(lon, lat) AS geom
    FROM osm
    WHERE kind = 'node' AND tags['amenity'] = 'hospital'
),
hospital_ways AS (
    SELECT 'W' AS osm_type, o.id AS osm_id, o.tags,
           -- CASE guard: the optimizer may evaluate this before the WHERE filter
           CASE WHEN ST_IsClosed(l.line) THEN ST_Centroid(ST_MakePolygon(l.line)) END AS geom
    FROM osm o
    JOIN way_lines l ON l.id = o.id
    WHERE o.kind = 'way' AND o.tags['amenity'] = 'hospital'
      AND len(o.refs) >= 4 AND o.refs[1] = o.refs[-1]
),
hospital_relations AS (
    SELECT 'R' AS osm_type, r.id AS osm_id, any_value(r.tags) AS tags,
           ST_Centroid(ST_BuildArea(ST_Collect(list(l.line)))) AS geom
    FROM (
        SELECT id, tags, unnest(refs) AS ref, unnest(ref_types) AS ref_type
        FROM osm
        WHERE kind = 'relation' AND tags['amenity'] = 'hospital'
          AND tags['type'] = 'multipolygon'
    ) r
    JOIN way_lines l ON l.id = r.ref AND r.ref_type = 'way'
    GROUP BY r.id
),
hospitals AS (
    SELECT * FROM hospital_nodes
    UNION ALL SELECT * FROM hospital_ways
    UNION ALL SELECT * FROM hospital_relations
)
-- same 'POINT(lon lat)' format as the old PostGIS ST_AsText output
SELECT 'POINT(' || ST_X(geom) || ' ' || ST_Y(geom) || ')' AS centroid,
       osm_id,
       tags['name'] AS name,
       tags['operator'] AS operator
FROM hospitals
WHERE geom IS NOT NULL AND NOT ST_IsEmpty(geom)
  AND tags['healthcare:speciality'] IS DISTINCT FROM 'psychiatry'
  AND tags['healthcare:speciality'] IS DISTINCT FROM 'behavior'
  AND tags['healthcare:speciality'] IS DISTINCT FROM 'child_psychiatry'
  AND tags['healthcare'] IS DISTINCT FROM 'rehabilitation'
  AND tags['healthcare:speciality'] IS DISTINCT FROM 'rehabilitation'
  AND tags['operator'] IS DISTINCT FROM 'Veterans Health Administration'
  AND tags['operator'] IS DISTINCT FROM 'United States Air Force'
  AND tags['operator'] IS DISTINCT FROM 'United States Navy'
  AND tags['operator'] IS DISTINCT FROM 'United States Army'
  AND tags['temporary'] IS DISTINCT FROM 'yes'
  AND tags['name'] NOT ILIKE '%veterans affairs%'
  AND tags['name'] IS NOT NULL
ORDER BY osm_type, osm_id
"""

# standardize operator names
operators_cleanup_map = {
    # "HCA": "HCA Virginia",
}


def get_hospital_records():
    conn = duckdb.connect()
    conn.execute("INSTALL spatial; LOAD spatial;")
    rel = conn.sql(HOSPITALS_QUERY, params={"pbf_path": PBF_PATH})
    columns = rel.columns
    all_records = [dict(zip(columns, row)) for row in rel.fetchall()]

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
