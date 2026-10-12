# -*- coding: utf-8 -*-
"""
StratumRO — Human-in-the-Loop (HITL) Feedback Bridge for QGIS Desktop 3.40.
=============================================================================
Enables the surveyor to select features with the mouse in the QGIS canvas
(or pass specific FIDs via CLI) and issue deterministic geomatics commands:
  - status:      Inspects selected features (area, vertices, centroid Stereo 70)
  - merge:       Unions split building bodies, bridges seams & regularizes at 90°
  - regularize:  Enforces strict 90° Manhattan geometry & removes jagged teeth
  - delete:      Removes false positive buildings or noise features
  - set_offset:  Adjusts eave ground foundation retraction (-0.40m, -0.50m)

Works both live via TCP socket 127.0.0.1:9876 (QGIS MCP) and in direct offline
mode on workspace/output/cladiri_stereo70.gpkg.
"""

import os
import sys
import json
import math
import socket
import struct
import argparse
from typing import Dict, Any, List, Optional, Tuple

import geopandas as gpd
from shapely.geometry import shape, mapping, Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely import wkt

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, PROJECT_ROOT)

from stratum_ro.vectorizer import CadastralVectorizer, orthogonalize_cad, _extract_largest_polygon

HOST = "127.0.0.1"
PORT = 9876
GPKG_PATH = os.path.join(PROJECT_ROOT, "workspace", "output", "cladiri_stereo70.gpkg")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def is_qgis_socket_alive() -> bool:
    """Checks if the QGIS MCP server is active on localhost:9876."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.8)
            s.connect((HOST, PORT))
            return True
    except (socket.error, ConnectionRefusedError, socket.timeout):
        return False


def send_mcp(command_type: str, params: Optional[Dict[str, Any]] = None, timeout: float = 10.0) -> Dict[str, Any]:
    """Sends framed JSON request to QGIS MCP server and returns decoded response."""
    if params is None:
        params = {}

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(timeout)
        s.connect((HOST, PORT))

        req = {"type": command_type, "params": params}
        payload = json.dumps(req).encode("utf-8")
        s.sendall(struct.pack(">I", len(payload)) + payload)

        raw_len = s.recv(4)
        if len(raw_len) != 4:
            raise RuntimeError("Failed to read length prefix from QGIS MCP")

        resp_len = struct.unpack(">I", raw_len)[0]
        data = bytearray()
        while len(data) < resp_len:
            chunk = s.recv(min(65536, resp_len - len(data)))
            if not chunk:
                break
            data.extend(chunk)

        res = json.loads(data.decode("utf-8"))
        if not res.get("success", True) and "error" in res:
            raise RuntimeError(f"QGIS MCP Error ({res.get('error', {}).get('code')}): {res.get('error', {}).get('message')}")
        return res


def find_layer_by_keyword(keyword: str) -> Optional[Dict[str, Any]]:
    """Locates a vector layer in the current QGIS project matching keyword."""
    res = send_mcp("get_layers", {"limit": 100})
    layers = res.get("result", {}).get("layers", [])

    kw_lower = keyword.lower()
    for lyr in layers:
        name = lyr.get("name", "")
        if kw_lower in name.lower() and lyr.get("geometry_type") is not None:
            return lyr

    for lyr in layers:
        if keyword == lyr.get("id"):
            return lyr

    return None


def execute_hitl(action: str, layer_kw: str = "Clădiri Sol", fids: Optional[List[int]] = None, offset_m: float = 0.40):
    """Executes the requested HITL geomatics operation."""
    vec = CadastralVectorizer(crs="EPSG:3844")
    online = is_qgis_socket_alive()

    layer_gpkg_name = "CLADIRI_SOL_ANCPI" if "sol" in layer_kw.lower() else "CLADIRI_CADASTRU_CLEAN"
    
    print("=" * 70)
    print("  STRATUM-RO — HUMAN-IN-THE-LOOP (HITL) CADASTRAL BRIDGE")
    print("=" * 70)
    print(f"[*] Canal QGIS Socket (127.0.0.1:9876): {'ONLINE (Activ)' if online else 'OFFLINE (Mod Direct GPKG)'}")

    qgis_layer_id = None
    target_fids = list(fids) if fids else []

    if online:
        layer_meta = find_layer_by_keyword(layer_kw)
        if layer_meta:
            qgis_layer_id = layer_meta["id"]
            print(f"[+] Conectat la stratul QGIS: '{layer_meta['name']}' (ID: {qgis_layer_id})")
            if not target_fids:
                sel_res = send_mcp("get_selection", {"layer_id": qgis_layer_id})
                target_fids = sel_res.get("result", {}).get("fids", [])
        else:
            print(f"[!] Stratul '{layer_kw}' nu a fost găsit în proiectul QGIS activ. Folosim fallback direct.")

    if not target_fids:
        if not online:
            print("[-] Eroare: Niciun FID specificat prin argumentul --ids în modul offline.")
            print("    Exemplu utilizare: python tools/hitl_feedback_bridge.py --action merge --ids 14,15")
            return False
        else:
            print("[!] Nicio entitate nu este selectată în canvas-ul QGIS.")
            print("    -> Selectează clădirile dorite cu unealta 'Select Feature' și re-rulează comanda.")
            return False

    print(f"[+] Entități selectate ({len(target_fids)}): {target_fids}")

    # Citim datele din GPKG
    if not os.path.exists(GPKG_PATH):
        print(f"[-] Fișierul {GPKG_PATH} nu există.")
        return False

    gdf = gpd.read_file(GPKG_PATH, layer=layer_gpkg_name)
    # Găsim coloana de identificare (id sau fid sau index)
    if "fid" not in gdf.columns:
        gdf["fid"] = gdf.index + 1
    
    if "id" in gdf.columns and any(gdf["id"].isin(target_fids)):
        id_col = "id"
        selected_rows = gdf[gdf["id"].isin(target_fids)]
    else:
        id_col = "fid"
        selected_rows = gdf[gdf["fid"].isin(target_fids)]

    if selected_rows.empty:
        print(f"[-] Nicio entitate cu ID-urile {target_fids} nu a fost găsită în stratul {layer_gpkg_name}.")
        return False

    # 1. ACTION: STATUS
    if action == "status":
        print("\n--- RAPORT ENTITĂȚI SELECTATE ---")
        for idx, row in selected_rows.iterrows():
            geom = row.geometry
            c = geom.centroid
            # Stereo 70: X=Nord (~585000), Y=Est (~392000)
            n_vertices = len(geom.exterior.coords) if hasattr(geom, "exterior") else sum(len(p.exterior.coords) for p in geom.geoms)
            print(f"  • FID {row[id_col]}: Arie={geom.area:.2f} mp, Noduri={n_vertices}, Centroid: Nord(X)={c.y:.2f}m, Est(Y)={c.x:.2f}m")
        return True

    # 2. ACTION: DELETE
    elif action == "delete":
        print(f"\n[...] Se elimină {len(target_fids)} entități selectate...")
        gdf_clean = gdf[~gdf[id_col].isin(target_fids)].copy()
        gdf_clean.to_file(GPKG_PATH, layer=layer_gpkg_name, driver="GPKG")
        print(f"[+] Salvat pe disc în GeoPackage ({len(gdf_clean)} entități rămase).")

        if online and qgis_layer_id:
            try:
                send_mcp("delete_features", {"layer_id": qgis_layer_id, "fids": target_fids})
                send_mcp("clear_selection", {"layer_id": qgis_layer_id})
                print("[+] Canvas QGIS reîmprospătat în timp real.")
            except Exception as e:
                print(f"[!] QGIS Sync avertisment: {e}")
        return True

    # 3. ACTION: MERGE (Unește două bucăți de clădire și închide fanta)
    elif action == "merge":
        if len(selected_rows) < 2:
            print("[!] Acțiunea 'merge' necesită selectarea a cel puțin 2 corpuri de clădire.")
            return False

        print(f"\n[...] Se unifică {len(selected_rows)} corpuri de clădire...")
        geoms = list(selected_rows.geometry)
        merged = unary_union(geoms)

        # Închidere fantă prin punte morfologică (dilation + erosion) dacă fanta <= 0.80m
        if isinstance(merged, MultiPolygon) or not merged.is_valid:
            bridged = merged.buffer(0.45).buffer(-0.45)
            merged = _extract_largest_polygon(bridged) or merged

        # Regularizare cad la 90 de grade
        if isinstance(merged, Polygon):
            merged_clean = vec.clean_cad_polygon(merged, tolerance=0.7)
        else:
            merged_clean = merged

        primary_fid = target_fids[0]
        other_fids = target_fids[1:]

        # Actualizare GeoPackage
        gdf.loc[gdf[id_col] == primary_fid, "geometry"] = merged_clean
        if "area_sol_m2" in gdf.columns:
            gdf.loc[gdf[id_col] == primary_fid, "area_sol_m2"] = merged_clean.area
        elif "area_sol" in gdf.columns:
            gdf.loc[gdf[id_col] == primary_fid, "area_sol"] = merged_clean.area
        gdf_updated = gdf[~gdf[id_col].isin(other_fids)].copy()
        gdf_updated.to_file(GPKG_PATH, layer=layer_gpkg_name, driver="GPKG")
        print(f"[+] Unificare completă pe disc: FID {primary_fid} a preluat corpul unificat ({merged_clean.area:.2f} mp).")

        if online and qgis_layer_id:
            try:
                send_mcp("update_feature_geometry", {
                    "layer_id": qgis_layer_id,
                    "updates": [{"fid": primary_fid, "geometry_wkt": merged_clean.wkt}]
                })
                send_mcp("delete_features", {"layer_id": qgis_layer_id, "fids": other_fids})
                send_mcp("clear_selection", {"layer_id": qgis_layer_id})
                print("[+] Canvas QGIS sincronizat live (<1.5s): fanta a fost închisă!")
            except Exception as e:
                print(f"[!] QGIS Sync avertisment: {e}")
        return True

    # 4. ACTION: REGULARIZE (Curăță zimții și forțează unghiuri de 90°)
    elif action == "regularize":
        print(f"\n[...] Se regularizează {len(selected_rows)} poligoane la unghiuri drepte de 90°...")
        updates = []
        for idx, row in selected_rows.iterrows():
            fid_val = row[id_col]
            geom = row.geometry
            if isinstance(geom, Polygon):
                reg_geom = vec.clean_cad_polygon(geom, tolerance=0.7)
            elif isinstance(geom, MultiPolygon):
                parts = [vec.clean_cad_polygon(p, tolerance=0.7) for p in geom.geoms]
                reg_geom = MultiPolygon([p for p in parts if p is not None and not p.is_empty])
            else:
                reg_geom = geom

            gdf.loc[gdf[id_col] == fid_val, "geometry"] = reg_geom
            updates.append({"fid": fid_val, "geometry_wkt": reg_geom.wkt})
            print(f"  • FID {fid_val}: noduri inițiale={len(geom.exterior.coords) if hasattr(geom, 'exterior') else 'N/A'} -> după regularizare={len(reg_geom.exterior.coords) if hasattr(reg_geom, 'exterior') else 'N/A'}")

        gdf.to_file(GPKG_PATH, layer=layer_gpkg_name, driver="GPKG")
        print("[+] Poligoane regularizate salvate pe disc.")

        if online and qgis_layer_id:
            try:
                send_mcp("update_feature_geometry", {
                    "layer_id": qgis_layer_id,
                    "updates": updates
                })
                send_mcp("clear_selection", {"layer_id": qgis_layer_id})
                print("[+] Canvas QGIS actualizat live: contururi perfect ortogonalizate!")
            except Exception as e:
                print(f"[!] QGIS Sync avertisment: {e}")
        return True

    # 5. ACTION: SET_OFFSET
    elif action == "set_offset":
        print(f"\n[...] Se aplică retragere streașină de -{abs(offset_m):.2f}m...")
        updates = []
        for idx, row in selected_rows.iterrows():
            fid_val = row[id_col]
            geom = row.geometry
            offset_geom = geom.buffer(-abs(offset_m))
            if not offset_geom.is_empty and offset_geom.is_valid:
                gdf.loc[gdf[id_col] == fid_val, "geometry"] = offset_geom
                updates.append({"fid": fid_val, "geometry_wkt": offset_geom.wkt})

        gdf.to_file(GPKG_PATH, layer=layer_gpkg_name, driver="GPKG")
        print("[+] Retragere aplicată pe disc.")

        if online and qgis_layer_id:
            try:
                send_mcp("update_feature_geometry", {
                    "layer_id": qgis_layer_id,
                    "updates": updates
                })
                send_mcp("clear_selection", {"layer_id": qgis_layer_id})
                print("[+] Canvas QGIS actualizat live cu noua retragere.")
            except Exception as e:
                print(f"[!] QGIS Sync avertisment: {e}")
        return True

    return True


def main():
    parser = argparse.ArgumentParser(description="StratumRO QGIS HITL Feedback Bridge")
    parser.add_argument("--action", choices=["status", "merge", "regularize", "delete", "set_offset"], default="status",
                        help="Acțiunea de executat pe selecția curentă")
    parser.add_argument("--layer", default="Clădiri Sol", help="Cuvânt cheie pentru identificarea stratului țintă")
    parser.add_argument("--ids", type=str, default="", help="Listă opțională de FIDs separate prin virgulă (ex: --ids 1,2)")
    parser.add_argument("--offset", type=float, default=0.40, help="Distanța de offset în metri")

    args = parser.parse_args()
    parsed_ids = [int(x.strip()) for x in args.ids.split(",") if x.strip().isdigit()] if args.ids else None
    execute_hitl(args.action, args.layer, parsed_ids, args.offset)


if __name__ == "__main__":
    main()
