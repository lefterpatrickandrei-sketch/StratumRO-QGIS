# -*- coding: utf-8 -*-
"""Independent local G3 coverage checks and handoff report."""
from pathlib import Path
import json, hashlib
import numpy as np
from osgeo import gdal, ogr
gdal.UseExceptions()
root = Path(__file__).resolve().parents[1]
qa = json.loads((root / "qa/03_raster_validation.json").read_text(encoding="utf-8"))
state = json.loads((root / "state/state.json").read_text(encoding="utf-8"))
assert qa["status"] == "COMPLETE" and state["gate"] == "G3_complete"
vector = ogr.Open(str(root / "data/processed/ancpi/limita_UAT.geojson"))
layer = vector.GetLayer(0)
checks = []
for f in qa["files"]:
    path = root / f["path"]
    ds = gdal.Open(str(path))
    arr = ds.GetRasterBand(1).ReadAsArray()
    mask = gdal.GetDriverByName("MEM").Create("", ds.RasterXSize, ds.RasterYSize, 1, gdal.GDT_Byte)
    mask.SetGeoTransform(ds.GetGeoTransform())
    mask.SetProjection(ds.GetProjection())
    layer.ResetReading()
    gdal.RasterizeLayer(mask, [1], layer, burn_values=[1])
    inside = mask.GetRasterBand(1).ReadAsArray() == 1
    total = int(inside.sum())
    zero = int((arr[inside] == 0).sum())
    assert total > 0 and zero == 0, (f["band"], total, zero)
    assert hashlib.sha256(path.read_bytes()).hexdigest() == f["sha256"]
    checks.append({"band": f["band"], "uat_pixels": total, "nodata_zero_pixels": zero,
                   "valid_uat_percent": 100.0, "sha256_matches": True, "evidence_class": "MEASURED"})
    print(f["band"], total, "UAT pixels;", zero, "nodata; SHA256 PASS")
(root / "qa/03_independent_checks.json").write_text(json.dumps(checks, indent=2), encoding="utf-8")
(root / "scripts/requirements-g3.txt").write_text(
    "pystac-client==0.9.0\nplanetary-computer==1.0.0\nrasterio==1.4.3\nnumpy==1.26.4\n", encoding="utf-8")
files = [
"scripts/03_raster_validation.py", "scripts/03_verify_local.py", "scripts/requirements-g3.txt",
"state/state.before_G3.json", "state/state.json", "logs/03_raster_validation.log",
"provenance/03_sentinel2_collection.json", "provenance/03_sentinel2_candidates.json",
"provenance/03_sentinel2_selected_item.json", "qa/03_raster_validation.json",
"qa/03_independent_checks.json", "qa/03_raster_validation.md"
] + [f["path"] for f in qa["files"]] + [
str(Path(f["path"]).with_suffix(".source.json")) for f in qa["files"]]
rows = "\n".join("| {band} | {bytes:,} | {crs} | 763 x 1101 | PASS |".format(**f) for f in qa["files"])
report = f"""# G3 — UAT Iepurești: validare raster

Stare: **G3_complete**. Execuția scriptului principal: **exit code 0**.
Proiect: {root}. Data verificării: {qa["completed_at"]}.
Dovezi numerice: **MEASURED**, fără validare cadastrală în teren.

## Selecție

- Scenă: {qa["item_id"]}
- Achiziție UTC: {qa["acquired_at"]}
- Interval căutat: {qa["search_interval"]}
- {qa["candidate_count"]} scene găsite; {qa["eligible_count"]} acoperă integral UAT și au toate benzile.
- Nori raportați pentru scena întreagă: {qa["scene_cloud_percent"]}%. Procentul local de nori nu a fost măsurat.
- Extinderea calculată prin OGR din limita OSM existentă: {qa["aoi_bbox_wgs84"]}.
- Limita este REFERENCE, nu limită oficială ANCPI.

## Fișiere raster și verificări

| Bandă | Octeți | CRS sursă | Dimensiuni | Verificări |
|---|---:|---|---|---|
{rows}

Cele patru fișiere sunt decupaje dreptunghiulare AOI ale COG-urilor originale,
la 10 m, UInt16, cu aceeași grilă. **Nu sunt tile-uri satelitare complete.**
GDAL a calculat fereastra din geometria UAT; pixelii de bază sunt identici
cu sursa, fără reeșantionare. Au fost verificate COG layout, citirea completă,
SHA-256, acoperirea geometrică și datele nenule în interiorul poligonului.
Verificarea independentă: {checks[0]["uat_pixels"]:,} pixeli UAT/bandă,
0 pixeli cu valoarea nodata Sentinel 0, acoperire cu date 100%.

CRS rastere brute: EPSG:32635. Validarea cu cutline a fost executată în memorie
în EPSG:3844. CRS masterului vectorial rămâne EPSG:3844.

## Licență și utilizare

Sentinel: Copernicus Sentinel Data Legal Notice, condiții cunoscute.
[Termeni oficiali](https://cds.climate.copernicus.eu/licences/ec-sentinel).
Atribuire pentru decupaje: {qa["attribution"]}.
Catalogul STAC raportează literal proprietary; valoarea este păstrată
în proveniență și nu a fost reinterpretată ca licență Creative Commons.

Esri World Imagery: **NOT_USED**; **LICENSE_CHECK = NOT_APPLICABLE**.

SAM2: **DISABLED_FALLBACK**, păstrat din inventarul G1. Rasterele de 10 m sunt
suport contextual; nu justifică precizie de 0,50 m sau contururi cadastrale
ale clădirilor. G4–G7 nu au fost executate.

## Mediu și testare

Dependențele sunt izolate în data/cache/g3_python și sunt folosite prin
python-qgis.bat. NumPy 1.26.4 și Rasterio 1.4.3 evită incompatibilitatea ABI
întâlnită cu NumPy 2.5.3. Importurile celor patru pachete au trecut, exit code 0.
Instalarea QGIS globală nu a fost modificată de comenzile pip --target.

Verificări G3: toate cele patru benzi au trecut controlul integral GDAL,
egalitatea cu pixelii sursă la extragere și controlul local de acoperire.

Suita generală StratumRO, rulată din directorul proiectului cu Python QGIS,
a raportat 125 teste: 88 reușite, 7 omise, 3 eșecuri și 27 erori, exit code 1.
Printre cauze: căi/importuri ale proiectului, fixture-uri relative indisponibile,
dependențe neinstalate în mediul de bază (ezdxf, fastmcp, fastapi, rasterio)
și disponibilitate ONNX. Acest rezultat nu reproduce raportul istoric al suitei
StratumRO și nu este declarat PASS. Nu s-au făcut remedieri în codul principal.

## Inventar

Directorul dependențelor conține și fișierele pachetelor instalate.
Inventarul rezultatelor, scripturilor și stării:

""" + "\n".join("- " + f for f in files) + """

## Conținutul integral al state/state.json

""" + chr(96)*3 + "json\n" + json.dumps(state, ensure_ascii=False, indent=2) + "\n" + chr(96)*3 + "\n"
(root / "qa/03_raster_validation.md").write_text(report, encoding="utf-8")
print("Independent checks PASS; report saved.")

