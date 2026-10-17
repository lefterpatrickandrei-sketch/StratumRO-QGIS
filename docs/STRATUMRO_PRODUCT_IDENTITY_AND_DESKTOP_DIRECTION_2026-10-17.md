# Identitatea StratumRO și direcția aplicației desktop

Confirmat cu proprietarul la 2026-10-17. Acest document clarifică scopul; nu declară funcționalități neimplementate.

**StratumRO este o platformă geospațială și științifică modulară pentru lucrul geodezului.** Cadastrul este prioritatea actuală și unul dintre domenii. Extracția clădirilor, fuziunea ortofoto–LiDAR și SAM2 sunt componente ale acestui domeniu, nu definiția întregului produs.

Nucleul comun servește geodezia, topografia, geometria, rasterele, norii de puncte, fotogrammetria, GIS și validarea. Domeniile și interfețele se dezvoltă după sarcini și date disponibile; nu se afirmă că toate modulele din arhitectura țintă funcționează deja.

Direcția discutată și acceptată: aplicație desktop proprie pentru Windows, distribuibilă ca executabil/instalator, cu proiecte, catalog de date, conversație pentru formularea sarcinilor, hartă, execuție urmărită, inspectarea rezultatelor și conexiuni cu instrumentele geodezului. Nucleul rămâne separat de interfață. QGIS și alte aplicații sunt conectate prin adaptoare verificate; interfața web poate rămâne un client secundar. Nu există prin această decizie o aplicație .exe nouă deja construită.

Codul existent nu se rescrie pentru a obține o interfață nouă. Se consolidează un flux cadastral real, apoi este expus prin aplicația desktop. Opțiunea Qt/PySide discutată necesită probă de distribuție și verificarea dependențelor; nu reprezintă încă o alegere tehnologică definitivă. QGIS poate rula într-un proces separat cu mediu controlat.

## Prioritatea de implementare curentă

Proprietarul a cerut continuarea părții cadastrale, nu începerea interfeței desktop acum. Integrați componentele executabile, validarea datelor și verificarea livrabilelor. Păstrați proiectele și contururile acceptate. Folosiți proiectul separat pentru ipotezele în curs.

- Ortofoto poate susține propuneri de contur; LiDAR este suport suplimentar, fără veto universal.
- Conturul acoperișului nu este automat amprenta la sol sau limita juridică.
- PENDING_OWNER_REVIEW nu devine ACCEPTED printr-o conversație despre arhitectură.
- Codul nou, testele, configurația, dovezile și instrucțiunile de continuare trebuie salvate explicit în Git. Nu includeți accidental modificările altor agenți și nu faceți push fără autorizare.

Referințe locale: `docs/architecture/STRATUMRO_CURRENT_VS_TARGET_ARCHITECTURE.md`, `docs/STRATUMRO_FUSION_DEMO_HANDOFF_2026-10-17.md`.
