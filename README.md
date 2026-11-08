To update extract for region:

```sh
osmium extract -p ~/Downloads/us.poly planet-260515.osm.pbf -O -o us.osm.pbf
osmium tags-filter -o /home/wcedmisten/repos/hospital-monopoly-map/osm2pgsql/postgis_osm_data/extract.osm.pbf ~/Downloads/osm_data/us.osm.pbf nwr/amenity=hospital --overwrite
```

```sh
cd osm2pgsql

docker compose up -d
docker exec -it postgis bash -c "osm2pgsql --create --verbose -U postgres -H localhost --output=flex -S /hospitals.lua /extract.osm.pbf"
```

Running the Python scripts (note: to refresh all data delete these files:
hospitals.json, hospitals_layer.json, hospitals-structured.json)

```sh
python3 hospitals.py
python3 hospital_layers.py
python3 voronoi.py
```

```sh
cp regions.json ~/repos/wcedmisten.fyi/pages/project/us-hospital-ownership/voronoi.json
cp hospitals_layer.json ~/repos/wcedmisten.fyi/pages/project/us-hospital-ownership/hospitals_layer.json
```

