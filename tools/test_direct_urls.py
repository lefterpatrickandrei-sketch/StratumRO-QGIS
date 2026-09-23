# -*- coding: utf-8 -*-
"""
Script de testare si verificare a linkurilor directe oficiale.
Verifica disponibilitatea, codurile de stare HTTP, redirectionarile si dimensiunile.
"""

import urllib.request
import urllib.error
import ssl
import json
import sys

# Ignorare erori SSL pentru servere guvernamentale cu certificate vechi
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "*/*"
}

def test_url(name, url, method="HEAD"):
    req = urllib.request.Request(url, headers=HEADERS, method=method)
    try:
        with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
            return {
                "name": name,
                "url": url,
                "status": resp.status,
                "content_type": resp.headers.get("Content-Type", ""),
                "content_length": resp.headers.get("Content-Length", "unknown"),
                "success": True,
                "note": "Accesibil direct"
            }
    except urllib.error.HTTPError as e:
        # Daca HEAD da 405 Method Not Allowed, incercam GET pe primii 1024 bytes
        if method == "HEAD" and e.code in (405, 403):
            return test_url(name, url, method="GET")
        return {
            "name": name,
            "url": url,
            "status": e.code,
            "content_type": e.headers.get("Content-Type", "") if hasattr(e, "headers") else "",
            "content_length": "unknown",
            "success": False,
            "note": f"HTTPError {e.code}: {e.reason}"
        }
    except Exception as e:
        return {
            "name": name,
            "url": url,
            "status": "ERROR",
            "content_type": "",
            "content_length": "0",
            "success": False,
            "note": str(e)
        }

def test_ckan_package(package_id):
    api_url = f"https://data.gov.ro/api/3/action/package_show?id={package_id}"
    req = urllib.request.Request(api_url, headers=HEADERS)
    try:
        with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            if data.get("success"):
                resources = data["result"]["resources"]
                res_list = []
                for r in resources:
                    res_list.append({
                        "name": r.get("name"),
                        "format": r.get("format"),
                        "url": r.get("url"),
                        "size": r.get("size")
                    })
                return {"success": True, "title": data["result"]["title"], "resources": res_list}
    except Exception as e:
        return {"success": False, "error": str(e)}

if __name__ == "__main__":
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding='utf-8')
    print("=== TESTARE ENDPOINT-URI DIRECTE OFICIALE ===")
    
    # 1. CKAN data.gov.ro API
    print("\n--- 1. data.gov.ro CKAN Packages ---")
    for pkg in ["unitati-administrativ-teritoriale", "parcele-de-referinta-2025-blocuri-fizice-apia", "hidrografie"]:
        res = test_ckan_package(pkg)
        if res.get("success"):
            print(f"[OK] {pkg}: {res['title']}")
            for r in res['resources'][:3]:
                print(f"     -> {r['format']}: {r['name']} | Direct URL: {r['url']}")
        else:
            print(f"[FAIL] {pkg}: {res.get('error')}")
            
    # 2. Test direct URL endpoints
    print("\n--- 2. Test Direct HTTP/WMS Endpoints ---")
    urls_to_test = [
        ("ANCPI Geoportal", "https://geoportal.ancpi.ro/"),
        ("ANCPI WMS Ortofoto", "https://geoportal.ancpi.ro/arcgis/services/INSPIRE/Orthophoto/ImageServer/WMSServer?service=WMS&request=GetCapabilities"),
        ("cIMeC RAN Portal", "https://ran.cimec.ro/"),
        ("cIMeC MapServer", "https://map.cimec.ro/Mapserver/"),
        ("ANAR Inundatii WMS", "https://inundatii.ro/geoserver/wms?service=WMS&request=GetCapabilities"),
        ("EEA Natura 2000 WMS", "https://bio.discomap.eea.europa.eu/arcgis/services/ProtectedSites/Natura2000Sites/MapServer/WMSServer?service=WMS&request=GetCapabilities"),
        ("ROMSILVA Inspectorul Padurii", "https://inspectorulpadurii.ro/"),
        ("ANCPI RENNS Public", "https://renns.ancpi.ro/renns-public/")
    ]
    
    for name, u in urls_to_test:
        r = test_url(name, u)
        status_sym = "[OK]" if r["success"] or (isinstance(r["status"], int) and r["status"] < 400) else "[FAIL]"
        print(f"{status_sym} {name}: Status={r['status']} | Content-Type={r['content_type'][:30]} | Note={r['note']}")
