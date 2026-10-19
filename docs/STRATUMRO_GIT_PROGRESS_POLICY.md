# Regula proprietarului: întregul progres util în Git

Confirmată la 2026-10-17 pentru repository-ul comun `C:/Users/lefpa/Downloads/QGIS-AI`.

„Salvează în Git” include fiecare fișier și set de date util creat pentru proiect: cod, teste, configurații, texte, documentație, imagini, capturi QGIS, comparații, proiecte QGIS, GeoPackage, GeoTIFF, DXF, rezultate, parametri, manifeste, proveniență și feedback-ul proprietarului.

La fiecare etapă semnificativă:

1. Identifică fișierele create sau modificate în etapa respectivă. Verifică explicit fișierele neversionate și cele ignorate; nu presupune că `git add` include tot.
2. Include artefactele utile și verifică lista exactă a commitului. Nu include modificările altui agent doar pentru a obține un working tree curat.
3. Păstrează dovezile și versiunile anterioare ale rezultatelor relevante. Înregistrează relația dintre ID-ul cazului, surse, cod, parametri, imagini, rezultat și verdict.
4. Exclude secretele, cheile și fișierele strict temporare fără valoare pentru continuare (lock-uri, WAL/SHM, cache regenerabil). O dovadă diagnostică utilă nu devine dispensabilă doar pentru că este generată automat.
5. Pentru fișiere mari, verifică suportul real Git/LFS și stabilește explicit păstrarea lor. Nu activa automat o migrare de istoric sau un upload. Un pointer sau o cale externă nu înseamnă că datele sunt incluse în repository; documentează diferența.
6. Confirmă hash-ul commitului și orice artefact util care încă nu este versionat. Nu afirma „totul salvat” dacă doar codul este în Git.

Commitul local nu reprezintă backup remote. Push-ul rămâne o operație distinctă, conform autorizării existente.

Această regulă se aplică progresului curent și viitor; nu este dovada că toate fișierele istorice neversionate din repository au fost deja auditate sau incluse.

Continuarea cadastrală se face în proiectul QGIS comun. Cererea cea mai recentă a proprietarului de a nu mai crea proiecte separate înlocuiește preferința anterioară pentru izolare vizuală; fișierele și proiectele separate deja create se păstrează ca istoric.


## Actualizare explicită a proprietarului, 2026-10-19

Proprietarul a cerut salvarea paginilor web create și a celorlalte rezultate utile în Git **și GitHub**, cu checkpointuri de progres. Pentru rezultatele B ale etapelor 2026-10-18/19 această cerere înlocuiește politica intermediară „doar cod/documentație pe GitHub, GIS și imagini numai local”. Include HTML, imagini, GIS și istoricul util aprobat; nu doar scriptul generator sau un manifest. Inventarul exact este în `workspace/option_b_consolidation_20261019/publication_inventory.json`.

Publicarea progresului este autorizată în ramura PR-ului draft #4, fără merge implicit în main, fără force push, fără rescriere de istoric. Nu includeți lucrările străine neexaminate, secretele sau automat toate datele brute ale proiectului. Pentru următoarele checkpointuri relevante verificați remote-ul și raportați separat commitul local și publicarea confirmată. Arhivarea continuă în `junk/`, cu lista aprobată, hash și restaurare. B este fluxul activ pentru această consolidare; loturile acceptate și celelalte funcții StratumRO nu sunt eliminate.
