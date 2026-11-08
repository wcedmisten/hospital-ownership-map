import json
import geodatasets
import geopandas as gpd
import matplotlib.pyplot as plt

from colorhash import ColorHash

import pandas as pd

from shapely.ops import unary_union as union
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

osm_ids = list([hospital["osm_id"] for hospital in hospitals_data])

import pprint

operator_counts = {operator: operators.count(operator) for operator in set(operators)}
pprint.pprint(operator_counts)
with open("operator_counts.json", "w") as f:
    json.dump(operator_counts, f, indent=4)

hospitals_dataframe = pd.DataFrame(
    {"geometry": points, "name": names, "operator": operators, "osm_id": osm_ids}
)


def color_by_row(row):
    if row["operator"] != "UNKNOWN":
        return ColorHash(row["operator"]).hex
    else:
        return "#dedede"

# set the color based on operator
hospitals_dataframe["color"] = hospitals_dataframe.apply(
    color_by_row, axis=1
)

hospital_gdf = gpd.GeoDataFrame(hospitals_dataframe, crs="EPSG:4326")
nearest_df = gpd.sjoin_nearest(
    hospital_gdf, 
    hospital_gdf, 
    how='inner', 
    exclusive=True, 
    distance_col="distance_to_nearest"
)
print("nearest")
print(nearest_df.sort_values(by="distance_to_nearest").head(20))

duplicate_rows = hospital_gdf[hospital_gdf.duplicated(subset="geometry", keep=False)]
print(f"Found {len(duplicate_rows)} duplicates")
print(duplicate_rows)

world = gpd.read_file(geodatasets.get_path("naturalearth.land"))

with open("states.json") as f:
    states = json.load(f)

print(list(map(lambda s: s["properties"]["name"], states["features"])))

included_states = [
    "Virginia", # cleaned
    "District of Columbia", # cleaned
    "West Virginia", # cleaned
    "Maryland", # cleaned
    "Kentucky", # cleaned
    "Tennessee", # cleaned
    "North Carolina", # cleaned
    "South Carolina", # cleaned
    "Georgia", # cleaned
    "Alabama", # cleaned
    "Delaware", # cleaned
    "Pennsylvania", # cleaned
    "New Jersey", # cleaned
    "New York", # cleaned
    "Florida", # cleaned
    "Connecticut", # cleaned
    "Rhode Island", # cleaned
    "New Hampshire", # cleaned
    "Massachusetts", # cleaned
    "Vermont", # cleaned
    "Ohio", # cleaned
    "Maine", # cleaned
    "Mississippi", # cleaned
    "Indiana", # cleaned
    "Michigan", # cleaned
    "Wisconsin", # cleaned
    "Illinois", # cleaned
    "Louisiana", # cleaned
    "Missouri", # cleaned
    "Iowa",
    "Arkansas",
    "Minnesota",
    "North Dakota",
    "South Dakota",
    "Nebraska",
    "Kansas",
    "Oklahoma",
    "Texas",
    "Montana",
    "Wyoming",
    "Colorado",
    "New Mexico",
    "Utah",
    "Arizona",
    "Idaho",
    "Nevada",
    "California",
    "Oregon",
    "Washington"
    ]

states_features = list(filter(lambda s: s["properties"]["name"] in included_states, states["features"]))

states_bounds = union(list(map(lambda s: shape(s["geometry"]), states_features)))

hospital_voronoi_regions = VoronoiRegionalizer(seeds=hospital_gdf).transform()

hospital_voronoi_regions["geometry"] = hospital_voronoi_regions.apply(
    lambda row: states_bounds.intersection(row["geometry"]), axis=1
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
