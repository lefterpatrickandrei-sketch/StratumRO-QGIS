import math
import pyproj

points = [
    {
        "id": "P1 (Dobrogea / Constanta)",
        "lat_dms": (44, 38, 43.52664),
        "lon_dms": (28, 46, 12.65034),
        "official_x_nord": 356514.605,
        "official_y_est": 799125.737,
    },
    {
        "id": "P2 (Bistrita / Nord)",
        "lat_dms": (47, 13, 34.72394),
        "lon_dms": (24, 31, 32.15343),
        "official_x_nord": 636431.725,
        "official_y_est": 464197.087,
    },
    {
        "id": "P3 (Bihor / Vest)",
        "lat_dms": (46, 46, 3.59286),
        "lon_dms": (21, 42, 38.23706),
        "official_x_nord": 590565.656,
        "official_y_est": 248951.801,
    },
    {
        "id": "P4 (Cluj / Centru-Vest)",
        "lat_dms": (46, 56, 28.43635),
        "lon_dms": (23, 25, 58.19140),
        "official_x_nord": 605818.798,
        "official_y_est": 380823.412,
    },
    {
        "id": "P5 (Apuseni / Alba)",
        "lat_dms": (46, 26, 26.03942),
        "lon_dms": (22, 41, 21.00950),
        "official_x_nord": 551576.298,
        "official_y_est": 322596.973,
    },
]

def dms_to_dd(d, m, s):
    return d + m / 60.0 + s / 3600.0

# 1. Pipeline din caseta de dialog QGIS (Ballpark dialog)
pipe_dialog = (
    "+proj=pipeline "
    "+step +proj=unitconvert +xy_in=deg +xy_out=rad "
    "+step +proj=push +v_3 "
    "+step +proj=cart +ellps=WGS84 "
    "+step +inv +proj=helmert +x=2.329 +y=-147.042 +z=-92.08 +rx=-0.309 +ry=-0.325 +rz=-0.497 +s=5.69 +convention=coordinate_frame "
    "+step +inv +proj=cart +ellps=krass "
    "+step +proj=pop +v_3 "
    "+step +proj=sterea +lat_0=46 +lon_0=25 +k=0.99975 +x_0=500000 +y_0=500000 +ellps=krass"
)
t_dialog = pyproj.Transformer.from_pipeline(pipe_dialog)

# 2. Standard PROJ EPSG:4326 -> EPSG:3844
t_std_4326 = pyproj.Transformer.from_crs("EPSG:4326", "EPSG:3844", always_xy=True)

# 3. Standard PROJ EPSG:4258 -> EPSG:3844 (ETRS89 to Stereo70)
t_std_4258 = pyproj.Transformer.from_crs("EPSG:4258", "EPSG:3844", always_xy=True)

print("=" * 115)
print("COMPARATIE GEODEZICA RIGUROASA: TRANSDAT-RO (ANCPI) vs. PROJ / QGIS PE VECTORII OFICIALI DE TEST")
print("=" * 115)

for pt in points:
    lat = dms_to_dd(*pt["lat_dms"])
    lon = dms_to_dd(*pt["lon_dms"])
    ox = pt["official_x_nord"]
    oy = pt["official_y_est"]
    
    # 1. Dialog pipeline
    e_diag, n_diag = t_dialog.transform(lon, lat)
    err_diag = math.hypot(n_diag - ox, e_diag - oy)
    
    # 2. Standard 4326 -> 3844
    e_4326, n_4326 = t_std_4326.transform(lon, lat)
    err_4326 = math.hypot(n_4326 - ox, e_4326 - oy)
    
    # 3. Standard 4258 -> 3844
    e_4258, n_4258 = t_std_4258.transform(lon, lat)
    err_4258 = math.hypot(n_4258 - ox, e_4258 - oy)
    
    print(f"Punct: {pt['id']}")
    print(f"  ETRS89 Geographic  : Lat = {lat:.7f}°, Lon = {lon:.7f}°")
    print(f"  TransDAT-RO Oficial : X(Nord) = {ox:10.3f} m,  Y(Est) = {oy:10.3f} m")
    print(f"  1) QGIS Dialog Pipe : X(Nord) = {n_diag:10.3f} m,  Y(Est) = {e_diag:10.3f} m  --> Eroare 2D: {err_diag:6.3f} m (dX: {n_diag-ox:+.3f}, dY: {e_diag-oy:+.3f})")
    print(f"  2) PROJ EPSG:4326   : X(Nord) = {n_4326:10.3f} m,  Y(Est) = {e_4326:10.3f} m  --> Eroare 2D: {err_4326:6.3f} m (dX: {n_4326-ox:+.3f}, dY: {e_4326-oy:+.3f})")
    print(f"  3) PROJ EPSG:4258   : X(Nord) = {n_4258:10.3f} m,  Y(Est) = {e_4258:10.3f} m  --> Eroare 2D: {err_4258:6.3f} m (dX: {n_4258-ox:+.3f}, dY: {e_4258-oy:+.3f})")
    print("-" * 115)
