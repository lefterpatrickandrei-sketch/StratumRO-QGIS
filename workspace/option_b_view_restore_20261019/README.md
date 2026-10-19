# Restabilirea afisarii celor cinci loturi, 2026-10-19

La cererea proprietarului s-a refacut numai afisarea de dinaintea integrarii B_CORECTII_20261019. Nu s-au retras rezultatele noi, nu s-au schimbat geometrii, codul algoritmic, selectorul sau verdictele de acceptare.

Vizibilitatea nodurilor existente a fost restaurata din snapshotul `workspace/reviews/option_b_repair_20261019_v2/project_before_integration.qgs`, folosind ID-urile stabile ale straturilor si caile grupurilor. Grupul B_CORECTII_20261019 ramane incarcat, initial ascuns. Cele cinci loturi sunt din nou vizibile, impreuna cu afisarea B anterioara. Harta a fost incadrata pe ansamblul loturilor.

Au fost verificate vizibilitatea efectiva si numarul de obiecte al straturilor Lot3 (20), Lot4 (10), Lot5 (10), precum si straturile Lot1/Lot2: ACOPERISURI_SIMPLE (7), B5_DOUA_CORPURI (2), TESTE_10_REZULTATE (4), RECTIFICARI_T05_T06_T07_T10 (5). Unele sunt rectificari suprapuse, nu numere de cladiri distincte care trebuie adunate.

Proiect comun salvat: `workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs`, 102 straturi pastrate. `before_visibility_restore.qgs` si `after_visibility_restore.qgs` conserva starea completa inainte/dupa. Snapshoturile au cai relative raportate la directorul proiectului comun si necesita restaurare la acea cale pentru deschidere corecta. `restored_lots.png` este randarea verificata vizual; `restoration.json` consemneaza schimbarile.

Nu ascundeti din nou loturile pentru a prezenta o varianta B. O verificare software trecuta nu compenseaza o regresie vizuala semnalata de proprietar.
