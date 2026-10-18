"""Read-only independent checks on Antigravity outputs; never runs its pipelines."""
import hashlib
import json
import subprocess
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.strtree import STRtree

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
SOURCES={
    "rest": ("workspace/reviews/auto_unvectorized_20261018/auto_unvectorized_orthogonal.gpkg", "ROOF_HYPOTHESES_ORTHO90"),
    "option_a": ("workspace/reviews/comparatie_a_vs_b_20261018/comparatie_a_vs_b.gpkg", "LOT5_OPTIUNEA_A_ROOF"),
    "option_b": ("workspace/reviews/comparatie_a_vs_b_20261018/comparatie_a_vs_b.gpkg", "OPTIUNEA_B_ROOF_VALIDAT"),
}

def polygon_parts(g):
    return list(g.geoms) if g.geom_type == "MultiPolygon" else [g]

def describe(g):
    angles=[]; nodes=0
    for p in polygon_parts(g):
        for ring in [p.exterior, *p.interiors]:
            xy=np.asarray(ring.coords)[:-1]; nodes+=len(xy)
            incoming=xy-np.roll(xy,1,axis=0); outgoing=np.roll(xy,-1,axis=0)-xy
            norms=np.linalg.norm(incoming,axis=1)*np.linalg.norm(outgoing,axis=1)
            ok=norms>1e-12
            corner=np.degrees(np.arccos(np.clip(np.sum(incoming*outgoing,axis=1)[ok]/norms[ok],-1,1)))
            # Straight collinear vertices are redundant, but not diagonal turns.
            remainder=corner % 90
            angles.extend(np.minimum(remainder,90-remainder).tolist())
    return {"area_m2":float(g.area),"nodes":nodes,"valid":bool(g.is_valid),
            "max_corner_deviation_from_90_multiple_deg":max(angles,default=None)}

results={"head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT).decode().strip(),
         "scope":"Read-only geometry and persistence audit, not building accuracy or owner acceptance", "datasets":{}}
for key,(path,layer) in SOURCES.items():
    try:
        df=gpd.read_file(ROOT/path,layer=layer)
    except Exception as e:
        results["datasets"][key]={"path":path,"layer":layer,"error":str(e)};continue
    geoms=list(df.geometry);tree=STRtree(geoms); overlaps=[];features=[]
    for i,(_,row) in enumerate(df.iterrows()):
        item=describe(row.geometry);item["body_id"]=str(row.get("body_id",i))
        item["bounds"]=list(row.geometry.bounds)
        for field in ("hausdorff_m","area_diff_pct","owner_verdict","ortho_after","method"):
            if field in row:
                val=row[field]; item[field]=val.item() if hasattr(val,"item") else val
        features.append(item)
        for j in tree.query(row.geometry):
            if int(j)<=i:continue
            area=row.geometry.intersection(geoms[int(j)]).area
            if area>1e-6:overlaps.append({"a":i,"b":int(j),"area_m2":float(area)})
    results["datasets"][key]={"path":path,"layer":layer,"sha256":hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),
        "tracked":bool(subprocess.check_output(["git","ls-files","--",path],cwd=ROOT).strip()),
        "crs":str(df.crs),"count":len(df),"invalid":sum(not g.is_valid for g in geoms),
        "positive_overlap_pairs":overlaps,"max_nodes":max(f["nodes"] for f in features),
        "non90_features_above_1deg":sum(f["max_corner_deviation_from_90_multiple_deg"]>1 for f in features),
        "features":features}
bench=json.loads((ROOT/"workspace/reviews/auto_unvectorized_20261018/stratumro_full_auto_benchmark.json").read_text(encoding="utf-8"))
results["timing_check"]={"total_s_reported":bench["timing_record_seconds"]["total_execution_time_s"],
 "count_reported":bench["inventory_record"]["unique_unvectorized_processed"],
 "total_ms_per_feature":1000*bench["timing_record_seconds"]["total_execution_time_s"]/bench["inventory_record"]["unique_unvectorized_processed"],
 "reported_average_ms":bench["timing_record_seconds"]["average_ms_per_building"],
 "scope":"Existing masks are loaded; no new image segmentation in this timing"}
(OUT/"output_audit.json").write_text(json.dumps(results,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
for key,v in results["datasets"].items():
    print(key,json.dumps({k:x for k,x in v.items() if k not in ("features","positive_overlap_pairs")},ensure_ascii=False))
    if "features" in v:
        print("overlap_pairs",len(v["positive_overlap_pairs"]),"complex",sorted([(f["nodes"],f["body_id"]) for f in v["features"]],reverse=True)[:4])
print("timing",json.dumps(results["timing_check"]))
