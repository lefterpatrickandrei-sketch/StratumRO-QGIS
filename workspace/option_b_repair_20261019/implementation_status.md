# Reparația B — etapă în curs, 2026-10-19

Intrare: auditul integral de la 2047ff4. Lucru în repository-ul comun.

Nucleul existent RegionalRoofRefiner.simplify_shapes a fost extins, fără un al doilea motor:
- diferențe locale dincolo de banda de 0,35 m; maximum 0,75 m² per componentă compactă, pentru a bloca retrageri umplute și colțuri tăiate;
- reutilizare normalize_height_supported_pinholes: numai goluri mici cu înălțime pozitivă comparabilă cu vecinătatea, cu diagnostic păstrat; lipsa LiDAR nu umple goluri;
- rutare vizuală explicită cu dovezi SHA-256, fără transformarea observațiilor agentului în verdicte ale proprietarului;
- relații parte–întreg ca avertismente, fără unire sau suprimare pe baza incluziunii;
- strat diagnostic separat, cu toate geometriile/ID-urile păstrate.

review_actions.json este o intrare de revizie pentru aceste cazuri, nu un clasificator învățat și nu etichete curate de antrenare. 6 false obiecte și 58 cazuri incomplete sunt izolate pentru recuperare, nu declarate reparate sau șterse. 13 cazuri cu artefacte de formă sunt vizate de schimbarea comună; comparația efectivă va stabili care s-au îmbunătățit.

Limitele fizice sunt parametri de dezvoltare, nu toleranțe cadastrale. Conservarea formei unei observații nu dovedește identitatea clădirii.

Verificări inițiale: 19 teste de forme/fidelitate trecute. Prima rulare a expus supraconservarea zgomotului; v2 distinge benzi subtiri de schimbari compacte si blocheaza umplerea a peste 30% din retragerile de minimum 1 m² si adancime 0,8 m. V2 este in curs; nu este inca integrata in QGIS. Preexistentele din proiectul QGIS și comparația A/B sunt protejate prin hash și snapshot; nu sunt incluse arbitrar în commitul de cod.

Referințe consultate: https://shapely.readthedocs.io/en/2.1.2/reference/shapely.coverage_simplify.html — simplificarea unei coverage presupune topologie adecvată; nu repară semantic suprapuneri/fragmente. https://shapely.readthedocs.io/en/stable/manual.html?highlight=distance — operații geometrice și simplificare; validitatea topologică nu stabilește corectitudinea acoperișului.


## Incheiere checkpoint

V2 este generata, verificata vizual si integrata in QGIS. Detalii actuale, verificari si cazuri ramase in README.md din acest dosar; etapele de mai sus sunt jurnalul dezvoltarii. Prima rulare nu este activa.
