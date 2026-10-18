# Lot3: finisare T17/T18, 2026-10-17

Continuare autorizată de proprietar în repository-ul comun QGIS-AI și în proiectul existent `workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs`. Nu a fost creat un nou proiect de inspecție. Rezultatele sunt ipoteze de acoperiș, nu amprente măsurate la sol și nu rezultate acceptate automat.

## Cauză și corecție reutilizabilă

T17:C1 pierdea legătura de acoperiș de lângă curte: SAM2 omitea o fâșie, iar recuperarea anterioară căuta numai la 1,5 m de mască. Diagnosticul fâșiei omise măsoară circa 63,64 m², fracție Class6 0,933, înălțime mediană 12,27 m și distanță maximă de aproximativ 2,49 m față de masca brută. Aceste valori sunt observații ale datelor disponibile, nu validare independentă a alinierii LiDAR.

`stratum_ro/fusion_refinement.py` recuperează suplimentar suportul interior din aceeași componentă LiDAR, în interiorul anvelopei convexe a măștii și la maximum 3 m de mască. Recuperarea exterioară rămâne limitată la 1,5 m. Filtrele de înălțime, vegetație și suport optic rămân active. Nu există ID-uri T17/T18 sau coordonate de caz în algoritmul generic. Curțile reale sunt păstrate; un gol fără suport nu este umplut. Două regresii verifică legătura susținută și refuzul unei legături peste teren fără suport.

La T18, noua mască și regularizarea reduc ieșirea greșită de pe muchia vestică superioară; aripa vestică inferioară rămâne reprezentată. Corpul brun adiacent din vest nu este adăugat automat la T18:C1. Identitatea sa și delimitarea anexelor rămân de verificat, nu de dedus exclusiv din schimbarea culorii.

## Verificări și limite

Au trecut 43 de teste din modulele fusion_refinement, cadastral_roof_workflow, fusion_guidance, roof_simple_geometry, roof_body_partition și roof_body_recovery_partition. Rularea reală a inclus exact T17:C1, T17:C2 și T18:C1, cu preflight valid pentru toate trei înainte de inițializarea modelului. Runner-ul `tools/run_cadastral_roof_review.py` impune acum validate_selection/require_ready și permite verificarea separată prin --preflight-only. Manifestul nou consemnează imaginile efectiv inspectate și hash-urile acestora. Manifestele istorice incomplete nu sunt exceptate tacit.

| Corp | Arie ipoteză, m² | Noduri totale | Curți | Stare |
|---|---:|---:|---:|---|
| T17:C1 | 1778,13 | 14, inclusiv inelul curții | 1 | REQUIRES_REVIEW |
| T17:C2 | 1620,11 | 14 | 0 | PENDING_OWNER_REVIEW |
| T18:C1 | 1248,75 | 14 | 0 | REQUIRES_REVIEW |

Toate geometriile sunt valide; intersecția T17:C1/C2 este 0 m². Distanța minimă dintre ele este aproximativ 0,109 m, o proprietate geometrică, nu o afirmație de precizie cadastrală. T17:C1 și T18:C1 păstrează avertizarea conservatoare POSSIBLE_SEARCH_WINDOW_TRUNCATION, declanșată de apropierea măștii brute de fereastra de căutare. T18 are și LOW_OPTICAL_SCORE (aproximativ 0,597). Aceste avertizări nu sunt ascunse pentru a declara reușită. Nu s-a executat o evaluare regională completă, iar LiDAR CRS și compatibilitatea temporală rămân limite cunoscute.

## Dovezi și integrare QGIS

`verification.json` consemnează verificările. Preflight-ul folosit avea modificări preexistente ale altui agent; acestea rămân în fișierul său de lucru, fără a fi comise direct de această etapă. `preexisting_preflight_dependency.patch` și hash-ul sursei păstrează explicit dependența rulării pentru reproducere pe checkpoint-ul de bază.

Director: `workspace/reviews/lot3_finishing_20261017/`.

- `workflow_inputs.json`, `results/inputs.json`, `results/preflight.json`: selecție, proveniență și condiții de intrare.
- `results/cadastral_review.gpkg`, `results/report.json`, cele trei crop-uri GeoTIFF: rezultate reale, măști brute și diagnostice.
- `missed_patch_diagnostics.json`, `geometry_checks.json`: cauza omisiunii și verificările geometrice.
- `T17_before_after.png`, `T18_before_after.png`: portocaliu = versiunea anterioară; cian = versiunea curentă.
- `T17_shared_qgis.png`, `T18_shared_qgis.png`: randări native QGIS cu rezultatele curente și ortofotoul comun.
- `live_shared_canvas.png`: captura pânzei sesiunii QGIS active după integrare.
- `shared_qgis_before.json`, `shared_qgis_after.json`, `previous_display_filters.json`, `integration_code.py`, `integration_response.json`: operațiile de integrare și starea sesiunii PID 13436.
- `shared_project_before_integration.qgs.backup`: copia de siguranță a proiectului de pe disc înainte de integrare; nu este un proiect nou de lucru.

Grup activ în proiectul comun: `LOT3_FINISARE_T17_T18_20261017`, trei straturi cian, câte un corp fiecare. Măștile brute sunt disponibile separat, debifate. În straturile istorice Lot3 cu atribut test_id, T17/T18 sunt excluse numai din afișare pentru a evita contururile vechi suprapuse. Geometriile istorice nu sunt șterse. Celelalte cazuri și loturile acceptate își păstrează straturile. Proiectul avea modificări nesalvate înainte de integrare; salvarea a păstrat starea existentă a sesiunii împreună cu grupul nou.

## Continuare

Solicitați verdictul vizual exact pentru aceste imagini înainte de a modifica accepted/owner_status. T17/C1/C2 și T18/C1 sunt încă neacceptate; celelalte cazuri Lot3, inclusiv T20, nu primesc un verdict nou prin această etapă. Verificați în special muchiile și identitatea anexelor T18 și avertizările de fereastră. Codul, datele, imaginile, backup-ul și handoff-ul acestei etape se versionează împreună. WAL/SHM și cache-urile Python sunt temporare și sunt excluse. Modificările paralele și artefactele istorice neauditate din repository nu sunt absorbite în acest checkpoint.
