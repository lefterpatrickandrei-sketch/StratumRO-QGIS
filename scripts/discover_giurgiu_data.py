import json
import urllib.request
import urllib.parse

def fetch_overpass(query):
    url = "https://overpass-api.de/api/interpreter"
    data = urllib.parse.urlencode({'data': query}).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={'User-Agent': 'StratumRO/2.0'})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode('utf-8'))

# Query UAT Giurgiu (admin_level 7 is city/municipality in Romania)
q = """
[out:json][timeout:30];
relation["admin_level"="7"]["name"~"Giurgiu"];
out tags;
"""
res = fetch_overpass(q)
print("Relations found:")
for el in res.get("elements", []):
    print(el.get("id"), el.get("tags", {}).get("name"), el.get("tags", {}).get("admin_level"), el.get("tags", {}).get("wikidata"))
