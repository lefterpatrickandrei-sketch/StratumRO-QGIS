# Lot3: muchii observate în sursa nativă și verificare vizuală completă

Continuare autorizată după `6f66b0f`: corectarea muchiei T18, verificarea T17 și examinarea întregului Lot3 în proiectul QGIS comun. Niciun caz nu primește acceptarea proprietarului prin această etapă.

## T18: corecția suprapunerii

S-au citit cele opt SID-uri originale cu GDAL din QGIS, într-un VRT de referință, fără modificarea surselor. Decupajul muchiei are 2403 × 2403 pixeli, pas 0,011651 m/pixel; detaliul pentru întregul T18 este resamplat la 0,05 m/pixel. Acesta este pasul rasterului, nu o precizie pozițională demonstrată. `native_sources.json` consemnează sursele, dimensiunile și transformările.

Pe imagine se vede o fâșie întunecată între acoperișul brun și hala roșie. `fit_roof_gap` extrage profile transversale ale luminozității și estimează separat cele două margini ale golului, numai dacă există contrast bilateral și suport stabil. Lățimea mediană observată în profile este circa 1,11 m. Pentru marginea completă a halei, `fit_red_roof_edge` estimează tranziția cromatică a acoperișului roșu pe întreaga latură, independent de poligonul anexei: 47/51 profile susțin fitul. Marginea anexei utilizează partea sa observată a fâșiei: 35/41 profile. Reziduurile mediane față de dreptele ajustate sunt aproximativ 0,026 m, respectiv 0,030 m; sunt reziduuri ale modelului optic, nu acuratețe cadastrală și nu eroare absolută.

`replace_observed_edge` intersectează dreapta observată cu cele două laturi vecine ale aceluiași poligon. Păstrează celelalte colțuri și curțile; refuză deplasări de colț peste 3,5 m, schimbări de arie peste 15%, vecini paraleli sau geometrie invalidă. Nu efectuează difference/intersection cu poligonul vecin ca metodă de construcție. Intersecția dintre corpuri este calculată numai ulterior, ca verificare. Nu sunt coordonate T18 sau ID-uri de caz în modulul generic `stratum_ro/roof_gap_edges.py`; selecția laturilor de diagnostic este explicită în scripturile de caz.

| Ipoteză | Arie anterioară, m² | Arie nouă, m² | Colțuri exterioare |
|---|---:|---:|---:|
| T18:C1 | 1248,75 | 1210,95 | 14 |
| T18:C2 | 148,05 | 150,02 | 4 |

Suprapunerea scade de la 5,78177 m² la 0. Distanța minimă dintre noile poligoane este aproximativ 1,223 m, o proprietate a ipotezelor geometrice. Ambele sunt valide și rămân `PENDING_OWNER_REVIEW`. Suportul LiDAR deja investigat arată acoperișuri ridicate cu înălțimi diferite; alinierea și compatibilitatea temporală nu sunt certificate. Poziția muchiei este decisă din ortofotoul nativ. Nu se pretinde o limită cadastrală la sol.

Această corecție privește muchia investigată, nu toate laturile anexei. Proiecția rotunjită din vestul acoperișului brun nu a fost complet refăcută prin acest dreptunghi; necesită revizie separată. Avertizările istorice SAM/fereastră și celelalte diagnostice se păstrează în pachetele sursă; rezultatul nou nu demonstrează completitudinea întregului obiect.

## T17: verificare fără regresie

Cele două geometrii sunt păstrate identic, inclusiv curtea închisă din T17:C1. Nu sunt adoptate variantele cu ferestre largi, care au degradat forma/identitățile. Randarea nativă QGIS `T17_qgis_checked.png` a fost inspectată. Verificarea vizuală confirmă păstrarea acestei situații, nu soluționarea avertizării de completitudine a măștii brute. Corpul sudic adiacent nu este unit automat cu T17:C1; identitatea sa necesită o decizie explicită dacă intră în domeniul țintei.

## Audit vizual al celor zece cazuri

`Lot3_review_page_1.png` acoperă T11–T15, `Lot3_review_page_2.png` T16–T20. Imaginile și constatările din `visual_findings.json` au fost efectiv inspectate. Snapshot-ul `lot3_display_snapshot.gpkg` și cele zece GeoTIFF-uri `audit_crops/` păstrează geometriile și imaginile folosite, inclusiv rezultate vechi încă greșite. Snapshot-ul nu este o nouă validare și nu schimbă proveniența lor.

| Caz | Constatare a agentului, nu verdict al proprietarului |
|---|---|
| T11 | Conturul suplimentar din nord are orientare nepotrivită față de acoperiș; identitate și formă de corectat. |
| T12 | Trei ipoteze plauzibile la scara planșei; relația anexei deschise cu acoperișul gri și corpul estic rămâne de verificat. |
| T13 | Acoperișul mic gri este urmărit plauzibil; colțurile necesită verificare. |
| T14 | Proiecțiile laterale și anexa deschisă nu sunt complet reprezentate; identitățile trebuie verificate înainte de extindere. |
| T15 | Dreptunghiul descrie acoperișul gri; relația cu acoperișul deschis și zona echipamentelor trebuie stabilită. |
| T16 | Acoperișul principal peticit este reprezentat simplu; vecinii nu sunt extensii automate. |
| T17 | Două corpuri separate, curte păstrată; avertizarea de completitudine rămâne deschisă. |
| T18 | Muchia investigată corectată, fără suprapunere; celelalte margini ale anexei nu sunt declarate finalizate. |
| T19 | Niciun contur recuperat, deși clădirea este vizibilă. Urmează recuperare optică pe ținte explicite. |
| T20 | Conturul reprezintă numai o parte a acoperișului superior; acoperișurile vecine/joase cer identități explicite, nu unire oarbă. |

Prioritatea tehnică următoare: T19 și T20 pentru omisiunile mari, apoi conturul suplimentar T11 și anexele T14. Nu se antrenează pe aceste ipoteze ca și cum ar fi etichete curate.

## QGIS, verificări și Git

Proiectul existent rămâne `workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs`. Grupul `LOT3_T18_MUCHII_OBSERVATE_20261017` conține noile două contururi, detaliul din SID la 5 cm și sursa nativă disponibilă pentru inspecție (debifată). Variantele vechi T18 și conflictul lor rămân istoric debifat. T17, celelalte cazuri și loturile acceptate nu sunt editate. Capturile `T18_qgis_current.png`, `T17_qgis_checked.png`, `Lot3_qgis_overview.png` și `live_current.png` provin din aceeași sesiune. Proiectul a fost salvat; niciun strat nu era în editare. Nu a fost creat un proiect de inspecție separat.

Suita relevantă: 56 teste, zero eșecuri, 5,572 s. Cele cinci regresii noi verifică un gol real, lipsa contrastului, masca invalidă, marginea roșie independentă și limitele modificării colțurilor. Nu s-a executat o inferență regională nouă. Detectarea și corecția optică sunt o etapă locală explicită, nu un nou implicit al întregului pipeline.

Directorul etapei este `workspace/reviews/lot3_edge_audit_20261017/`; include TIFF-uri native/5cm/crop-uri, VRT, GeoPackage-uri, diagnosticele de profile, rapoarte, planșe, capturi, backup-ul proiectului și proveniență. Se versionează împreună cu modulul, scripturile și testele. Fișierele WAL/SHM și cache-urile Python sunt temporare. Datele sursă originale existente sunt referențiate, nu duplicate integral. Modificările paralele ale altor agenți nu sunt absorbite în commitul acestei etape.
