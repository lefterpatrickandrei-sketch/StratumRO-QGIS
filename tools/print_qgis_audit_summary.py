import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
audit_file = ROOT / "workspace" / "reviews" / "comparatie_a_vs_b_20261018" / "qgis_internal_audit.json"

with open(audit_file, encoding="utf-8") as f:
    data = json.load(f)

print("=" * 70)
print(">>> STRATUMRO — AUDIT COGNITIV LIVE DIN INTERIORUL QGIS DESKTOP <<<")
print("=" * 70)

print(f"[*] Titlu Proiect: {data['project_title']}")
print(f"[*] Cale Proiect: {data['project_path']}")
print(f"[*] CRS Proiect: {data['crs']}")
print(f"[*] Numar Total Straturi Incarcate: {data['layer_count_total']}")

print("\n--- 1. STARE CANVAS ACTIV (Ce se deseneaza efectiv in acest moment) ---")
c = data["canvas"]
print(f"Scara Curenta: 1:{c['scale']}")
ext = c["extent"]
print(f"Extindere Spatiala: {ext['width_m']:.1f}m x {ext['height_m']:.1f}m (X: {ext['xmin']}..{ext['xmax']}, Y: {ext['ymin']}..{ext['ymax']})")
print(f"Are Ordine Personalizata (Custom Layer Order): {c['has_custom_order']}")
print(f"Numar Straturi Randate Curent: {len(c['rendered_layers'])}")
print("Straturile active in render stack:")
for idx, lyr_name in enumerate(c["rendered_layers"]):
    print(f"  [{idx:02d}] {lyr_name}")

print("\n--- 2. IERARHIA RADACINA (Arborele de Straturi) ---")
for node in data["tree_hierarchy"]:
    status = "VIZIBIL" if node["visible"] else "ASCUNS"
    print(f"• {node['name']} [{node['type'].upper()}] --> {status}")
    if node.get("children"):
        for sub in node["children"]:
            sub_status = "VIZIBIL" if sub["visible"] else "ASCUNS"
            extra = f"({sub.get('feature_count')} corpuri)" if sub.get("feature_count") is not None else ""
            print(f"    - {sub['name']} [{sub_status}] {extra}")
            if sub.get("children"):
                for subsub in sub["children"]:
                    s3_status = "VIZIBIL" if subsub["visible"] else "ASCUNS"
                    s3_extra = f"({subsub.get('feature_count')} corpuri)" if subsub.get("feature_count") is not None else ""
                    print(f"        * {subsub['name']} [{s3_status}] {s3_extra}")

print("\n--- 3. STRATURILE CADASTRALE DE CORPURI (Analiza Detaliata) ---")
for name, info in data.get("lot_layers_detail", {}).items():
    vis = "DA" if info["visible_in_tree"] else "NU"
    lbl = "DA" if info["labels_enabled"] else "NU"
    print(f"• Strat: '{name}'")
    print(f"    Vizibil in Tree: {vis} | Etichete Active: {lbl} | Total Corpuri: {info['total_features']} | CRS: {info['crs']}")
    if info.get("features_sample"):
        sample_str = ", ".join([f.get("fields", {}).get("body_id", "N/A") + f"({f.get('area_geom')}m2)" for f in info["features_sample"][:4]])
        print(f"    Sample: {sample_str}")
