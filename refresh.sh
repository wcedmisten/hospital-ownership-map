echo "Removing old json files"
rm hospitals.json hospitals_layer.json regions.json hospitals-structured.json

echo "Rerunning python scripts"

python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -r requirements.txt

python3 hospitals.py
python3 hospital_layers.py
python3 voronoi.py

echo "Copying generated files to the web app"
cp regions.json web/public/data/regions.json
cp hospitals_layer.json web/public/data/hospitals_layer.json