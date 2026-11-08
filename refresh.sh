echo "Removing old json files"
rm hospitals.json hospitals_layer.json regions.json hospitals-structured.json

echo "Updating postgis data"
cd osm2pgsql
docker compose down -v
docker compose up -d
sleep 10

docker exec -it postgis bash -c "osm2pgsql --create --verbose -U postgres -H localhost --output=flex -S /hospitals.lua /extract.osm.pbf"
cd -

echo "Rerunning python scripts"

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt

python3 hospitals.py
python3 hospital_layers.py
python3 voronoi.py

echo "Copying generated files to wcedmisten.fyi repo"
cp regions.json ~/repos/wcedmisten.fyi/pages/project/us-hospital-ownership/voronoi.json
cp hospitals_layer.json ~/repos/wcedmisten.fyi/pages/project/us-hospital-ownership/hospitals_layer.json