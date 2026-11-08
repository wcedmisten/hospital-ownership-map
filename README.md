To update extract for region:

```sh
osmium extract -p ~/Downloads/us.poly planet-260515.osm.pbf -O -o us.osm.pbf
osmium tags-filter -o extract.osm.pbf us.osm.pbf nwr/amenity=hospital --overwrite
```

Running the Python scripts (note: to refresh all data delete these files:
hospitals.json, hospitals_layer.json, hospitals-structured.json)

```sh
python3 hospitals.py  # reads extract.osm.pbf directly with DuckDB
python3 hospital_layers.py
python3 voronoi.py
```

```sh
cp regions.json web/public/data/regions.json
cp hospitals_layer.json web/public/data/hospitals_layer.json
```


## Web map

The interactive map lives in `web/` (Vite + React + TypeScript, MapLibre GL).

```sh
cd web
npm install
npm run dev      # local dev server
npm run build    # type-check + production build into web/dist
```

Map data is fetched at runtime from `web/public/data/` (`regions.json`, `hospitals_layer.json`); the base map style is `web/src/data/positron_style.json`.

### Deploying

The build output is a fully static site. Pushes to `main` that touch `web/` are built and deployed to
GitHub Pages by `.github/workflows/deploy-web.yml` (it can also be run manually from the Actions tab),
and the site is served at https://wcedmisten.github.io/hospital-ownership-map/.

One-time setup:

1. In the GitHub repo, go to Settings → Pages → Build and deployment and set Source to **GitHub Actions**.
2. Make sure the tile server (`planet-tiles.wcedmisten.dev`) allows CORS requests from `https://wcedmisten.github.io`.

To publish new data, run `refresh.sh` (it copies the outputs into `web/public/data/`), then commit and push.
