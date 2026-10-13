# StratumRO — perfecționare folosind referințele utilizatorului

## Baza de lucru

Utilizatorul a confirmat la 13 octombrie 2026 că `COAJE LUCRU DATE.gmw` este proiectul său și că aceste contururi pot fi utilizate ca referință pentru perfecționare. `tier1_teren.geojson` este tratat drept **USER_PROVIDED_DEVELOPMENT_REFERENCE**. Nu se modifică geometriile și nu se copiază în predicțiile prezentate ca extracție independentă. Clarificarea este înregistrată și în AGENTS.md.

Fișierele de probă sunt în `workspace/reviews/refinement_20261013/`. `reference_manifest.json` leagă cele 29 de ID-uri de fișierul sursă și hash. Referințele 9–13 formează un bloc spațial intern pentru verificare, iar restul un lot de dezvoltare. Toate au fost expuse anterior; acest bloc NU este un holdout independent. Nu s-au căutat parametri pe acel bloc. Cele trei cazuri SAM2 preselectate sunt 6, 14 și 21, toate din lotul de dezvoltare.

## Ipoteza testată

Generatorul LiDAR completează propunerile din regiuni nDSM ≥0,8 m. Regula existentă reintroduce și celule care conțin puncte deja clasificate ca vegetație medie/înaltă (ASPRS 4/5), ceea ce poate conecta clădiri cu arbori. Ipoteză: excluderea acelor celule din completarea suplimentară reduce contaminarea, păstrând suportul de clădire existent.

Antigravity a implementat funcția pură `complete_building_grid`, integrarea sa și teste sintetice. Codex a identificat și restaurat o linie omisă în integrare (`objs_b = find_objects(lbl_b)`), apoi a executat testele și experimentele. La cererea Codex, Antigravity a introdus selecția explicită `completion_policy`, deoarece măsurătorile au demonstrat și regresii.

## Rezultatul pe întregul nor LiDAR real

Aceleași **4.624.905 puncte**, același DTM, rezoluție 1 m și aceleași reguli din celelalte etape. Politicile au fost executate explicit prin API-ul procesorului, fără modificarea livrabilelor active.

| Măsură | Regula existentă | Excluderea experimentală |
| --- | ---: | ---: |
| Celule în propuneri de clădire/anexă | 411.264 | 161.367 |
| Celule cu vegetație 4/5 în propuneri | 298.534 | 52.299 |
| Componente principale | 438 | 523 |
| Componente de anexe | 32 | 57 |
| Acoperirea medie a celor 29 de referințe de către propuneri | 81,64% | 68,71% |

Sunt eliminate 249.897 de celule de 1 m²; nicio celulă nouă nu este adăugată. Aceste valori descriu propuneri și suport raster, nu numărul clădirilor corecte. Mai multe componente pot însemna fragmentare, nu detecție mai bună. Clasificarea arborilor/stâlpilor se schimbă și ea deoarece vechea mască de clădiri le excludea din acele categorii.

Referințele 21 și 22 pierd tot suportul din propuneri. Acesta este un motiv de respingere a activării globale a experimentului, nu de schimbare a referințelor pentru a îmbunătăți cifrele.

## Test SAM2 proaspăt, pe trei decupaje reale

Modelul SAM2 Hiera Tiny a rulat pe CUDA, pe aceleași decupaje de 90×90 m. Ortofotografia existentă este reutilizată explicit. Limita a fost de trei candidați LiDAR cei mai apropiați de centrul fiecărui decupaj, pentru fiecare politică. Centrele de referință localizează cazurile de diagnostic; contururile referință nu sunt introduse în SAM2 ca măști sau casete de prompt. Punctul pozitiv vine din clasa LiDAR 6 când există suport, altfel din componenta LiDAR. Acestea sunt teste de dezvoltare delimitate, nu o evaluare independentă a întregului AOI.

| Referință | IoU existent | IoU experimental | Interpretare în acest test |
| --- | ---: | ---: | --- |
| 6 | 0,9363 | 0,9364 | Aproape neschimbat |
| 14 | 0,3752 | 0,4287 | Îmbunătățire locală; încă sub pragul diagnostic 0,50 |
| 21 | 0,8939 | 0,0000 | Regresie severă; clădirea nu mai este recuperată de candidații testați |

`sam2_crops/sam2_policy_comparison.json` include numărul efectiv de candidați, scoruri, origine prompt și timpul per caz/politică. GeoPackage-urile separate păstrează geometriile. `sam2_comparison.png` arată toate cele trei cazuri cu aceleași ferestre și contururile de referință ale utilizatorului.

Pentru cazul 14 am păstrat și măștile vectorizate înainte de regularizare. IoU crește prin regularizare de la 0,2902 la 0,3752 pentru regula existentă și de la 0,3384 la 0,4287 pentru experiment. Așadar, în acest test regularizarea nu este etapa care strică potrivirea; asocierea/formarea corpului de clădire și segmentarea brută necesită investigare. Imaginea arată că propunerea poate include un corp în formă de T, în timp ce referința utilizatorului delimitează numai corpul longitudinal. Aceasta este o diferență de granularitate de verificat, nu o justificare pentru a modifica automat referința.

## Decizia de integrare

**Regula nouă nu este activată implicit.** `process_multicategory(..., completion_policy='legacy')` păstrează comportamentul existent; `completion_policy='exclude_known_vegetation'` activează explicit experimentul. Politica este returnată în metadatele rezultatului. Astfel, codul de experiment poate fi reprodus fără o regresie silențioasă în pipeline.

Funcția experimentală păstrează celulele de bază ale clădirilor, exclude NaN/Inf și vegetația numai din completarea suplimentară, și aplică pragul de 35 m² în unități fizice la alte rezoluții. Cele nouă teste acoperă atât helper-ul, cât și citirea unui LAS sintetic prin procesor, politica implicită și validarea opțiunilor. Nu s-au adăugat modele sau dependențe.

Suita completă: `venv\Scripts\python -m unittest discover stratum_ro/test`, exit 0; **289 descoperite, 280 trecute, 9 sărite, 0 eșecuri**, 45,994 secunde. Nu s-a modificat niciun baseline pentru a obține acest rezultat.

## Ce învățăm și următorul experiment

1. Eticheta LiDAR de vegetație nu este suficientă pentru a elimina definitiv un candidat optic. Referința 21 este contraexemplul de dezvoltare observat.
2. Cazurile cu conflict între clasă LiDAR și contur optic trebuie păstrate într-o categorie de candidați ambigui pentru verificare optică/structurală; nu trebuie aprobate sau eliminate numai prin etichetă.
3. Pentru referința 14, eliminarea vegetației ajută insuficient. Trebuie urmărite separat promptul pozitiv, separarea corpurilor și efectul regularizării, schimbând câte o singură componentă.
4. Se păstrează rezultatul de bază al fiecărui caz și se acceptă o regulă generală doar după evaluarea omisiunilor și a contaminării pe toate cele 29 și pe date noi.

În timpul citirii rasterelor au apărut avertismente despre definiții CRS GeoTIFF diferite de registrul EPSG. DTM-ul își declară sistemul ca un LOCAL_CS cu text STEREO70 / S-42_ROMANIA și coordonate metrice compatibile numeric cu zona. Nu am demonstrat o deplasare a rasterelor și nu am rescris metadatele; standardizarea provenienței CRS rămâne o verificare separată înaintea afirmațiilor de precizie absolută.

Stare: **experiment implementat și măsurat; activare globală respinsă din cauza regresiei demonstrate**. Rezultatul suitei complete și hash-urile sunt consemnate în `verification_summary.json`. Niciun fișier GMW, contur de referință sau livrabil activ nu a fost suprascris.
