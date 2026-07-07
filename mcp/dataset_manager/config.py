import os
from pathlib import Path

# Determinarea căii absolute către rădăcina proiectului QGIS-AI
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# Definirea directoarelor dedicate stocării seturilor de date geospațiale
DATASETS_DIR = BASE_DIR / "datasets"
ORTHOPHOTO_DIR = DATASETS_DIR / "orthophotos"
LIDAR_DIR = DATASETS_DIR / "lidar"

# Forțarea creării directoarelor fizice pe disk dacă nu există deja
os.makedirs(ORTHOPHOTO_DIR, exist_ok=True)
os.makedirs(LIDAR_DIR, exist_ok=True)

# Sisteme de coordonate de referință (CRS) acceptate în pipeline
# EPSG:31700 reprezintă proiecția Stereografică 1970 utilizată oficial în România
VALID_CRS = ["EPSG:31700", "EPSG:3844", "EPSG:4326"]

# Extensii de fișiere permise pentru procesările ulterioare în GDAL și PDAL
ALLOWED_EXTENSIONS = {
    "raster": [".tif", ".tiff"],
    "point_cloud": [".las", ".laz"]
}