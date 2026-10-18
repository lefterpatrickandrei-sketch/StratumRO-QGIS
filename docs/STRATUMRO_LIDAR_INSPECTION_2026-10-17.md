# Inspecție LiDAR Cluj în proiect QGIS separat — 2026-10-17

## Verdict

Norul conține dovezi utile despre clădiri, dar nu este validat independent pentru precizie cadastrală și nu poate fi impus drept condiție obligatorie pentru fiecare clădire din ortofoto. Există metadate CRS incompatibile cu valorile coordonatelor, clasificare incompletă și o neconcordanță locală importantă la T20.

Proiect separat: `workspace/reviews/lidar_audit_20261017/inspectie_lidar_separata.qgz`. Instanță QGIS cu profil separat, pluginuri oprite. Proiectul principal din procesul 13436 a rămas pe aceeași cale, cu 29 de straturi și starea nesalvată preexistentă `dirty=true`; nu a fost salvat sau modificat de audit.

## Date și metodă

- Sursă: `C:/Users/lefpa/Desktop/date/Z_VladP/Comparatie/LAZ/NorPuncte_St70_S42.laz`.
- 4.624.905 puncte; 660.106 clasificate 6; 1.940.705 clasificate 2.
- Densitate: mediană 5 puncte/celulă ocupată de 1 m²; media 5,207. Nu este densitate uniformă garantată pe orice acoperiș. Celulele fără puncte sunt excluse din această medie.
- Header-ul declară EPSG:4284 (Pulkovo 1942, coordonate geografice), dar X=390478,540–391522,106 și Y=584981,226–585877,657 sunt coordonate cu valori de grilă metrică.
- DTM-ul de 3 m are un CRS local cu textul `STEREO70 / S-42_ROMANIA`, fără identificator EPSG complet recunoscut.
- Pentru inspecție, valorile X/Y au fost interpretate ca ipoteză EPSG:3844, fără transformare și fără rescrierea sursei. Suprapunerea vizuală cu ortofoto susține această ipoteză, dar nu măsoară eroarea planimetrică și nu stabilește independent datum-ul.
- Data header-ului LAS este 2017-03-09; nu dovedește data achiziției. Data fotografierii și referința verticală nu sunt confirmate.

S-au produs rastere de diagnostic la 1 m: densitatea tuturor punctelor, densitatea Clasei 6, cota maximă și maximul înălțimilor relative față de DTM. Înălțimile relative folosesc eșantionarea nearest a DTM-ului de 3 m; nu reprezintă un model final validat al clădirilor. Clasificarea și poziția sursei nu au fost reparate în acest audit.

## Observații măsurate și vizuale

1. T17 și T18: rasterul Clasei 6 urmărește vizual acoperișuri și aripi importante. Nu apare un decalaj global evident de zeci de metri în imaginile inspectate. Nu s-a calculat RMSE și nu se afirmă precizie centimetrică.
2. T15: 5.803 puncte în fereastra de căutare, zero Clasa 6. T20: 22.811 puncte în fereastra de căutare, zero Clasa 6. Absența Clasei 6 nu înseamnă lipsa norului sau absența clădirii.
3. T20: nici diagnosticul din toate clasele nu reproduce clar acoperișul din ortofoto. Trei cercuri cu raza de 3 m, alese vizual pe zona acoperișului, dau următoarele diferențe Z–DTM:

| Centru X,Y, ipoteză EPSG:3844 | Puncte | Mediană Z–DTM | Percentila 95 | Clase prezente |
|---|---:|---:|---:|---|
| 390967,5; 585237,5 | 202 | 0,018 m | 0,179 m | 2,3 |
| 390967,5; 585253,25 | 210 | 0,047 m | 0,723 m | 2,3,4 |
| 390967,5; 585221,75 | 156 | 0,210 m | 0,539 m | 2,3,4 |

Aceste eșantioane sunt diagnostic manual local, nu etichete de antrenare sau contururi de referință. Posibile explicații: diferență temporală, schimbare a construcției, problemă locală de date/DTM/aliniere. Cauza nu este demonstrată; nu afirmați că simpla reclasificare rezolvă T20.

4. Pentru 1.940.705 puncte Clasa 2, Z–DTM are mediană +0,029 m, mediană absolută 0,096 m, percentile 5/95 de −0,263/+0,709 m. Este coerență internă între produse posibil dependente, nu validare verticală externă.
5. Clasa 5 include cote până la 542,018 m. Valorile extreme trebuie verificate local înainte de folosirea maximelor drept înălțime de clădire; nu s-a demonstrat că toate sunt erori.

## Consecințe pentru StratumRO

- Mai întâi clarificați CRS și epocile surselor; nu transformați norul plecând automat de la EPSG:4284.
- Introduceți verificări explicite pentru compatibilitatea CRS/unităților și proveniență. Codul actual `stratum_ro/lidar_processor.py` folosește coordonatele numerice și declară ieșirea EPSG:3844; aceasta nu dovedește validitatea intrării.
- Folosiți suportul LiDAR local cu o stare de calitate/acoperire. Lipsa Clasei 6 sau a unei elevații compatibile trebuie să ducă la revizie/sursă alternativă, fără respingerea automată a clădirii vizibile.
- Pentru T20 verificați data norului și a ortofotoului, apoi secțiuni și puncte originale. Nu antrenați modelul să considere acea clădire fundal pe baza acestei neconcordanțe.
- Continuați corectarea NoData/cusăturilor separat de această problemă. Mai mulți pixeli RGB nu rezolvă nepotrivirea temporală a senzorilor.

## Dovezi și reproducere

În `workspace/reviews/lidar_audit_20261017/`: `audit_lidar.py`, `lidar_metadata_audit.json`, `open_inspection_qgis.py`, `separate_qgis_state.json`, proiectul QGIS și imaginile `overview_class6.png`, `T17_class6.png`, `T18_class6.png`, `T20_class6.png`, `T20_height.png`. Galben–roșu în imaginile `class6` înseamnă număr de puncte Clasa 6 pe celulă, nu verdict sau contur cadastral. Imaginile `height` arată o scară diferită: înălțime relativă diagnostică.

Nu au fost rulate SAM, antrenare, corecții de geometrie sau inferență de producție. Auditul nu schimbă acceptările proprietarului și nu repară pipeline-ul prin simpla documentare.
