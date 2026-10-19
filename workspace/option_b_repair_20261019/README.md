# B: corectii locale si integrare QGIS, 2026-10-19

Rezultat activ: `workspace/reviews/option_b_repair_20261019_v2/`. Selector comun: `workspace/building_workflow/CURRENT.json`. Toate rezultatele sunt propuneri in revizie. Nu reprezinta livrare cadastrala sau acceptare a proprietarului.

## Ce s-a schimbat efectiv

Nucleul existent `RegionalRoofRefiner.simplify_shapes` ramane singurul motor al acestei etape. In `roof_simple_geometry.py`, schimbarea locala este verificata separat de bugetul global de arie: retragerile de minimum 1 m² si adancime 0,8 m nu pot fi umplute peste 30%. Componentele compacte adaugate/eliminate dincolo de banda de 0,35 m au limita de dezvoltare 0,75 m²; benzile foarte subtiri nu sunt tratate ca retrageri importante numai dupa arie. Unghiurile noi sub 40° sunt respinse cand observatia initiala nu avea asemenea unghiuri. Aceste valori sunt euristici de dezvoltare, nu tolerante cadastrale validate.

Reutilizam `normalize_height_supported_pinholes` pentru goluri de masca mici sustinute de inaltime valida si comparabila cu vecinatatea. Golurile necunoscute nu devin automat curti sau echipamente. RGB/NoData si verificarile comune ale vecinilor raman active. Incluziunea genereaza avertismente parte-intreg, fara unirea sau stergerea corpurilor.

`review_actions.json` contine rutarea explicita a auditului anterior, cu autor, observatie, imagine si SHA-256. Este contributie manuala a agentului la revizie, nu un clasificator invatat sau etichete curate. Nu pretindem ca StratumRO ar descoperi singur aceleasi 64 de cazuri intr-o zona noua.

## Rezultate si verificari

- 216 ID-uri pastrate, 1.026 alternative pastrate; 54 geometrii schimbate fata de B activ anterior.
- 152 propuneri in revizie; 64 in diagnostic: 6 falsuri si 58 incomplete. Aceste 58 nu au fost recuperate prin simplificare.
- 3.664 noduri in observatiile de intrare, 2.765 dupa selectie; rezultatul activ anterior avea 2.798. 106 cazuri simplificate fata de observatie, nu 106 cladiri reparate.
- 0 geometrii invalide; conflicte intre toate cele 216 peste 0,05 m²: 68 la intrarea bruta, 58 dupa selectie. Rezultatul activ anterior avea 60. Conflictele ramase nu sunt rezolvate semantic.
- 511 teste unitare: 502 trecute, 9 omise, 0 esecuri; `tests_final_511.txt`. Avertisment ONNX de model de test si avertisment Shapely consemnate in log. Testele nu masoara corectitudinea cadastrala.
- Audit anterior integral: 216 planse si 1.026 alternative. Reverificare noua: toate cele 54 comparatii modificate in noua planse de contact si cele 13 cazuri tinta cu alternativele complete. Observatiile individuale si hash-urile sunt in `post_repair_visual_review.json`. Cele 162 geometrii neschimbate nu au primit un nou verdict pozitiv.

B035/B049/B055/B096/B115/B129 pastreaza acum retrageri pierdute anterior. B043 are goluri mici curatate si o forma mult mai simpla, dar capatul ascutit ramane de verificat. B039 are inca o decupare exterioara suspecta langa echipament. B108 este neschimbat si ramane suspect; B144/B147 au proeminente ramase; B126 ramane complex. Aceste cazuri nu sunt declarate reparate.

## QGIS comun

Integrat si salvat in `workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs`, grup `B_CORECTII_20261019`: strat cyan 152 propuneri, diagnostic portocaliu 64 si comparatie anterioara mov 216, ultimele doua initial ascunse. Straturile vectoriale istorice sunt ascunse pentru o vedere B fara contururi suprapuse, dar toate cele 99 straturi anterioare raman incarcate; total 102, fara surse invalide. Etichetele arata ID-urile B.

In dosarul rezultatului: `project_before_integration.qgs` si `shared_project_after.qgs`, `qgis_integration.json`, `qgis_main_B049.png`, `qgis_canvas_B049.png`. Snapshoturile sunt versionate. Proiectul comun avea modificari preexistente ale altui agent; copia exacta de dinainte este pastrata. Fisierul comun modificat nu este introdus arbitrar in commit, pentru a nu atribui acele editari acestei sarcini. Snapshotul complet dupa integrare conserva starea reala comuna.

Prima incercare `workspace/reviews/option_b_repair_20261019/` este pastrata ca dovada de dezvoltare, dar nu este activa: verificarea vizuala a aratat prea multe reveniri la contururi zgomotoase. Nu o promovati dupa numele folderului. V2 corecteaza acea supraconservare, cu limitarile consemnate mai sus.

## Reproducere si continuare

`venv/Scripts/python.exe tools/review_simple_roof_variations.py <director-nou> --review-actions workspace/option_b_repair_20261019/review_actions.json`

Selectorul pastreaza intrarea bruta B4 si comparatia anterioara completa de 216, astfel incat rerularea nu simplifica iterativ propriul rezultat si nu pierde cazurile diagnostice. Necesita ortofotourile si nDSM local din configuratie; aceste surse brute nu sunt incluse in noul pachet Git.

Integrare prin bridge-ul QGIS existent: incarcati `tools/show_simple_roof_variations_qgis.py` fara executia blocului `__main__`, apoi apelati `integrate_simple_review(directory, group_name, repair=True)`. Refuza proiectul gresit, modificari nesalvate, straturi editabile sau grup duplicat; nu relansati orbește dupa timeout.

`finalize_checkpoint.py` impacheteaza selectorul, observatiile post-verificare si manifestul final. `manifest.json` ramane dovada codului la generarea geometriei; `checkpoint_manifest.json` leaga ulterior snapshoturile QGIS si corectiile de prezentare HTML. Nu confundati hash-urile celor doua etape.

Urmatoarea problema de fond este recuperarea obiectelor incomplete cu context extins si identitati explicite, apoi clasificarea semantica a falsurilor. Reducerea nodurilor nu poate rezolva singura aceste probleme. Nu porniti antrenarea din predictiile acestei rulari ca si cum ar fi acceptate.

Surse tehnice consultate: [Shapely coverage simplification](https://shapely.readthedocs.io/en/2.1.2/reference/shapely.coverage_simplify.html), [manualul Shapely](https://shapely.readthedocs.io/en/stable/manual.html). Operatiile geometrice nu stabilesc identitatea cladirii sau adevarul cadastral.

Restaurare snapshot QGS: inchideti orice editare activa si restaurati copia aleasa la calea comuna originala, cu backup prealabil; sursele relative sunt raportate la acel director. Snapshoturile nu sunt proiecte portabile autonome.
