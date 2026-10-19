# Reparația B — etapă în curs, 2026-10-19

Intrare: auditul integral de la 2047ff4. Lucru în repository-ul comun.

Nucleul existent RegionalRoofRefiner.simplify_shapes a fost extins, fără un al doilea motor:
- diferențe locale dincolo de banda de 0,35 m; maximum 0,25 m² per componentă, pentru a bloca retrageri umplute și colțuri tăiate;
- reutilizare normalize_height_supported_pinholes: numai goluri mici cu înălțime pozitivă comparabilă cu vecinătatea, cu diagnostic păstrat; lipsa LiDAR nu umple goluri;
- rutare vizuală explicită cu dovezi SHA-256, fără transformarea observațiilor agentului în verdicte ale proprietarului;
- relații parte–întreg ca avertismente, fără unire sau suprimare pe baza incluziunii;
- strat diagnostic separat, cu toate geometriile/ID-urile păstrate.

review_actions.json este o intrare de revizie pentru aceste cazuri, nu un clasificator învățat și nu etichete curate de antrenare. 6 false obiecte și 58 cazuri incomplete sunt izolate pentru recuperare, nu declarate reparate sau șterse. 13 cazuri cu artefacte de formă sunt vizate de schimbarea comună; comparația efectivă va stabili care s-au îmbunătățit.

Limitele fizice sunt parametri de dezvoltare, nu toleranțe cadastrale. Conservarea formei unei observații nu dovedește identitatea clădirii.

Verificări inițiale: 19 teste de forme/fidelitate trecute. Rularea tuturor celor 216 cazuri este în curs; nu este încă integrată în QGIS. Preexistentele din proiectul QGIS și comparația A/B sunt protejate prin hash și snapshot; nu sunt incluse arbitrar în commitul de cod.

Referințe consultate: https://shapely.readthedocs.io/en/2.1.2/reference/shapely.coverage_simplify.html — simplificarea unei coverage presupune topologie adecvată; nu repară semantic suprapuneri/fragmente. https://shapely.readthedocs.io/en/stable/manual.html?highlight=distance — operații geometrice și simplificare; validitatea topologică nu stabilește corectitudinea acoperișului.
