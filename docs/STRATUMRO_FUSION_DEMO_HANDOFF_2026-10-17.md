# Fuziune ghidată și rectificare — proiect separat, 2026-10-17

## Livrare și statut

Proiect: `workspace/reviews/fusion_complete_20261017/StratumRO_fuziune_inspectie_separata.qgz`.
Rezultate: `fusion_complete.gpkg`, layer `IPOTEZE_RECTIFICATE`, patru obiecte:

| Corp | Rută | Noduri totale | Statut |
|---|---|---:|---|
| T17:C1 | LiDAR + ortofoto, corp roșu cu curte | 14 (exterior + curte) | PENDING_OWNER_REVIEW |
| T17:C2 | LiDAR + ortofoto, corp gri separat | 10 | PENDING_OWNER_REVIEW |
| T18:C1 | LiDAR + ortofoto | 10 | PENDING_OWNER_REVIEW |
| T20:C1 | recuperare optică, fără veto de înălțime | 8 | PENDING_OWNER_REVIEW |

Contururile cyan sunt ipoteze rectificate; mov reprezintă măștile inițiale, într-un grup debifat. Nici culoarea, nici eticheta RECTIFIED nu sunt acceptarea proprietarului. Există bookmark-uri de proiect T17/T18/T20. Proiectul principal nu a fost schimbat sau salvat.

## Ce este implementat

- `stratum_ro/fusion_guidance.py`: folosește componenta locală Clasa 6 + înălțime din apropierea unui candidat optic. Dacă suportul lipsește sau este incompatibil, păstrează ancora RGB și semnalează revizia; nu fabrică puncte negative din lipsa LiDAR.
- `stratum_ro/fusion_refinement.py`: verifică suprafața după segmentare, exclude vegetația/terenul cu suport local, recuperează pixelii omiși din aceeași componentă într-o margine limitată la 1,5 m, apoi aplică simplificarea existentă. Păstrează curțile mari. Ruta RGB nu moștenește veto-ul LiDAR. Rezultatul nesusținut rămâne explicit nerezolvat.
- Repararea golurilor diferă între ruta LiDAR rasterizată la 1 m și ruta RGB; parametrii sunt euristici de dezvoltare și nu toleranțe cadastrale validate.
- Se folosește motorul SAM2 existent și `roof_simple_geometry`; nu sunt inventate înălțimi pentru a trece validarea veche. Predictorul este folosit explicit în acest experiment, cu stări noi de revizie.

## Executat și păstrat în Git

1. `tools/run_fusion_guidance_demo.py`: manifestul Lot3 v3 a trecut preflight, apoi comparație SAM2 pe aceleași T17/T18/T20, cu encoding comun pe imagine. Output inițial imuabil: `workspace/reviews/fusion_demo_20261017/`. Commit checkpoint `02bbde4`.
2. `tools/refine_fusion_demo.py --output-dir <director nou>`: rafinare fără rerulare SAM2. Încercările `fusion_rectified_20261017`, `fusion_rectified_v2_20261017`, `fusion_rectified_v3_20261017`, `fusion_rectified_v4_20261017` sunt păstrate. V2 a demonstrat extinderea greșită în vecinul conectat; versiunea actuală limitează extinderea și are test de regresie.
3. `tools/complete_fusion_demo.py`: extrage separat corpul gri T17 din sursa native-cache la 15 cm, pe o fereastră extinsă, inspectată vizual, cu ancoră RGB explicită. Salvează proveniența și unește în pachet cele patru ipoteze, fără union geometric între corpuri.
4. `tools/open_fusion_demo_qgis.py`: construiește doar proiectul separat și randările QGIS, fără pluginuri active. Profilul de lucru al acestei instanțe este în afara repo-ului; nu este parte din cod/produs.

12 teste noi au trecut; împreună cu testele existente relevante, 30 teste au trecut:

```powershell
venv/Scripts/python.exe -m unittest stratum_ro.test.test_fusion_guidance stratum_ro.test.test_fusion_refinement stratum_ro.test.test_roof_simple_geometry stratum_ro.test.test_roof_body_partition stratum_ro.test.test_roof_body_recovery_partition
```

Toate cele patru geometrii sunt valide. Suprapunere T17:C1 cu T17:C2: 0 m²; distanță minimă aproximativ 0,484 m. Acestea sunt verificări geometrice, nu dovada preciziei poziționale. Au fost inspectate imaginile înainte/după și randările reale QGIS T17/T18/T20.

## Limite și următorul pas

Aceasta este o implementare experimentală în module StratumRO, executată cap-coadă pe candidați selectați: citire/validare → ghidare → SAM2 → rafinare → simplificare → GPKG → QGIS. Nu este conectată implicit la toate intrările pipeline-ului principal și nu este detector RGB autonom pentru regiuni întregi. Ancorele RGB sunt revizuite, nu ieșirea unui detector antrenat; corpul gri T17 are selecție suplimentară documentată.

În continuare: verdict vizual al proprietarului asupra corpurilor și limitelor, apoi remedierea problemelor și integrarea controlată în orchestratorul principal, cu regresii pe loturile acceptate. Nu marcați automat loturile vechi sau aceste patru corpuri drept acceptate. Nu transformați aceste rezultate în etichete curate fără verdict.

T18 este ipoteza corpului principal; recuperarea tuturor anexelor vecine nu este demonstrată. La T20 extensia îngustă din sud poate reprezenta acces/scări, iar suprafața galbenă cu echipamente necesită interpretare vizuală; numărul mic de noduri nu rezolvă singur aceste ambiguități. La T17 curtea este păstrată, dar muchiile și separarea trebuie confirmate de proprietar.

CRS LiDAR rămâne ipoteza Stereo70 susținută vizual, nu validare independentă. Nu s-a măsurat accelerarea end-to-end sau acuratețea; scorurile SAM2 nu sunt acuratețe cadastrală. Nu s-au rulat antrenare sau procesare regională completă. Modificările străine preexistente în roof_retry, evaluation_preflight și proiectele principale nu au fost incluse în acest commit.
