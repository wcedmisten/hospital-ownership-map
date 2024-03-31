import json
import geodatasets
import geopandas as gpd
import matplotlib.pyplot as plt

from colorhash import ColorHash

import pandas as pd

from shapely.geometry import MultiPoint, Point, Polygon, shape
from shapely.ops import voronoi_diagram

from srai.regionalizers import VoronoiRegionalizer, geocode_to_region_gdf

with open("hospitals-structured.json") as f:
    hospitals_data = json.load(f)

# remove multipolygons
hospitals_data = list(filter(lambda x: x["osm_id"] > 0, hospitals_data))

points = list([Point(hospital["lon"], hospital["lat"]) for hospital in hospitals_data])

names = list(
    [
        "UNKNOWN" if hospital["name"] is None else hospital["name"]
        for hospital in hospitals_data
    ]
)

operators = list(
    [
        "UNKNOWN" if hospital["operator"] is None else hospital["operator"]
        for hospital in hospitals_data
    ]
)

# standardize operator names
operators_cleanup_map = {"Bon Secours Health System": "Bon Secours",
                        "HCA": "HCA Virginia",
                        'HCA Virginia Health System': 'HCA Virginia',
                        'VCU': 'VCU Health'}

# replace names in the cleanup map to standardize the data
operators = [operators_cleanup_map.get(operator, operator) for operator in operators]

hospitals_dataframe = pd.DataFrame(
    {"geometry": points, "name": names, "operator": operators}
)


def color_by_row(row):
    if row["operator"] != "UNKNOWN":
        return ColorHash(row["operator"]).hex
    else:
        return ColorHash(row["name"]).hex

# set the color based on operator
hospitals_dataframe["color"] = hospitals_dataframe.apply(
    color_by_row, axis=1
)

hospital_gdf = gpd.GeoDataFrame(hospitals_dataframe, crs="EPSG:4326")

world = gpd.read_file(geodatasets.get_path("naturalearth.land"))

with open("states.json") as f:
    states = json.load(f)

virginia = list(filter(lambda s: s["properties"]["name"] == "Virginia", states["features"]))[0]

virginia_bounds = shape(virginia["geometry"])

hospital_voronoi_regions = VoronoiRegionalizer(seeds=hospital_gdf).transform()

hospital_voronoi_regions["geometry"] = hospital_voronoi_regions.apply(
    lambda row: virginia_bounds.intersection(row["geometry"]), axis=1
)

def plot_flat(
    seeds_gdf: gpd.GeoDataFrame,
    regions_gdf: gpd.GeoDataFrame,
    marker_size: float = None,
    title: str = None,
) -> None:
    fig, ax = plt.subplots(figsize=(20, 10))
    world.plot(ax=ax, alpha=0.6, color="grey")
    regions_gdf.reset_index().plot(
        ax=ax,
        alpha=0.4,
        column="region_id",
        edgecolor="black",
        color=hospital_gdf["color"],
        linewidth=0.5,
    )
    seeds_gdf.plot(ax=ax, alpha=0.6, color="black", markersize=marker_size)
    ax.set_axis_off()
    fig.tight_layout()
    if title:
        plt.title(title)
    plt.show()


# plot_flat(
#     hospital_gdf,
#     hospital_voronoi_regions,
#     title="Spherical Voronoi diagram",
# )

joined = gpd.sjoin(hospital_voronoi_regions, hospital_gdf)

print(joined.head())

export = joined.to_file("regions.json")
