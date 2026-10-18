# G3 — UAT Iepurești: validare raster

Stare: **G3_complete**. Execuția scriptului principal: **exit code 0**.
Proiect: C:\Users\lefpa\Downloads\QGIS-AI\projects\UAT_Iepuresti. Data verificării: 2026-09-22T12:25:29.057234+00:00.
Dovezi numerice: **MEASURED**, fără validare cadastrală în teren.

## Selecție

- Scenă: S2C_MSIL2A_20260817T090551_R050_T35TMK_20260817T124254
- Achiziție UTC: 2026-08-17T09:05:51.025000+00:00
- Interval căutat: 2026-03-22T00:00:00Z/2026-09-22T12:24:32Z
- 215 scene găsite; 52 acoperă integral UAT și au toate benzile.
- Nori raportați pentru scena întreagă: 0.000252%. Procentul local de nori nu a fost măsurat.
- Extinderea calculată prin OGR din limita OSM existentă: [25.833709909437268, 44.20158740089577, 25.928612409385632, 44.30015710088856].
- Limita este REFERENCE, nu limită oficială ANCPI.

## Fișiere raster și verificări

| Bandă | Octeți | CRS sursă | Dimensiuni | Verificări |
|---|---:|---|---|---|
| B04 | 1,988,682 | EPSG:32635 | 763 x 1101 | PASS |
| B03 | 1,944,121 | EPSG:32635 | 763 x 1101 | PASS |
| B02 | 1,926,778 | EPSG:32635 | 763 x 1101 | PASS |
| B08 | 1,999,876 | EPSG:32635 | 763 x 1101 | PASS |

Cele patru fișiere sunt decupaje dreptunghiulare AOI ale COG-urilor originale,
la 10 m, UInt16, cu aceeași grilă. **Nu sunt tile-uri satelitare complete.**
GDAL a calculat fereastra din geometria UAT; pixelii de bază sunt identici
cu sursa, fără reeșantionare. Au fost verificate COG layout, citirea completă,
SHA-256, acoperirea geometrică și datele nenule în interiorul poligonului.
Verificarea independentă: 544,490 pixeli UAT/bandă,
0 pixeli cu valoarea nodata Sentinel 0, acoperire cu date 100%.

CRS rastere brute: EPSG:32635. Validarea cu cutline a fost executată în memorie
în EPSG:3844. CRS masterului vectorial rămâne EPSG:3844.

## Licență și utilizare

Sentinel: Copernicus Sentinel Data Legal Notice, condiții cunoscute.
[Termeni oficiali](https://cds.climate.copernicus.eu/licences/ec-sentinel).
Atribuire pentru decupaje: Contains modified Copernicus Sentinel data [2026].
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

- scripts/03_raster_validation.py
- scripts/03_verify_local.py
- scripts/requirements-g3.txt
- state/state.before_G3.json
- state/state.json
- logs/03_raster_validation.log
- provenance/03_sentinel2_collection.json
- provenance/03_sentinel2_candidates.json
- provenance/03_sentinel2_selected_item.json
- qa/03_raster_validation.json
- qa/03_independent_checks.json
- qa/03_raster_validation.md
- data\raw\sentinel2\S2C_MSIL2A_20260817T090551_R050_T35TMK_20260817T124254_AOI_B04.tif
- data\raw\sentinel2\S2C_MSIL2A_20260817T090551_R050_T35TMK_20260817T124254_AOI_B03.tif
- data\raw\sentinel2\S2C_MSIL2A_20260817T090551_R050_T35TMK_20260817T124254_AOI_B02.tif
- data\raw\sentinel2\S2C_MSIL2A_20260817T090551_R050_T35TMK_20260817T124254_AOI_B08.tif
- data\raw\sentinel2\S2C_MSIL2A_20260817T090551_R050_T35TMK_20260817T124254_AOI_B04.source.json
- data\raw\sentinel2\S2C_MSIL2A_20260817T090551_R050_T35TMK_20260817T124254_AOI_B03.source.json
- data\raw\sentinel2\S2C_MSIL2A_20260817T090551_R050_T35TMK_20260817T124254_AOI_B02.source.json
- data\raw\sentinel2\S2C_MSIL2A_20260817T090551_R050_T35TMK_20260817T124254_AOI_B08.source.json

## Conținutul integral al state/state.json

```json
{
  "mission": "UAT_Iepuresti",
  "siruta": 103684,
  "crs": "EPSG:3844",
  "gate": "G3_complete",
  "updated": "2026-09-22T15:25:29.057234+03:00",
  "gate_since": "2026-09-22T15:25:29.057234+03:00",
  "updated_at": "2026-09-22T15:25:29.057234+03:00",
  "system_inventory": {
    "qgis_version": "3.40.0-Bratislava",
    "gdal_version": "3.9.3",
    "python_interpreter": "C:\\Program Files\\QGIS 3.40.0\\bin\\python-qgis.bat",
    "sam2_status": "DISABLED_FALLBACK",
    "crs_policy": "EPSG:3844"
  },
  "layer_schema_verified": true,
  "poduri_geometry_corrected": true,
  "data_sources": {
    "osm": "OK",
    "limita_UAT": "OK",
    "sentinel2": "OK",
    "ancpi_cadastral": "DATA_GAP"
  },
  "data_gaps": [
    {
      "layer": "imobile_cadastrale",
      "reason": "geoportal.ancpi.ro does not resolve (DNS NXDOMAIN); WFS/INSPIRE unreachable, no credentials available"
    },
    {
      "layer": "limita_UAT",
      "reason": "OSM admin_level=8 boundary used as proxy; official ANCPI UAT limit unavailable (geoportal.ancpi.ro unreachable)"
    }
  ],
  "raster_validation": {
    "status": "COMPLETE",
    "item_id": "S2C_MSIL2A_20260817T090551_R050_T35TMK_20260817T124254",
    "acquired_at": "2026-08-17T12:05:51.025+03:00",
    "scene_cloud_percent": 0.000252,
    "candidate_count": 215,
    "eligible_count": 52,
    "search_interval": "2026-03-22T00:00:00Z/2026-09-22T12:24:32Z",
    "aoi_bbox_wgs84": [
      25.833709909437268,
      44.20158740089577,
      25.928612409385632,
      44.30015710088856
    ],
    "license": {
      "status": "KNOWN_TERMS",
      "name": "Copernicus Sentinel Data Legal Notice",
      "stac_license_literal": "proprietary",
      "terms_url": "https://dataspace.copernicus.eu/terms-and-conditions",
      "legal_notice_url": "https://cds.climate.copernicus.eu/licences/ec-sentinel",
      "note": "STAC proprietary is retained verbatim; Sentinel-specific open terms apply, not an assumed CC license."
    },
    "esri_world_imagery": {
      "status": "NOT_USED",
      "LICENSE_CHECK": "NOT_APPLICABLE"
    },
    "sam2_status": "DISABLED_FALLBACK",
    "suitability": "10 m imagery is context only; not suitable for cadastral building outlines or 0.50 m accuracy.",
    "qa_report": "qa/03_raster_validation.json",
    "files": [
      "data\\raw\\sentinel2\\S2C_MSIL2A_20260817T090551_R050_T35TMK_20260817T124254_AOI_B04.tif",
      "data\\raw\\sentinel2\\S2C_MSIL2A_20260817T090551_R050_T35TMK_20260817T124254_AOI_B03.tif",
      "data\\raw\\sentinel2\\S2C_MSIL2A_20260817T090551_R050_T35TMK_20260817T124254_AOI_B02.tif",
      "data\\raw\\sentinel2\\S2C_MSIL2A_20260817T090551_R050_T35TMK_20260817T124254_AOI_B08.tif"
    ],
    "download_mode": "AOI native-grid COG subsets; not full satellite tiles",
    "raw_crs": "EPSG:32635"
  }
}
```
