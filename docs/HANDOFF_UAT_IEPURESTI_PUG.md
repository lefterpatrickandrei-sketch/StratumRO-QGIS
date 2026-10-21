# Handoff: UAT Iepurești — [ARHIVAT / PROIECT FINALIZAT]

> [!WARNING]
> **STATUT: PROIECT FINALIZAT ȘI ARHIVAT**  
> Cazul UAT Iepurești a avut ca scop exclusiv **extragerea de date deschise (harvesting)** din surse naționale și este **încheiat**.
> Nu mai este în lucru activ. Vezi documentul oficial: [docs/STATUS_UAT_IEPURESTI_ARHIVAT.md](STATUS_UAT_IEPURESTI_ARHIVAT.md).
> Focusul activ al depozitului este exclusiv **Cadastrul Cluj-Napoca**.

---


## Rol

Ești **Codex MAIN**, orchestrator principal. Ai acces la:
- **QGIS MCP** (`qgis.*`) pentru sesiunea QGIS Desktop vie, pe portul `9876`
- **Headless processing**: `qgis_process-qgis.bat --skip-loading-plugins run <algorithm_id> -- <params>` sau PyQGIS prin `o4w_env.bat` + `bin\python.exe`
- **Cline CLI** ca worker subordonat, delegat exclusiv în worktree-uri izolate (`cline --plan --worktree "..."` / `cline --cwd ... "..."`)
- **OpenCode + DCP** pentru refactoring greu multi-fișier / context pruning

Nu modifici `main` direct. Tot ce produci trece prin branch-uri dedicate, worktree-uri izolate, review și confirmare explicită înainte de orice integrare.

---

## 1. Problemă activă de rezolvat înainte de orice altceva

Screenshot curent din QGIS Desktop arată:

```
QGIS MCP: Port 9876 is already in use - another QGIS window or program is on it.
Pick a different port for this window.
```

**Acțiune imediată:**
1. Verifică prin `Get-Process qgis-bin*` / `Get-NetTCPConnection -LocalPort 9876` câte instanțe QGIS rulează și care deține portul.
2. Dacă există o instanță QGIS "fantomă" (zombie) rămasă din sesiuni anterioare (vezi istoricul: procese care nu răspundeau la `ping`/`get_state` mai devreme), închide-o explicit, nu forța kill fără verificare.
3. Repornește MCP-ul pe instanța corectă și confirmă cu `qgis.ping` + `qgis.diagnose` că `connected_clients: 1` și că versiunile server/plugin (`0.14.1`) coincid.
4. Abia după ce MCP e sănătos, reia lucrul pe proiect. Nu rula comenzi `qgis.*` în paralel cu o instanță pe conflict de port — riști să scrii peste starea greșitei ferestre.

---

## 2. Politica Dual-Mode (deja stabilită, se păstrează)

| Situație | Canal | Note |
|---|---|---|
| QGIS Desktop deschis, port 9876 liber, `qgis.ping` = healthy | **QGIS MCP** (`qgis.*`) | Manipulare proiect, layer tree, stiluri, zoom, layout-uri, salvare |
| QGIS Desktop închis SAU algoritmi grei de procesare | **Headless** | `qgis_process-qgis.bat --skip-loading-plugins run <alg> -- <params>` sau PyQGIS via `o4w_env.bat` |

Reguli:
- Python-ul QGIS (3.12.7, `o4w_env.bat`) e **separat** de venv-ul proiectului (`Downloads\QGIS-AI\venv`, folosit pentru `laspy`, `geopandas`, teste). Nu le amesteca.
- Orice modificare de proiect prin MCP trebuie verificată apoi cu `qgis.get_project_info` + `qgis.get_layer_tree` înainte de `qgis.save_project`.
- `qgis.execute_code` e disponibil pentru operații care nu au tool dedicat (stiluri, layout-uri, custom layer order) — dar orice cod acolo trebuie să fie verificat linie cu linie înainte de execuție (nu improviza pe proiectul live fără să fi văzut întâi starea curentă a straturilor).

---

## 3. Starea reală a datelor (audit confirmat, nu presupune nimic peste asta)

Sursă: GeoPackage `UAT_Iepuresti.gpkg`, worktree `feature/ancpi-footprint-validation`.

| Layer | Entități | CRS | Sursă | Stare |
|---|---:|---|---|---|
| `limita_UAT` | 1 | EPSG:3844 | OSM/Nominatim | **neconfirmată oficial** (nu e ANCPI/INSPIRE) |
| `limita_intravilan` | 0 | — | — | **DATA GAP** |
| `imobile_cadastrale` | 0 | — | — | **DATA GAP** |
| `constructii` | 648 | EPSG:3844 | OSM buildings + buffer exterior +0.50 m | geometrii valide |
| `drumuri_poligon` | 179 | EPSG:3844 | axe OSM bufferizate cu 3 m | **aproximare tehnică**, nu amprize oficiale |
| `drumuri_ax` | 179 | EPSG:3844 | OSM | — |
| `cursuri_apa` | 6 | EPSG:3844 | OSM `waterway` | acoperire posibil incompletă |
| `paduri` | 3 | EPSG:3844 | OSM `natural=wood`/`landuse=forest` | acoperire posibil incompletă |

**Nu trata niciodată aceste date ca fiind un PUG aprobat sau ca zonificare funcțională.** Sunt exclusiv o bază cartografică de fundamentare din date deschise.

---

## 4. De ce nu poate fi produs un "PUG" complet doar prin AI + OSM

Un Plan Urbanistic General presupune, conform cadrului legal românesc (Legea 350/2001, art. 46 și 46¹; Ordinul 233/2016 cu modificările ulterioare):

- piese scrise (memoriu, regulament local de urbanism — RLU)
- diagnostic multicriterial (demografie, infrastructură, mediu, patrimoniu)
- zonificare funcțională aprobată
- delimitare oficială de intravilan
- studii de fundamentare (geotehnic, hidrologic, rețele edilitare)
- consultare publică
- avize de la instituții abilitate (mediu, sănătate, protecție civilă etc.)
- aprobare prin hotărâre de consiliu local

**Nimic din toate acestea nu poate fi generat legitim doar din OSM + orchestrare AI.** Ce se poate produce corect este o **planșă de situație existentă** (bază cartografică de fundamentare), clar marcată ca atare, cu golurile de date explicite, NU o propunere de reglementare.

---

## 5. Structura corectă a proiectului (ce se cere acum)

Redenumește/reorganizează arborele de straturi în QGIS (prin MCP, cu grijă să nu deconectezi layerele din registry — vezi incidentul anterior unde `root.removeAllChildren()` a rupt referințele) astfel:

```
00_CONTROL          -> limita_UAT (marcată "sursă neoficială"), limita_intravilan (gol)
01_FUNDAL           -> Esri World Imagery (sau alt WMS/XYZ)
02_EXISTENT         -> constructii, drumuri_poligon, drumuri_ax, cursuri_apa, paduri
03_PUG_PROPUNERI    -> GOL intenționat — nu popula cu date inventate
04_RESTRICTII       -> GOL intenționat — riscuri, servituți, protecții (necesită surse oficiale)
05_DATE_LIPSA       -> imobile_cadastrale, limita_intravilan (placeholder, vizibilitate OFF)
06_QA_QC            -> jurnal de proveniență, verificări de validitate geometrică
```

**Regulă strictă:** grupurile `03_PUG_PROPUNERI` și `04_RESTRICTII` rămân goale sau primesc doar geometrii marcate explicit "SCENARIU CONCEPTUAL — NEAPROBAT" dacă se cere un exercițiu ipotetic. Niciodată nu se prezintă ca reglementare reală.

---

## 6. Plan de execuție (delegare Cline + headless + MCP)

### Pas 1 — Reparare MCP (blocant)
Manual/Codex direct, nu se delegă. Vezi secțiunea 1.

### Pas 2 — Reconstrucție sigură a arborelui (MCP, cod verificat înainte de rulare)
```python
# Mutare noduri fără a rupe referințele la layere:
# folosește group.addLayer(layer) / group.insertChildNode()
# NU folosi root.removeAllChildren() urmat de reasignare pe alt obiect QgsProject
```
Verifică după fiecare pas cu `qgis.get_layer_tree` că toate straturile rămân `valid: true`.

### Pas 3 — Delegare validare geometrică (headless, prin Cline într-un worktree izolat)
```powershell
cline --cwd "<worktree>" --auto-approve true "Rulează native:fixgeometries și un raport de validitate pe toate layerele din UAT_Iepuresti.gpkg folosind qgis_process headless. Nu modifica GeoPackage-ul original — scrie output în fișiere temporare. Raportează geometrii invalide, self-intersections, duplicate."
```

### Pas 4 — Raport de proveniență (QA_QC)
Generează în `06_QA_QC` (ca strat text/tabel sau ca fișier markdown separat, nu ca geometrie fictivă) un tabel cu: sursă, dată extragere, URL Overpass/Nominatim folosit, limitări cunoscute — pentru fiecare layer din secțiunea 3.

### Pas 5 — Layout de prezentare (planșă A3, prin MCP `execute_code`)
Reia layout-ul `PUG_01_Situatie_Existenta` întrerupt anterior, dar:
- verifică întâi că toate cheile `layers[...]` există (`print([l.name() for l in QgsProject.instance().mapLayers().values()])`) înainte de a le referenția în cod
- păstrează explicit în layout caseta „DOCUMENT DE LUCRU — NU ESTE PUG APROBAT”

### Pas 6 — Raport final Codex MAIN
Format standard (Status / Modificări izolate / Rezultate teste / Riscuri / Decizie necesară), branch dedicat, fără merge în `main`, fără suprascrierea `StratumRO_Rezultate.qgs`.

---

## 7. Limite pe care orchestratorul (și Cline) nu trebuie să le depășească

- Nu inventa coordonate, limite de intravilan sau zonificări.
- Nu prezenta bufferul de +0.50 m sau amprizele de 3 m drept măsurători cadastrale oficiale.
- Nu eticheta planșa produsă drept "PUG" fără calificativul "document de lucru / bază de fundamentare, neaprobat".
- Nu comite/mergiu în `main` fără aprobare explicită.
- Nu rula concomitent MCP pe un port conflictual — verifică sănătatea conexiunii înainte de fiecare sesiune de modificări.

---

## 8. Ce lipsește real pentru pasul următor (de cerut utilizatorului, nu de inventat)

1. Limită oficială de intravilan (PUG anterior / date vectoriale de la primărie sau ANCPI)
2. Date cadastrale autorizate pentru `imobile_cadastrale`
3. Confirmarea limitei UAT față de geoportalul ANCPI/INSPIRE
4. Studii de fundamentare (dacă se dorește avansarea reală spre un PUG, nu doar o planșă de situație existentă)

Fără acestea, orice etapă următoare rămâne la nivelul de bază cartografică de fundamentare — corect livrabilă, dar explicit non-reglementară.