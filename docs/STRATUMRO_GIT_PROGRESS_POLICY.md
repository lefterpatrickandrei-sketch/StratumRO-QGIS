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
