import json
import urllib.request
import urllib.parse
import sys

# 1. Fetch UAT Giurgiu boundary
nom_url = 'https://nominatim.openstreetmap.org/search?city=Giurgiu&county=Giurgiu&country=Romania&format=geojson&polygon_geojson=1'
req = urllib.request.Request(nom_url, headers={'User-Agent': 'StratumRO-Benchmark/2.0'})
with urllib.request.urlopen(req, timeout=15) as resp:
    data = json.loads(resp.read().decode('utf-8'))

feat = data['features'][0]
bbox = feat['bbox'] # [min_lon, min_lat, max_lon, max_lat]
print(f"UAT Giurgiu found: bbox={bbox}")

# Overpass mirrors
mirrors = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://maps.mail.ru/osm/tools/overpass/api/interpreter",
    "https://overpass-api.de/api/interpreter"
]

# Query sample features in Giurgiu central AOI: [43.88, 25.95, 43.91, 25.98]
central_bbox = "43.88,25.95,43.91,25.98"
query = f"""[out:json][timeout:25];
(
  way["building"]({central_bbox});
  way["highway"]({central_bbox});
  way["waterway"]({central_bbox});
  relation["waterway"]({central_bbox});
  way["natural"="water"]({central_bbox});
  way["landuse"="forest"]({central_bbox});
  way["natural"="wood"]({central_bbox});
);
out geom 50;
"""

success = False
for m in mirrors:
    try:
        print(f"Testing mirror: {m}")
        pdata = urllib.parse.urlencode({'data': query}).encode('utf-8')
        mreq = urllib.request.Request(m, data=pdata, headers={'User-Agent': 'StratumRO-Benchmark/2.0'})
        with urllib.request.urlopen(mreq, timeout=20) as mresp:
            mres = json.loads(mresp.read().decode('utf-8'))
            print(f"Success from {m}: received {len(mres.get('elements', []))} elements!")
            success = True
            break
    except Exception as e:
        print(f"Mirror {m} failed: {e}")

if not success:
    print("Could not query overpass mirrors")
