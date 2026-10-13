# Continuare StratumRO — două corpuri la B00005 și încă10 teste vizuale

> Actualizare: proprietarul a acceptat8/8 primul lot și T01–T04 din al doilea, respingând T05–T10. Continuarea autoritativă este [STRATUMRO_SIX_RETRY_HANDOFF_2026-10-13.md](STRATUMRO_SIX_RETRY_HANDOFF_2026-10-13.md). Verdictele PENDING/7din8 de mai jos descriu starea istorică.

## Starea curentă, 2026-10-13

Proprietarul a evaluat lotul anterior de8 imagini: **7 trecute,1 respins**. B00005 este respins pentru unirea a două clădiri și forma conturului. Acesta este verdictul uman pentru lotul anterior, nu o metrică de precizie cadastrală. Feedbackul este salvat în `workspace/reviews/review18_20261013/owner_feedback.json`.

În noua variantă, B00005 este separat în două corpuri simple cu4 colțuri fiecare, fără suprapunere de arie. Identitățile derivate sunt `REF_TIER1_021:B00005:C1` și `:C2`, cu `parent_id` păstrat. Suprafețele sunt aproximativ92.61 și77.03m2. Masca părinte respinsă rămâne în stratul `B5_RESPINS_ANTERIOR`. Verde/cyan disting cele două corpuri; mov arată conturul respins. **Noua separare nu a primit încă verdictul proprietarului; nu transformați7/8 în8/8 automat.** Confirmarea proprietarului că există două clădiri se aplică acestui caz, nu fiecărei schimbări de culoare din AOI.

Au fost selectate înaintea inferenței încă10 obiecte spațial distincte față de cele8 din ultimul lot, din candidații existenți de dezvoltare:4 candidați prioritari din alte regiuni și6 din coada de revizie, în ordine stabilă deID. Arie40..3000m2, suprapunere pe obiectul mai mic<=20%, distanță între centroizi>=5m. Nu s-au ales după rezultatele noii inferențe. Lista exactă este `selection.json`. Acestea NU sunt date independente sau un holdout neatins.

S-a executat inferență SAM2 nouă pe tile-urile native corespunzătoare, cu puncte din propunerile originale și rafinarea punctelor RGB/LiDAR. Nu se citesc poligoane GMW pentru generarea contururilor. Toate10 rezultatele sunt păstrate:

| Test | Sursă | Rezultat algoritmic | Observație vizuală Codex |
|---|---|---|---|
| T01 | REF_TIER1_006:B00015 | Formă simplă4 noduri | Hală roșie plauzibilă, pentru verificare |
| T02 | REF_TIER1_014:B00001 | Formă simplă4 noduri | Acoperiș gri plauzibil; capetele necesită verificare |
| T03 | REF_TIER1_014:B00008 | Formă simplă4 noduri | Marginea de sus/anexa și separarea de suprafața vecină necesită atenție |
| T04 | REF_TIER1_014:B00009 | Formă simplă4 noduri | Clădire lungă roșie plauzibilă, pentru verificare |
| T05 | REF_TIER1_006:B00006 | NEEDS_REVIEW | Clădire complexă; maskă cu multe trepte, fără formă simplă susținută |
| T06 | REF_TIER1_006:B00007 | NEEDS_REVIEW | Acoperiș/corpuri și vegetație unite; contur inutilizabil ca rezultat final |
| T07 | REF_TIER1_006:B00008 | NEEDS_REVIEW | Corpuri complexe și suprafețe adiacente unite |
| T08 | REF_TIER1_006:B00009 | NEEDS_REVIEW | Include teren/vegetație lângă clădire |
| T09 | REF_TIER1_006:B00010 | NEEDS_REVIEW | Vegetație și teren, nu un contur utilizabil de clădire |
| T10 | REF_TIER1_006:B00011 | NEEDS_REVIEW | Acoperiș parțial, contur insuficient |

**4 forme simple și6 revizii nu înseamnă4/10 aprobate de proprietar.** Verdictul pentru toate cele10 este `PENDING`. Verde în planșa nouă înseamnă formă simplă propusă, roșu înseamnă eșec/revizie, mov este conturul anterior. Scorul SAM2 este scor optic, nu aprobare.

## Codul inclus în StratumRO

- `stratum_ro/roof_body_partition.py`: ipoteză de separare printr-o singură linie aliniată cu acoperișul, între regiuni spectrale roșu/non-roșu. Caută praguri R-G20/25/30/35/40, cu R-B>15. Precizie de separare spectrală>=90%, fiecare regiune>=20% din mască și>=20m2. Acest scor măsoară separarea culorilor, nu numărul adevărat de clădiri.
- Fiecare parte este simplificată prin `roof_simple_geometry.py` și decupată la linia comună; nu există suprapunere de arie. Dacă separarea nu este susținută, masca rămâne întreagă în revizie. Iluminarea sau materialele diferite pot exista pe aceeași clădire: `PARTITION_REVIEW_REQUIRED` este obligatoriu.
- `stratum_ro/roof_body_recovery.py`: integrare în modul existent `simple_edges=True`, activat prin `--proposal-policy roof_bodies --simple-roof-edges`. Vectorizează fiecare corp separat, păstrează masca părinte și `raw_id`, `body_index`, `body_count`, `split_status`. Corpurile separate merg în `REVIZUIRE_COMPLEXA` pentru confirmarea identității. Scorul SAM2 moștenit este etichetat `sam2_score_scope=PARENT_MASK`.
- Testul de integrare a identificat o regresie reală: dilatarea culorii putea extinde un copil în corpul vecin. Corecția păstrează geometriile deja decupate la seam și nu mai aplică dilatarea independentă peste vecin.
- `stratum_ro/test/test_roof_body_partition.py`:7 teste sintetice scrise de Antigravity, executate de Codex. Codex a corectat semnul rotației din fixture-ul testului rotit.
- `stratum_ro/test/test_roof_body_recovery_partition.py`:2 teste de integrare pentru părinte păstrat, doi copii fără suprapunere, coadă de revizie și comportamentul implicit fără separare.
- `scripts/extend_roof_visual_review.py`: selecție fixată înainte de inferență, SAM2 nou pe10 obiecte, exportul tuturor rezultatelor, imagini.
- `scripts/render_extended_roof_review.py`: rerandare din rezultatele salvate, fără repetarea inferenței.

## Artefacte autoritative

Director nou: `workspace/reviews/review18_20261013/`.

- `inspectie_18_cazuri.qgs`: proiect QGIS redeschis cu succes,10 straturi. Cele7 contururi din lotul anterior acceptate de proprietar rămân afișate; primul contur respins este înlocuit vizual cu cele2 corpuri separate. Testele noi au verde/roșu conform stării algoritmice.
- `review18.gpkg`: `B5_DOUA_CORPURI`2, `B5_RESPINS_ANTERIOR`1, `CONTURURI_PASTRATE`11, `TESTE_10_REZULTATE`10, `TESTE_10_MASTI_SAM2`10, `TESTE_10_ANTERIOR`10. Sunt straturi cu roluri diferite; nu adunați numerele ca total clădiri independente.
- `B00005_separat.png`; `test10_contact_sheet.png`; `T01.png`..`T10.png`; `qgis_canvas.png`.
- `selection.json`, `test10_results.json`, `owner_feedback.json`, `codex_visual_review.json`, `qgis_readback.json`, `verification_manifest.json`, `unit_tests.log`.

Lotul anterior `simple_roofs_rectified_20261013/` și raportul `STRATUMRO_SIMPLE_ROOFS_HANDOFF_2026-10-13.md` rămân dovezi istorice. Indicația anterioară de a păstra B00005 este **revocată de feedbackul uman nou**.

## Teste și reluare

Suitei complete i s-a executat comanda `venv\Scripts\python.exe -m unittest discover stratum_ro/test`: **355 descoperite,346 trecute,9 omise,0 eșecuri,37.589s,exit0**. Geometriile noi au fost citite înapoi din GPKG și proiectul QGIS a fost redeschis. Numărați prin iterarea `getFeatures()` când QGIS/OGR întoarce `featureCount()=-1` pentru filtreSQL; acesta nu înseamnă că stratul este gol.

Din `C:\Users\lefpa\Downloads\QGIS-AI`:

```powershell
# Inferență nouă; folosiți un director NOU, nu suprascrieți lotul curent.
venv\Scripts\python.exe scripts/extend_roof_visual_review.py --output-dir workspace/reviews/review18_next_run

# Numai randarea dovezilor deja salvate:
venv\Scripts\python.exe scripts/render_extended_roof_review.py --run-dir workspace/reviews/review18_20261013

# Suitele obligatorii:
venv\Scripts\python.exe -m unittest discover stratum_ro/test

# Integrarea completă opțională; NU a fost încă rulată pe toate8 tile-urile:
venv\Scripts\python.exe run_hybrid_full_aoi.py --proposal-policy roof_bodies --simple-roof-edges --output-dir workspace/reviews/full_simple_bodies_next_run
```

## Pașii următori

1. Obțineți verdictul proprietarului pentru noul B00005 și cele10 imagini; păstrați verdictul7/8 pentru lotul anterior.
2. Prioritizați filtrarea/correctarea T06/T08/T09, care includ vegetație/teren, și separarea corpurilor T05/T07/T10. Nu eliminați aceste eșecuri din raport ca să creșteți procentul.
3. Nu transformați automat schimbarea de culoare în două clădiri cadastrale. Confirmați corpuri/identitate prin date adecvate și revizie.
4. Nu prezentați conturul acoperișului ca amprentă la sol măsurată; ipoteza de retragere0.4m din lotul anterior rămâne neverificată.
5. Rulați noul mod pe AOI separat înainte de adoptarea ca implicit. Implicitul rămâne `legacy`; nu există dovadă de generalizare sau validare terestră.

Referințele GMW și fișierele active GPKG/DXF nu au fost suprascrise; hashurile SHA256 au rămas identice. Proiectul QGIS inițial a fost păstrat pe disc; s-a salvat o copie nouă. Nu există commit/push pentru acest lot. Checkout-ul are modificări anterioare; nu le resetați.

Antigravity a livrat cele7 teste în conversația `47d788df-e79b-4b2c-a5cb-8697ca51d280`,SUCCESS,52.20s, fără să revendice executarea lor. Codex a executat testele, a corectat fixture-ul, a implementat separarea/integrat pipeline-ul, a rulat cele10 cazuri reale și a inspectat imaginile. Niciun worker nu mai rulează.
