# G6 — Adversarial Review: UAT Iepurești

**Data revizuirii:** 2026-09-22T13:27:02.585140+00:00
**Stare:** **PASS** (Fără date fabricate, conformitate strictă cu Invariantele I1–I7)

---

## 1. Sunt sursele autoritative sau doar REFERENCE?
* **limita_UAT:** Este o aproximare geometrică extrasă din **OpenStreetMap (admin_level=8)**, având statutul strict de **`REFERENCE`**. Geoportalul ANCPI nu a putut fi interogat la momentul execuției. **Nu reprezintă o graniță cadastrală legală oficială.**
* **Rețele stradale, hidrografie, construcții, fond forestier:** Provin integral din open data OSM (licență ODbL). Oferă suport cartografic contextual, fără valoare de publicitate imobiliară.

## 2. Există date fabricate / coordonate generate de LLM?
* **Nu.** S-a respectat Invariantul **I3** (LLM ≠ geometry). Toate punctele, nodurile și poligoanele au fost transformate și procesate exclusiv prin bibliotecile OGR și GEOS în mediul Python QGIS 3.40.
* Buffer-ul de **+0.50m** pentru `constructii` și cel de **3.0m** pentru `drumuri_poligon` au fost calculate algoritmic, fără intervenție euristică arbitrară.

## 3. Gestionarea golurilor de date (DATA GAP)
* `imobile_cadastrale` a fost marcat drept **DATA GAP** (0 entități). Nu s-a încercat inventarea parcelelor sau interpolarea lor.
* `limita_intravilan` a fost marcat drept **DATA GAP** (0 entități). Datele PUG/GIS nefiind publice în format vectorial deschis, stratul rămâne gol în mod deliberat.

## 4. Statut imagini satelitare și inteligență artificială (SAM2)
* Datele satelitare Sentinel-2 L2A (10 m rezoluție nativă) sunt destinate analizei de context și nu permit delimitarea contururilor cadastrale cu precizie sub-metrică.
* SAM2 rămâne pe starea **`DISABLED_FALLBACK`** conform inventarului tehnic inițial.

---
**Concluzie:** Setul de date din `output/UAT_Iepuresti.gpkg` respectă standardele de integritate, trasabilitate și licențiere deschisă.
