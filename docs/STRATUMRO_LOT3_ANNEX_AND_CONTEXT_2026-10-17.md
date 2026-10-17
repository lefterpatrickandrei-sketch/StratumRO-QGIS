# Lot3: anexa T18 și sensibilitatea la context

Continuare după `77cebed`, în același proiect QGIS `workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs`. Cerere: „mai continua”. Niciun verdict de acceptare nu a fost dedus din această cerere.

## Rezultat vizibil

Grupul nou `LOT3_T18_ANEXA_IPOTEZA_20261017` conține ipoteza T18:C2, anexa brună din vestul halei: aproximativ 148,05 m², patru colțuri, contur chihlimbar. Conturul actual al halei T18:C1 și cele două corpuri T17 rămân neschimbate, cian. Zona roșie marchează suprapunerea de 5,78177 m² dintre anexă și ipoteza anterioară a halei. Muchia comună nu este rezolvată și nu a fost tăiată artificial pe baza unui contur încă neacceptat. Nu se afirmă identitate cadastrală oficială sau precizie la sol.

`T18_shared_annex_qgis.png` este randarea nativă inspectată; `live_shared_annex.png` este captura pânzei active. `annex_review_final.gpkg` păstrează cele trei ipoteze anterioare, anexa și stratul separat BOUNDARY_CONFLICT. `packaging_final_decision.json` leagă sursele prin hash. Proiectul existent a fost salvat; cele trei straturi anterioare de finisare au fost păstrate. Starea sesiunii era dirty, fără straturi în editare; copia proiectului de pe disc anterior integrării se păstrează ca backup de evidență.

## Ce s-a învățat din experimente

`T18_sensor_evidence.png` juxtapune ortofotoul, înălțimea relativă și Class6. Anexa are suport de acoperiș în ambele surse. Pentru ipoteza extrasă, înălțimea mediană este circa 9,52 m, comparativ cu circa 5,84 m pentru hala extrasă în testul cu context extins. Diferența sprijină investigarea separată; nu dovedește singură două unități cadastrale și depinde de compatibilitatea experimentală a LiDAR-ului.

Ferestrele extinse au fost verificate înainte de inferență. Primele decupaje nu acopereau noul context. S-au creat mozaicuri reale din cele opt cache-uri vecine, cu mască explicită păstrată. O pată NoData reală, 79 pixeli în verificarea ferestrei T18, era în afara țintei, la x aproximativ 390582,075–390582,975 și y 585585,225–585587,025. Extinderea vestică a fost limitată la 2 m, restul la 6 m; ținta inițială și minimum 4 m de context valid rămân incluse. Nu s-au inventat pixeli prin np.clip, umplere sau eliminarea măștii.

Experimentul cu ferestre mai largi a înrăutățit unele rezultate: primul T17:C1 a suprapus aproximativ 1236,48 m² peste T17:C2; o variantă ulterioară a pierdut proiecțiile corpului gri și a inclus acoperișul sudic în corpul roșu. T18:C1 a omis o parte a aripii vestice. Toate aceste rezultate și imagini sunt păstrate; niciunul nu înlocuiește geometria afișată anterior.

Punctul LiDAR ales din maximul interior al întregii componente conectate putea migra de pe anexa verificată spre hala vecină. S-a adăugat o limită de deplasare opțională, `max_prompt_shift_m`, propagată din manifest prin runner și workflow în `fusion_guidance.py`. Pentru anexă se utilizează explicit 3 m; deplasarea efectivă este circa 2,016 m, scorul SAM circa 0,841. Modul limitat a fost verificat și pe corpurile mari și nu a îmbunătățit toate cazurile; implicitul anterior se păstrează (`None`). Deplasările nelimitate peste 3 m sunt semnalate pentru revizie. Scorul nu reprezintă acuratețe.

## Implementare și verificări

- `cadastral_roof_workflow.py`: diagnostic separat pentru distanța măștii brute și a conturului rafinat față de fereastră, acoperirea lor de către fereastră și avertizarea de deplasare a punctului. Distanța zero și includerea geometrică nu demonstrează completitudinea obiectului.
- `fusion_guidance.py`: opțiune explicită de limitare a deplasării; păstrează fallback-ul optic când suportul lipsește.
- `roof_revision_review.py`: comparație reutilizabilă între ipoteze, cu raportarea suprafețelor anterioare omise, schimbării curților, identităților lipsă și suprapunerilor. Pragul de acoperire 97% este un semnal pentru revizie, nu acuratețe și nu obligație de a reproduce un contur anterior greșit. Adoptarea automată nu este permisă de acest raport.
- `run_cadastral_roof_review.py`: citește opțiunea per caz și oferă `--previous-review` pentru raportul de regresie al identităților și topologiei.

Suita relevantă finală: 51 teste, zero eșecuri, 5,128 s. Include regresii pentru componenta LiDAR conectată la vecin, distanțele față de fereastră, omiterea unei aripi, umplerea curții și suprapunerea identităților. Preflight: 4/4 înaintea celor două experimente principale, 3/3 la controlul ferestrelor originale, 1/1 la extragerea finală explicită a anexei.

## Artefacte și reproducere

Directorul `workspace/reviews/lot3_continuation_20261017/` conține:

- manifeste, hash-uri ale celor opt surse, două mozaicuri GeoTIFF și eșecul inițial de preflight;
- `results/`: ferestre extinse, ghidare inițială nelimitată;
- `results_local_prompt/`: ferestre extinse, limită 3 m pentru toate patru corpurile în acel experiment;
- `original_windows_local_prompt/`: ferestre inițiale, limită 3 m, neadoptat;
- `annex_inputs.json` și `annex_final/`: rularea finală reproductibilă a anexei, cu limita explicită per caz;
- GeoPackage-uri, crop-uri, măști brute, rapoarte, verificări, comparații, capturi și codul integrării QGIS.

`experimental_configurations.json` explică configurația efectivă a fiecărei încercări: limita de 3 m a fost încercată temporar ca implicit înainte ca regresiile să determine trecerea la opțiune explicită. Pentru reproducerea experimentelor respective cu codul final, adăugați `max_prompt_shift_m: 3` fiecărui caz într-o copie nouă a manifestului. Nu modificați manifestele istorice ale rulărilor și hash-urile acestora. `annex_inputs.json` are deja configurația explicită corectă. Verificările de comparație ale primei rulări sunt păstrate și ca rezultat istoric, și în directorul rulării.

## Ce rămâne de făcut

Muchia comună T18:C1/C2 necesită verificare pe evidență, fără diferențiere forțată după o referință neacceptată. Ferestrele largi nu constituie o soluție universală pentru T17; este necesară controlarea identităților și a componentelor alipite înainte de adoptarea vreunei variante. T17/T18 și întregul Lot3 rămân în revizie; celelalte cazuri nu primesc un verdict nou. LiDAR-ul rămâne o ipoteză de compatibilitate spațială și temporală, nu un reper independent validat. Codul și întregul pachet util se versionează local în Git; fișierele temporare WAL/SHM sunt excluse, iar modificările paralele ale altor agenți sunt păstrate separat.
