# -*- coding: utf-8 -*-
import json

with open(r"tools\layer_audit_report.json", "r", encoding="utf-8") as f:
    layers = json.load(f)

print(f"{'Idx':<3} | {'Feature Count':<12} | {'Group':<25} | {'Layer Name'}")
print("-" * 90)
for idx, l in enumerate(layers, 1):
    cnt = str(l['feature_count']) if l['feature_count'] is not None else "Raster"
    grp = l['group'] or "(root)"
    name = l['name']
    print(f"{idx:<3} | {cnt:<12} | {grp[:24]:<25} | {name}")
