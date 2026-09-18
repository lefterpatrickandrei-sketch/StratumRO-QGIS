import geopandas as gpd

t2 = gpd.read_file('data/ground_truth/tier2_extended_gt.geojson')
print("Tier 2 Extended GT count:", len(t2))
print("Columns:", t2.columns.tolist())

osm = gpd.read_file('data/ground_truth/osm_buildings_aoi.geojson')
print("OSM buildings count:", len(osm))
print("Columns:", osm.columns.tolist())
