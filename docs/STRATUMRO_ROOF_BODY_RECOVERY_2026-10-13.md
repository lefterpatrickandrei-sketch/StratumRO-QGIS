# StratumRO — corecții vizuale pentru6,14,21 — 2026-10-13

## Rezultat concret
MEASURED: cele3 acoperișuri urmărite au acum propuneri selectate. 6:IoU.908;14:.913;21:.868, față de principalele anterioare.743/.341/.831. Inspecția vizuală before_after.png și randarea QGIS qgis_case14.png arată corpul gri14 separat și acoperișul21 păstrat. Nu se aprobă automat contururile.

## IMPLEMENTED — corecția
- roof_body_proposals.py: celulele cu suport LiDARclasa6 sunt separate în propuneri neutre/roșii după RGB. Se generează puncte în interior din date, fără referințe. Neutralitate:saturație≤.25; roșu:R−G>25,R−B>15. Aceste indicii generează ipoteze, nu clasifică legal obiecte. Închiderea3x3 umple doar goluri mici de aceeași culoare; conexiune4; minimum20m².
- roof_body_recovery.py: ipotezele de corp sunt segmentate și reconstruite individual; propunerile nDSM se păstrează pentru acoperișuri fără clasa6, precum21. Nu se amestecă înainte de regularizare cu un corp vecin.
- roof_rectangle_core.py: extensiile mici sunt corectate prin profilul de ocupare al măștii, orientat după muchia dominantă. Se păstrează minimumIoU.80 față de conturul original și minimum90% suport în masca optică; altfel se păstrează geometria inițială. Fără coordonate din referință.
- roof_candidate_routing.py: sunt prioritizate contururile regulate cu suport optic și scor suficiente. Vegetația galben-verde dominantă fără suport clasa6 este trimisă separat la verificare. Acest control a eliminat dreptunghiul fals de pe arborii de lângă6, păstrând acoperișul neutru21. Obiectele complexe/neclare nu sunt șterse.
- run_hybrid_full_aoi.py: noua opțiune roof_bodies salvează PROPUNERI_SELECTATE/CORPURI_TOATE/CORPURI_MASTI_OPTICE. Modul este opțional; rezultatele vechi nu sunt înlocuite automat. Atributele de arie, centru, contur la sol și scoruri sunt recalculate după corecție.

## TESTED și domeniul măsurării
326 teste descoperite,317 trecute,9 omise,0 eșecuri,exit0,43.311s. Log:unit_tests_verified.log. CompilareaPython și gitdiff--check au trecut.

SAM2 a fost rulat din nou pe imaginile tile-urilor native și norul complet4.62M puncte, cu3 regiuni de calcul90m declarate anterior. Poziția regiunilor provine din diagnosticul de dezvoltare. Nici conturul, nici centrul referinței nu au fost folosite drept punct de segmentare sau pentru alegerea conturului selectat. Referințele au fost comparate după procesare. Acesta nu este un benchmark independent și nici o nouă rulare completă a tuturor8 tile-urilor cu noua politică.

| Țintă | IoU principal anterior | IoU selectat nou | Propuneri selectate în regiune | Restul păstrate la verificare |
|---|---:|---:|---:|---:|
|6|.743|.908|1|20|
|14|.341|.913|3|27|
|21|.831|.868|8|24|

Asociere1:1:3 potriviri/3 referințe/12 propuneri selectate. Cele9 neasociate pot fi alte clădiri reale din cadre; nu sunt automat erori. Inventarul integral are83 contururi, din care71 sunt în verificarea complexă. Există42 măști optice originale; o mască poate fi separată în mai multe corpuri. Nu sunt83 clădiri unice confirmate.

## Control intern suplimentar9–13
Aceleași praguri, fără căutare de parametri pe acest bloc. Tile-ul este ales după grila geografică a datelor, inclusiv coloana2. Este un control de dezvoltare, nu un holdout independent.

| Referință | IoU maxim selectat | Observație |
|---|---:|---|
|9|.488|Încă incomplet; sub pragul.50|
|10|.610|Propunere prezentă, necesită inspecție|
|11|.791|Propunere prezentă, necesită inspecție|
|12|.630|Propunere prezentă, necesită inspecție|
|13|.000|Ținta nu este recuperată în stratul selectat|

Nu se afirmă că toate clădirile proiectului sunt reparate. Pragurile sunt indicii de lucru; alte culori de acoperiș, umbrele, vegetația fără culoare distinctă și formele complexe pot rămâne în verificare.

## Fișiere pentru inspecție
- before_after.png: toate propunerile selectate din fiecare cadru, nu numai cel mai bun contur.
- inspectie_corectii.qgs: proiectQGIS cu3 tile-uri, referințele galbene și propunerile magenta; se deschide pe14. Stratul REVIZUIRE_COMPLEXA este disponibil, inițial ascuns.
- roof_recovery.gpkg:12 selectate,71 pentru verificare,83 în inventarul integral,42 măști și3 referințe.
- roof_recovery.dxf: export al celor12 propuneri,430 entități,0 erori structurale; randare roof_recovery_dxf.png. Este un export de acoperișuri propuse, nu cadastru aprobat.
- qgis_readback.json: proiectul scris/reîncărcat și cele3 straturi vectoriale citite cu geometrii valide,EPSG3844. qgis_case14.png este randat din proiectulQGIS real.
- verification_manifest.json: parametri,domeniu,rezultate,hashuri și rolulAntigravity.

## Utilizare în pipeline
Din rădăcina proiectului, cuvenvlocal:

```powershell
.\venv\Scripts\python run_hybrid_full_aoi.py --proposal-policy roof_bodies --output-dir workspace\reviews\body_recovery_20261013\full_run
```

Această comandă execută noua politică pe întregulAOI și păstrează ieșirile într-un director separat. Comanda este disponibilă; verificările din prezentul raport acoperă cele3 ținte și controlul9–13. Nu trebuie confundată noua selecție cu aprobarea umană.

Referințele GMW și GeoPackage/DXF active au hashuri neschimbate. Tipurile mixte26–29 confirmate de utilizator rămân documentate separat. Nu s-au schimbat geometriile de referință și nu se raportează o rată de detecție a clădirilor pe toate29.
