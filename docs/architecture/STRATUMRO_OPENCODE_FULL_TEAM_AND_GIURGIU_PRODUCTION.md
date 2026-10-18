# STRATUMRO — OPENCODE FULL MISSION
## TEAM SETUP → VALIDATION → GIURGIU GIS PRODUCTION

**PRIMARY RUNTIME:** OpenCode  
**CANONICAL REPOSITORY:** `C:\Users\lefpa\Downloads\QGIS-AI`  
**GIS APPLICATION:** QGIS  
**GIS BRIDGE:** QGIS MCP  
**OS:** Windows 11 x64  
**OLLAMA:** FORBIDDEN  
**REPO STATE:** existing dirty state = baseline; DO NOT reset/clean/rebase.

---

## 0. INSTRUCȚIUNEA ABSOLUTĂ

**NU TE OPRI** după:

- repository audit;
- `STRATUMRO_ORCHESTRATOR_OK`;
- agent creation;
- provider discovery;
- QGIS MCP discovery.

Aceasta este o **misiune END-TO-END**.

Continuă automat:

```text
AUDIT
→ TEAM SETUP
→ MODEL/PROVIDER VALIDATION
→ MCP/QGIS VALIDATION
→ AGENT TESTS
→ DATA DISCOVERY
→ RASTER/ORTHO VALIDATION
→ QGIS EXECUTION
→ FINAL GIS PRODUCT
→ QA/QC
→ REVIEWER
→ FINAL QGIS PROJECT + REPORTS

Nu opri misiunea decât când:

PRODUCT COMPLETE

sau există un blocaj real demonstrat.

1. PRODUSUL CERUT DE PDF

 Ținta:

UAT GIURGIU

Cerințele produsului sunt:

1. Limita UAT
2. Limita intravilan
3. Imobile cadastrale
4. Vectorizarea construcțiilor după forma acoperișului
   + offset 50 cm
5. Drumuri:
   - tip poligon
   - tip linie / Ax
6. Cursuri de apă
7. Păduri

Aceste cerințe sunt sursa de adevăr pentru produs.

Nu elimina cerințe și nu inventa altele pentru a face produsul să pară mai complet.

2. ECHIPA

Creează sau reutilizează acești agenți:

stratumro-orchestrator
stratumro-architect
stratumro-researcher
stratumro-geospatial
stratumro-qgis
stratumro-coder
stratumro-reviewer

Înainte de a crea duplicate, inspectează:

.opencode/
.agents/
configurația OpenCode existentă

Reutilizează agenții StratumRO existente atunci când sunt compatibili.

3. ORCHESTRATOR

Este agentul principal.

Responsabil:

inspect
plan
delegate
coordinate
integrate
verify

Poate delega către:

Architect
Researcher
Geospatial
QGIS
Coder
Reviewer

Nu face singur toate operațiile dacă un specialist este potrivit.

4. ARCHITECT

Responsabil:

architecture
workflow planning
dependency reasoning
risks
acceptance criteria

Nu refactoriza proiectul pentru această misiune fără necesitate.

5. RESEARCHER

Responsabil:

official source discovery
OGC/WMS/WFS/ArcGIS REST discovery
metadata
source verification
usage conditions
provenance

Prioritizează:

surse oficiale românești
ANCPI
surse instituționale GIS
servicii OGC/ArcGIS verificate
Copernicus / EO ca surse auxiliare când sunt potrivite

Nu inventa endpoint-uri, layer IDs, date sau metadate.

Când ceva nu poate fi verificat:

UNVERIFIED
6. GEOSPATIAL

Responsabil:

CRS
AOI
raster/vector alignment
geometry
topology
spatial validation
QA/QC

Reguli:

NEVER GUESS CRS
NEVER GUESS UNITS
NEVER INVENT COORDINATES
7. QGIS

Acesta este agentul operațional GIS principal.

Trebuie să folosește efectiv:

QGIS MCP
QGIS
Processing
Raster tools
Vector tools
Project
Browser
Layers
CRS
Map Canvas
Symbology
Snapping
Topology
PyQGIS când este justificat
GDAL printr-un runtime valid

QGIS nu trebuie tratat ca simplu viewer.

8. CODER

Intervine numai când:

QGIS Processing nu este suficient;
este nevoie de automatizare;
este nevoie de test;
este justificat un helper PyQGIS.

Înainte de cod:

search existing code
inspect contracts
inspect tests
inspect domain
reuse existing implementation

Nu construi duplicate.

Pentru:

from qgis.core import ...

folosește un runtime PyQGIS valid. Nu presupune că Python generic poate importa QGIS.

9. REVIEWER

Reviewer verifică read-only:

cerințe PDF
surse
CRS
geometry
layer structure
offset
QGIS project
provenance
data gaps
QA/QC

Nu modifica baseline-ul pentru a face testul să treacă.

Nu face commit/push automat.

10. VERSION + CONFIGURATION AUDIT

Înainte de modificarea configurației:

opencode --version
opencode --help
opencode agent --help
opencode run --help
opencode models --help
opencode mcp --help
opencode debug config
opencode debug paths
opencode auth list
opencode mcp list
opencode models

Folosește sintaxa acceptată de versiunea instalată.

Nu copia orbește schema altei versiuni.

11. PROVIDER + MODEL POLICY

Nu presupune că toți agenții trebuie să folosească același model.

Nu copia automat configurația Hermes:

deepseek/deepseek-chat

Mai întâi verifică live providerii și modelele realmente disponibile.

Pentru fiecare candidat:

provider
model
authentication
generation
tool use
latency
error

Apoi atribuie modelele după rol:

Orchestrator → planning + tool use
Architect    → reasoning + architecture
Coder        → coding + tool use
Geospatial   → technical GIS reasoning
QGIS         → fast and reliable tool use
Researcher   → research + synthesis
Reviewer     → verification + careful analysis

Nu declara un model "cel mai bun" universal. Selectează-l numai în raport cu taskul și testul live.

12. CREDENȚIALE

Nu afișa niciodată:

API keys
tokens
Authorization headers
.env values

În rapoarte folosește numai:

PRESENT
MISSING
FAILED
UNVERIFIED

Nu introduce chei în:

opencode.json
agents/*.md
AGENTS.md
reports
Git
screenshots
13. MCP

Inspectează configurația existentă înainte de a crea ceva nou.

Servere cunoscute în StratumRO:

qgis
stratumro
filesystem
dataset_manager
context7

Nu activa toate serverele pentru toți agenții.

Mapare minimă:

QGIS       → qgis
Geospatial → qgis / GIS relevant
Coder      → filesystem / repo relevant
Researcher → web/research
Reviewer   → read-only repo
Orchestrator → minimum necessary
14. QGIS MCP — TEST OBLIGATORIU

Înainte de producție:

QGIS_MCP_READONLY_OK

QGIS agent trebuie să demonstreze:

QGIS available
MCP reachable
tools discoverable
current project readable

Test:

Read the current QGIS project path and currently loaded layer names.
Do not modify anything.

Dacă eșuează:

diagnose
→ documented fallback
→ exact failure report

Nu modifica StratumRO doar pentru a ascunde problema.

15. REPO SAFETY

Verifică:

git -C "C:\Users\lefpa\Downloads\QGIS-AI" rev-parse --show-toplevel
git -C "C:\Users\lefpa\Downloads\QGIS-AI" branch --show-current
git -C "C:\Users\lefpa\Downloads\QGIS-AI" rev-parse HEAD
git -C "C:\Users\lefpa\Downloads\QGIS-AI" status --short

Înregistrează:

BASELINE_DIRTY = TRUE/FALSE

NU executa:

git reset --hard
git clean
git restore .
git checkout .
rebase
automatic branch switching

Nu șterge worktree changes.

Nu modifica:

Ground Truth
baseline
scientific behavior
tests solely to make them pass

Nu recrea dev_sdk/.

16. EXISTING STRATUMRO .agents

Inspectează:

.agents/agents/
.agents/rules/
.agents/skills/

Nu șterge.

Nu muta automat.

Reutilizează ce este bun.

Rolurile deja existente pot include specialiști precum:

architect
geodesy-engineer
gis-engineer
researcher
reviewer
tester
validator
vision-engineer

Dacă sunt echivalente, adaptează-le controlat în loc să le dublezi inutil.

17. DATA DISCOVERY — NU AȘTEPTA INPUT MANUAL

După ce echipa este sănătoasă, nu cere automat utilizatorului să trimită ortofoto.

Caută în:

C:\Users\lefpa\Downloads\QGIS-AI

și în directoarele de date accesibile.

Raster candidates:

.tif
.tiff
.jp2
.vrt
.img
.ecw (numai dacă QGIS îl suportă)

Verifică:

path
format
CRS
resolution
width/height
bands
nodata
extent
metadata
QGIS open status
AOI coverage
visual alignment

Nu presupune că un fișier local este pentru Giurgiu numai pentru că există.

18. SURSE EXTERNE

Dacă datele locale nu sunt suficiente:

1. official Romanian GIS sources
2. institutional GIS services
3. verified OGC / WMS / WFS / ArcGIS REST
4. Copernicus / EO auxiliary data
5. DATA GAP

Verifică înainte de utilizare:

source
endpoint
layer
CRS
coverage
date
usage notes

Nu inventa nimic.

19. AOI GIURGIU

Identifică și verifică UAT Giurgiu.

Verifică:

identity
geometry
CRS
extent

Nu folosi un bounding box arbitrar dacă este disponibilă o geometrie UAT verificată.

Creează:

00_CONTROL/UAT_Giurgiu_AOI
20. REGULA RASTER / ORTHOPHOTO

Inputul vizual principal trebuie să fie:

VALID GEOSPATIAL RASTER / ORTHOPHOTO

Trebuie să treacă:

QGIS OPEN = PASS
CRS = KNOWN
EXTENT = KNOWN
RESOLUTION = KNOWN
AOI COVERAGE = PASS
GEOREFERENCE = PASS
VISUAL ALIGNMENT = PASS

Nu folosi ca input vizual principal:

screenshots
ordinary photographs
unknown images
unregistered images
fabricated imagery

Abia după:

RASTER_VALIDATED

începe vectorizarea.

21. QGIS PROJECT STRUCTURE

Organizează:

00_CONTROL
01_ORTHO_RASTER
02_REFERENCE
03_OUTPUT_VECTOR
04_QA_QC
05_METADATA

Output:

limita_UAT
limita_intravilan
imobile_cadastrale
constructii
drumuri_poligon
drumuri_ax
cursuri_apa
paduri

Folosește GeoPackage ca master local atunci când este adecvat.

22. CERINȚA 1 — LIMITA UAT

Folosește o sursă verificabilă.

Încarcă în QGIS.

Validează:

nume
identitate administrativă
CRS
geometry
23. CERINȚA 2 — INTRAVILAN

Caută o sursă verificabilă.

Dacă nu există o sursă verificabilă:

DATA GAP

Nu desena o limită imaginară.

Continuă celelalte cerințe.

24. CERINȚA 3 — IMOBILE CADASTRALE

Folosește o sursă cadastrală/referențială verificată.

Marchează clar natura sursei.

Nu prezenta automat un serviciu public de vizualizare drept adevăr cadastral juridic.

25. CERINȎA 4 — CONSTRUCȚII

Workflow:

VALID ORTHOPHOTO
→ identify roof footprints
→ candidate/vector extraction
→ geometry cleanup
→ validation
→ 50 cm offset
→ final construction layer

Înainte de offset:

verify CRS
verify metric units

Dacă CRS este în grade:

REPROJECT FIRST

Dacă este metric:

OFFSET = 0.50 m

Documentează:

source
method
CRS
offset
26. CERINȚA 5 — DRUMURI

Creează:

drumuri_poligon
drumuri_ax

Poligon:

road surface

Ax:

road centerline

Nu presupune că axul este mereu doar mijlocul geometric al poligonului dacă sursele arată altceva.

27. CERINȚA 6 — CURSURI DE APĂ

Interpretează din:

raster/orthophoto
+
verified reference data

Nu inventa clase sau diferențieri nesusținute de dovezi.

28. CERINȚA 7 — PĂDURI

Interpretează din:

valid orthophoto
+
verified thematic/reference data

EO poate ajuta la control tematic.

Nu prezenta automat date EO auxiliare drept precizie cadastrală locală.

29. AI / CV

AI/CV poate produce:

building candidates
road candidates
water candidates
forest candidates

dar:

AI CANDIDATE != FINAL GIS TRUTH

Workflow obligatoriu:

AI/CV
→ candidate
→ QGIS geometry processing
→ visual validation
→ QA/QC
→ final output
30. QGIS EXECUTION

Folosește QGIS efectiv pentru:

Project
Browser
Layers
Processing
Raster
Vector
Geometry
CRS
Symbology
Labels
Attribute Table
Field Calculator
Snapping
Topology
Map Canvas
Layout
PyQGIS
GDAL

Terminalul se folosește pentru:

local file discovery
metadata
Git
diagnostics
scripts
tests
API checks

Browser-ul este pentru web/research, nu substitut pentru QGIS.

31. FALLBACK

Pentru fișiere:

filesystem/search
→ terminal
→ QGIS/PyQGIS

Pentru GIS:

QGIS MCP
→ QGIS / Processing
→ PyQGIS în runtime valid

Pentru web:

research/web
→ browser/API

Dacă un tool eșuează, nu abandona imediat taskul.

32. PARALLELISM

Folosește paralelism pentru subtaskuri independente:

Researcher → source discovery
Architect → workflow
Geospatial → CRS/AOI analysis

Ține secvențiale operațiile care modifică aceleași artefacte:

raster selection
→ QGIS processing
→ final vector
→ QA/QC
→ review

Pe sistemul cu 16 GB RAM:

max ~2–3 heavy active tasks

Nu executa simultan multe procesări grele ale aceluiași raster.

33. PERFORMANCE TIMING

Înregistrează wall-clock time:

T0 = mission start
T1 = team ready
T2 = QGIS verified
T3 = data discovery complete
T4 = raster validated
T5 = first useful output
T6 = final output complete
T7 = reviewer complete

Scrie rezultatul în:

workspace/opencode/STRATUMRO_OPENCODE_GIURGIU_TIMING.md
34. QA/QC

Verifică:

geometry validity
self-intersections
duplicate geometries
unexpected overlaps
unexpected gaps
CRS consistency
spatial alignment
AOI containment
attribute consistency
offset correctness
layer naming

Închide și redeschide proiectul QGIS și confirmă că se încarcă.

35. PROVENIENȚĂ

Pentru fiecare output:

output layer
input raster
reference sources
method
processing date
QGIS version
CRS
agent/operator
validation status
36. LIVRABILE FINALE

Creează:

workspace/UAT_Giurgiu/
├── UAT_Giurgiu.qgz
├── data/
│   ├── raster/
│   ├── reference/
│   └── output/
├── qa/
├── metadata/
├── DATA_DISCOVERY_REPORT.md
├── PROCESS_REPORT.md
└── VALIDATION_REPORT.md

Nu suprascrie date originale fără motiv.

37. DATA_DISCOVERY_REPORT

Trebuie să conțină:

sources searched
sources accepted
sources rejected
raster candidates
selected raster
CRS
resolution
extent
AOI coverage
QGIS validation
provenance
usage notes
data gaps
38. PROCESS_REPORT

Trebuie să conțină:

objective
PDF requirements
sources
raster
AOI
CRS
QGIS operations
reference layers
output layers
construction vectorization
50 cm offset
road polygon
road axis
water
forest
cadastral parcels
intravilan
QA/QC
timing
final artifacts
39. VALIDATION_REPORT

Reviewer verifică explicit:

[ ] UAT Giurgiu
[ ] UAT boundary
[ ] intravilan / DATA GAP
[ ] cadastral reference
[ ] valid raster/orthophoto
[ ] CRS
[ ] constructions
[ ] 50 cm offset
[ ] road polygons
[ ] road axes
[ ] watercourses
[ ] forests
[ ] geometry
[ ] spatial alignment
[ ] layer organization
[ ] QGIS project reopens
[ ] provenance
40. DATA GAP VS BLOCKED

O singură cerință lipsă:

DATA GAP

Nu abandona întreaga misiune.

Folosește:

BLOCKED

numai când o precondiție reală împiedică continuarea, de exemplu:

QGIS unavailable
AND no usable fallback

sau:

nu există nicio cale verificabilă de a obține datele absolut necesare
41. FAILURE HANDLING

Dacă agentul sau tool-ul eșuează:

1. capture exact error
2. classify
3. try documented fallback
4. retry maximum once after diagnosis
5. delegate to another specialist if appropriate

Nu face:

blind retry loops
42. NU MODIFICA SCIENTIFIC STRATUMRO

În această misiune nu ai voie să:

rescrii core
modifici Ground Truth
modifici baseline pentru scor
schimbi definițiile științifice
ștergi testele ca să treacă
recreezi dev_sdk

Dacă este necesar cod minim pentru automatizare GIS, documentează exact:

file
reason
change
test
43. FINAL RESPONSE OBLIGATORIU

La final returnează:

STRATUMRO GIURGIU MISSION RESULT

TEAM:
PASS / CONDITIONAL / BLOCKED

QGIS:
PASS / CONDITIONAL / BLOCKED

PRIMARY RASTER:
...

REQUIREMENTS:
1. UAT = ...
2. INTRAVILAN = ...
3. CADASTRAL = ...
4. BUILDINGS + 50 cm = ...
5. ROADS POLYGON + AXIS = ...
6. WATER = ...
7. FOREST = ...

QGIS PROJECT:
...

VALIDATION:
PASS / CONDITIONAL / BLOCKED

TOTAL ELAPSED:
...

DATA GAPS:
...

PROJECT MODIFICATIONS:
...

Nu declara PASS doar pe baza unui răspuns textual.

Trebuie să existe artefactele reale.

44. START COMMAND

Pornește acum misiunea completă.

STRATUMRO OPENCODE FULL GIURGIU MISSION STARTED

DO NOT STOP AT AUDIT.
DO NOT STOP AT STRATUMRO_ORCHESTRATOR_OK.
DO NOT STOP AT AGENT CREATION.
DO NOT STOP AT QGIS MCP DETECTION.

BUILD THE TEAM.
VALIDATE THE TEAM.
FIND THE DATA.
VALIDATE THE RASTER.
USE QGIS.
PRODUCE THE GIS PRODUCT.
RUN QA/QC.
REVIEW.
SAVE THE PROJECT.
WRITE REPORTS.
MEASURE TOTAL TIME.

Obiectivul final este produsul GIS real pentru Giurgiu conform PDF-ului.