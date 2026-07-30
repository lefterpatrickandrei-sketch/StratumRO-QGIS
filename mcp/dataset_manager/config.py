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

# Sisteme de coordonate de referință (CRS) acceptate în pipeline:
# EPSG:3844 reprezintă codul oficial actualizat al proiecției Stereografice 1970 utilizat de ANCPI / eTerra / TransdatRO.
# EPSG:31700 este varianta istorică/legacy pentru Stereo 70 în QGIS.
VALID_CRS = ["EPSG:3844", "EPSG:31700", "EPSG:4326"]

# Extensii de fișiere permise pentru procesările ulterioare în GDAL și PDAL
ALLOWED_EXTENSIONS = {
    "raster": [".tif", ".tiff"],
    "point_cloud": [".las", ".laz"]
}

# Sistemul vertical de altitudini oficial al României
# EPSG:5781 — Marea Neagră 1975 (datumul vertical utilizat de ANCPI / cadastru)
VERTICAL_CRS = "EPSG:5781"

# CRS compus 3D: Stereo 70 (plan) + Marea Neagră 1975 (vertical)
COMPOUND_3D_CRS = "EPSG:3844+5781"

# Intervalul altimetric valid al României (în metri deasupra nivelului Mării Negre)
ROMANIA_Z_RANGE = (0.0, 2544.0)  # 0m = Marea Neagră, 2544m = Vf. Moldoveanu