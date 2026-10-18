"""Read-only reconciliation of Antigravity conversation claims with saved geometry.

Reads user requests, public assistant responses and tool argument metadata only.
Never extracts thinking, model metadata or system instructions for publication.
"""
import collections
import hashlib
import json
import re
import subprocess
from pathlib import Path

import geopandas as gpd
import numpy as np
from shapely.strtree import STRtree

ROOT=Path(__file__).resolve().parents[2]
OUT=Path(__file__).resolve().parent
CID="80fa85ac-8b08-481d-a858-2210a8757155"
TRANSCRIPT=Path.home()/f".gemini/antigravity/brain/{CID}/.system_generated/logs/transcript.jsonl"
rows=[json.loads(s) for s in TRANSCRIPT.read_text(encoding="utf-8").splitlines() if s.strip()]
users=[];finals=[];cwds=collections.Counter()
for r in rows:
    if r["type"]=="USER_INPUT":
        match=re.search(r"<USER_REQUEST>(.*?)</USER_REQUEST>",str(r.get("content","")),re.S)
        if match:
            text=match.group(1).strip()
            # Save only short task descriptions, not private transcripts or pasted instructions.
            users.append({"step":r["step_index"],"time_utc":r.get("created_at"),"request_excerpt":text[:220]})
    if r["type"]=="PLANNER_RESPONSE" and r.get("content"):
        finals.append({"step":r["step_index"],"time_utc":r.get("created_at"),"public_response_characters":len(str(r["content"]))})
    for call in r.get("tool_calls",[]) or []:
        args=call.get("args",{})
        if isinstance(args,str):
            try:args=json.loads(args)
            except (ValueError,TypeError):continue
        if isinstance(args,dict) and "Cwd" in args:
            raw=str(args["Cwd"]).strip('"')
            cwds[raw.replace("\\\\","/").replace("\\","/").lower()]+=1

sets={
 "lot3_v4":("workspace/reviews/lot3_repairs_20261017/selected_v4_orthogonal/lot3_orthogonal.gpkg","ROOF_HYPOTHESES_ORTHO90"),
 "lot4_v4":("workspace/reviews/lot4_20261017/selected_v4_orthogonal/lot4_orthogonal.gpkg","ROOF_HYPOTHESES_ORTHO90"),
 "full_auto_264":("workspace/reviews/auto_unvectorized_20261018/auto_unvectorized_orthogonal.gpkg","ROOF_HYPOTHESES_ORTHO90"),
 "lot5_option_a":("workspace/reviews/comparatie_a_vs_b_20261018/comparatie_a_vs_b.gpkg","LOT5_OPTIUNEA_A_ROOF"),
 "option_b_216":("workspace/reviews/comparatie_a_vs_b_20261018/comparatie_a_vs_b.gpkg","OPTIUNEA_B_ROOF_VALIDAT"),
}
results={"conversation_id":CID,"source_transcript_sha256":hashlib.sha256(TRANSCRIPT.read_bytes()).hexdigest(),
 "user_count":len(users),"public_response_count":len(finals),"tool_workdirs":dict(cwds),
 "head":subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT).decode().strip(),
 "selected_conversation_events":[u for u in users if u["step"] in [41,164,356,500,506,635,766,768,821,831,903,1001]],
 "public_response_index":finals,"datasets":{}}

for key,(path,layer) in sets.items():
    df=gpd.read_file(ROOT/path,layer=layer)
    tree=STRtree(df.geometry.values);features=[];pairs=[]
    for i,(_,row) in enumerate(df.iterrows()):
        g=row.geometry
        p=g if g.geom_type=="Polygon" else max(g.geoms,key=lambda x:x.area)
        item={"body_id":str(row.get("body_id",i)),"area_m2":float(g.area),"nodes":len(p.exterior.coords)-1,
              "holes":len(p.interiors),"valid":bool(g.is_valid),"bounds":list(g.bounds)}
        for name in ["owner_verdict","agent_status","ortho_after","hausdorff_m","v_before","v_after","vertices_before","vertices_after"]:
            if name in row:
                v=row[name];item[name]=v.item() if hasattr(v,"item") else v
        xy=np.asarray(p.exterior.coords)[:-1]
        u=xy-np.roll(xy,1,axis=0);v=np.roll(xy,-1,axis=0)-xy
        denom=np.linalg.norm(u,axis=1)*np.linalg.norm(v,axis=1)
        theta=np.degrees(np.arccos(np.clip(np.sum(u*v,axis=1)/np.maximum(denom,1e-15),-1,1)))
        rem=theta%90;item["max_deviation_from_90_multiple_deg"]=float(np.minimum(rem,90-rem).max())
        features.append(item)
        for j in tree.query(g):
            if int(j)<=i:continue
            area=g.intersection(df.geometry.iloc[int(j)]).area
            if area>0.05:pairs.append({"a":item["body_id"],"b":str(df.iloc[int(j)].get("body_id",j)),"area_m2":float(area)})
    results["datasets"][key]={"source":path,"layer":layer,"sha256":hashlib.sha256((ROOT/path).read_bytes()).hexdigest(),
        "count":len(df),"crs":str(df.crs),"overlap_pairs_above_005m2":pairs,"features":features}

path=ROOT/sets["lot4_v4"][0]
raw=gpd.read_file(path,layer="RAW_CANDIDATES_BEFORE").set_index("body_id")
roof=gpd.read_file(path,layer="ROOF_HYPOTHESES_ORTHO90").set_index("body_id")
diag=gpd.read_file(path,layer="T22_DIAGNOSTIC_LIDAR").geometry.iloc[0]
results["lot4_comparison"]=[]
for bid,row in roof.iterrows():
    a=raw.loc[bid].geometry;b=row.geometry
    results["lot4_comparison"].append({"body_id":bid,"raw_nodes":len(a.exterior.coords)-1,"new_nodes":len(b.exterior.coords)-1,
        "raw_area_m2":a.area,"new_area_m2":b.area,"hausdorff_from_raw_m":a.hausdorff_distance(b),
        "added_area_m2":b.difference(a).area,"removed_area_m2":a.difference(b).area})
b=roof.loc["T22:C1"].geometry
results["t22_diagnostic_comparison"]={"diagnostic_area_m2":diag.area,"regularized_area_m2":b.area,
 "added_outside_diagnostic_m2":b.difference(diag).area,"removed_from_diagnostic_m2":diag.difference(b).area,
 "hausdorff_from_diagnostic_m":diag.hausdorff_distance(b),"hausdorff_attribute":float(roof.loc["T22:C1"].hausdorff_m)}

(OUT/"recheck.json").write_text(json.dumps(results,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
print("workdirs",dict(cwds),"users",len(users),"public_responses",len(finals))
for key,d in results["datasets"].items():
    print(key,"count",d["count"],"overlaps > .05m2",len(d["overlap_pairs_above_005m2"]))
print("LOT4",json.dumps(results["lot4_comparison"]))
print("T22",json.dumps(results["t22_diagnostic_comparison"]))
