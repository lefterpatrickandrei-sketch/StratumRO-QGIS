# -*- coding: utf-8 -*-
import urllib.request
import urllib.error
import ssl
import json

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def test(url):
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            return {"url": url, "status": r.status, "content_type": r.headers.get("Content-Type", "")}
    except urllib.error.HTTPError as e:
        return {"url": url, "status": e.code, "error": e.reason}
    except Exception as e:
        return {"url": url, "status": "EXC", "error": str(e)}

# 1. Test cIMeC endpoints
print("cIMeC:")
print(test("https://ran.cimec.ro/"))
print(test("https://map.cimec.ro/Mapserver/"))
print(test("https://map.cimec.ro/ArcGIS/rest/services"))

# 2. Test EEA Natura 2000
print("\nEEA:")
print(test("https://bio.discomap.eea.europa.eu/arcgis/rest/services/ProtectedSites/Natura2000Sites/MapServer"))
print(test("https://bio.discomap.eea.europa.eu/arcgis/services/ProtectedSites/Natura2000Sites/MapServer/WMSServer?SERVICE=WMS&VERSION=1.3.0&REQUEST=GetCapabilities"))

# 3. Test ANAR Inundatii
print("\nInundatii.ro:")
print(test("https://inundatii.ro/"))
print(test("https://inundatii.ro/geoserver/web/"))
print(test("https://inundatii.ro/geoserver/ows?service=WMS&version=1.3.0&request=GetCapabilities"))

# 4. Test Inspectorul Padurii
print("\nInspectorul Padurii:")
print(test("https://inspectorulpadurii.ro/"))
print(test("https://inspectorulpadurii.ro/api/"))
print(test("https://inspectorulpadurii.ro/arcgis/rest/services"))

# 5. Test direct download for APIA and ANAR
print("\nDirect downloads from data.gov.ro:")
# Test HEAD for APIA 1.12GB
req_apia = urllib.request.Request(
    "https://data.gov.ro/dataset/93895f6f-ade1-443a-b509-6dd2becdc521/resource/0801eae4-df61-4300-a77b-986817a0900f/download/blocuri_fizice_2025.zip",
    headers={"User-Agent": HEADERS["User-Agent"], "Range": "bytes=0-1024"}
)
try:
    with urllib.request.urlopen(req_apia, timeout=15, context=ctx) as r:
        print("APIA Download test:", r.status, r.headers.get("Content-Range"), r.headers.get("Content-Length"))
except Exception as e:
    print("APIA Download error:", e)
