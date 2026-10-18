# StratumRO — recuperarea pipeline-ului, 13 octombrie 2026

## Obiectivul confirmat de utilizator

StratumRO trebuie să funcționeze pe date reale: LiDAR și ortofoto → segmentare → geometrii corecte → QGIS → export verificabil. Galeria HTML nu este obiectivul acestei etape. Planul anterior pentru galerie rămâne material de diagnostic, fără prioritate de implementare.

## Corecții implementate

1. **Evaluator: asociere unu-la-unu cu prag real.** `engine/evaluation.py` nu mai numără aceeași predicție la două referințe și nu mai pierde referințele cu candidat sub prag. Maximizează numărul perechilor calificate, apoi IoU, într-o ordine stabilă. TP+FN conservă referințele, iar TP+predicții neasociate conservă predicțiile. Pragul este inclusiv, fără relaxare epsilon; statisticile nu reevaluează greșit pragul pe IoU rotunjit. Cifrele de precizie rămân compatibile cu API-ul existent și sunt marcate explicit drept condiționale unei referințe exhaustive, încă neverificate. Predicțiile neasociate nu sunt declarate artefacte fizice.
2. **GeoPackage: identitate și atribute pentru amprenta la sol.** `CadastralVectorizer.save_multicategory_geopackage` respectă stratul de sol furnizat explicit și nu îl înlocuiește cu o derivare. Când derivă solul din CLEAN/HIBRID, fiecare ID apare o singură dată. Conflictele între geometrii cu același ID sunt refuzate înainte de scriere. Salvările repetate înlocuiesc straturile respective, păstrând straturile fără legătură. Un strat explicit gol golește și versiunea anterioară. Nu este necesar Fiona; se folosesc dependențele disponibile.
3. **Reunire conservatoare a contururilor.** O intersecție de numai 0,05 m² nu mai este suficientă pentru a uni clădiri diferite. Noua politică cere implicit suprapunere de minimum 50% din poligonul mai mic, configurabilă prin `merge_min_overlap_ratio`. Suprapunerile mici se rezolvă ulterior fără a transforma obiectele într-o singură clădire. Testele acoperă fâșii, lanțuri de suprapuneri și măști duplicate. Nu pretindem că această regulă rezolvă toate cazurile de fuziune; efectul pe întregul AOI trebuie evaluat separat.

## Probe de funcționare pe date reale

S-a executat un test delimitat de 90×90 m, fără modificarea livrabilelor active:

- Sursa LiDAR: fișierul real `NorPuncte_St70_S42.laz`; decupajul conține **37.343 puncte**. DTM-ul real al proiectului a fost folosit pentru nDSM.
- nDSM calculat din nou; SAM2 Hiera Tiny încărcat și rulat pe CUDA; ortofotografia existentă este declarată `CACHE_REUSED`.
- Promptul pozitiv este un punct real din clasa LiDAR 6. Geometria referinței nu a fost folosită pentru segmentare. Locația testului este un caz de dezvoltare cunoscut, nu un holdout independent.
- Rezultatul este regularizat și exportat în GeoPackage, DXF TopoLT și CP de diagnostic. GeoPackage-ul păstrează un ID pentru acoperiș și unul pentru sol, cu `NOT_REVIEWED`.
- Evaluarea ulterioară față de referința disponibilă 6: **IoU 0,9363**, **Boundary RMSE 0,556 m**. Aceste valori măsoară un caz diagnostic, nu validare geodezică de teren.
- GeoPackage redeschis: geometrii valide, EPSG:3844, număr corect și atribute de inspecție păstrate. DXF redeschis prin ezdxf: **0 erori de audit structural**, 45 entități.
- Motorul QGIS **3.40.0-Bratislava** a redeschis și verificat cele trei straturi. Verificarea a folosit runtime-ul standalone; interfața QGIS Desktop nu era deschisă, iar bridge-ul live nu a răspuns. Niciun proiect activ nu a fost modificat.
- CP-ul existent scrie Z=0. Este un export planimetric de diagnostic; cotele nu sunt măsurători validate. Tratarea cotelor reale este o sarcină rămasă.

Rezultatele: `workspace/reviews/core_recovery_20261013/real_smoke/`. Manifestul păstrează stările de execuție, hash-uri pentru model/intrări/ieșiri și limitele verificării. Imagine: `real_result_overlay.png`.

## Comparație controlată a reunirii

Pe aceleași **14 intrări reale salvate** dintr-o regiune delimitată, schimbând numai criteriul de reunire:

| Politică | Predicții după procesare | Perechi unu-la-unu cu IoU ≥0,50 |
| --- | ---: | ---: |
| Orice intersecție >0,05 m² | 11 | 2 |
| Suprapunere ≥50% din poligonul mai mic | 18 | 3 |

Numărul de ieșiri poate depăși intrările prin separarea componentelor. Aceasta este o ablație locală, nu o îmbunătățire demonstrată pe toate cele 29 sau pe întregul AOI. Datele au fost reutilizate explicit; SAM2 nu a fost relansat pentru ablație. Comparația inițială pe toate cele 508 de intrări a fost oprită pentru a limita costul de calcul și înlocuită cu acest experiment delimitat.

## Testare și controlul baseline-ului

Au fost adăugate 20 de teste: 9 pentru asociere/evaluare, 7 pentru exportul solului și 4 pentru identitatea clădirilor la suprapuneri. Suitele țintite au trecut. Rezultatul final al întregii suite este păstrat în `workspace/reviews/core_recovery_20261013/suite_final.stderr.txt` și rezumat în `verification_summary.json`.

Testul de înghețare a detectat schimbarea intenționată a celor două module. Manifestul `workspace/baseline/manifest_critical_modules.json` a fost actualizat numai pentru evaluator și vectorizator, cu hash-ul anterior și motivul corecției autorizate. Testul nu a fost dezactivat. Referințele, geometriile golden și constantele benchmark-ului nu au fost ajustate ca să treacă testele.

## Rolul Antigravity

Antigravity a executat două audituri de cod/date, a produs modificarea inițială a evaluatorului și a implementat salvatorul GeoPackage plus șase teste inițiale. Prima sarcină de implementare a atins limita de 8 minute cu o modificare parțială și fără raport; Codex a preluat explicit finalizarea, testele și revizuirea. Sarcina mică următoare a revenit cu raport. Codex a înlăturat dependența Fiona indisponibilă, a întărit comportamentul la conflict/strat gol, a verificat modificările și a implementat protecția reunirii după experimentul controlat.

Pentru următoarele loturi: un singur writer, un defect concret, fișiere permise explicit, timp limitat și raport scurt. Antigravity implementează, Codex revizuiește și rulează verificările locale când permisiunile headless ale workerului împiedică shell-ul. Un timeout nu este acceptat ca sarcină finalizată.

## Lucrul rămas, în ordinea execuției

1. **Rulare completă într-un director nou.** Parametrizarea runnerului pentru căi, AOI, configurație și director de ieșire, înainte de relansare; checkpoint-uri și manifest pentru fiecare etapă. Nu suprascriem livrabilele actuale sau modificările utilizatorului. Recalculăm toate cele 29 cu evaluatorul reparat și toate predicțiile, inclusiv candidații respinși și neasociați.
2. **Vegetație versus clădiri și prompturi.** `LidarProcessor` completează momentan propunerile și din regiuni nDSM elevate; trebuie verificat efectul includerii vegetației deja clasificate și al componentelor foarte mari. Reparația trebuie justificată prin clase reale, măști și cazuri de regresie, nu prin eliminarea automată a tuturor candidaților cu scor mic.
3. **Linia de proveniență și identitatea referințelor.** Verificarea tipurilor de obiect din sursa GIS nativă, în special referința 29, a epocii datelor și a diferenței acoperiș/fundație. Evităm să măsurăm rezultate derivate din referință drept extracție independentă.
4. **Export profesional și editare QGIS.** Recuperare tranzacțională în bridge, stabilitatea FID-urilor, cote Z reale sau câmp explicit necunoscut, păstrarea corecțiilor umane. Acceptarea finală cere dovezi suplimentare față de funcționarea codului.

Starea curentă este: **trei defecte de nucleu reparate și un flux real delimitat demonstrat până la export și citirea în QGIS**. Verificarea completă a întregului AOI și corectitudinea tuturor clădirilor rămân în lucru. Livrabilele vechi nu au fost regenerate și nu devin corecte doar prin modificarea codului.
