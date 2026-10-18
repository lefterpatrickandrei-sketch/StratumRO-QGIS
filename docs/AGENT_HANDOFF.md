# Preluare și predare comună între agenți

## La preluare

Deschide aceeași copie de repository și citește [AGENTS.md](../AGENTS.md), [PROJECT_STATE.md](PROJECT_STATE.md), [SYSTEM_MAP.md](SYSTEM_MAP.md) și documentul specializat al sarcinii. Confirmă local branch-ul, HEAD și modificările existente; nu te baza doar pe GitHub sau pe o conversație copiată.

Pentru rezultate GIS urmărește fișierul `CURRENT_SELECTION.json` ori `CURRENT_REVIEW.json` indicat în starea proiectului. Verifică sursa, hash-ul și verdictul, nu alege directorul cu nume cel mai optimist. Nu schimba acceptarea unui caz prin actualizarea unui raport de arhitectură.

Înainte de cod nou, caută simbolul, implementările similare, importurile și testele. Notează pe scurt: funcția deja existentă, lipsa observată și locul în care se integrează schimbarea. Dacă există două implementări, stabilește apelanții; nu construi o a treia pentru a ocoli consolidarea.

Un agent poate citi fișierele accesibile din proiect. Nu poate presupune acces la această conversație sau la istoricul privat al altor aplicații. Intrările CLAUDE/GEMINI/Kilo trimit la același contract; descoperirea și respectarea lui trebuie confirmate în fiecare client.

## În timpul lucrului

- Identifică fișierele proprii și evită editarea simultană a acelorași căi cu alt agent.
- Folosește capabilitățile existente QGIS, GDAL și bibliotecile proiectului înainte să reinventezi operația.
- Verifică resursele ocupate înainte de inferență sau teste costisitoare.
- Păstrează intrările, încercările nereușite utile și proveniența. Nu transforma lipsa datelor în dovadă negativă.
- Rulează verificările potrivite schimbării. Pentru documentație verifică legături, căi, hash-uri și diff; pentru cod verifică comportamentul și integrarea. Nu executa o inferență doar pentru o reorganizare de Markdown.
- Fă checkpoint după schimbările semnificative, cu toate artefactele utile proprii și fără secrete.

## La predare

Lasă un document datat în folderul dovezilor sarcinii și actualizează starea/indexul relevant. Predarea trebuie să răspundă la:

| Câmp | Conținut necesar |
|---|---|
| Cerință | Ce a autorizat proprietarul și ce rămâne de decis. |
| Integrare | Componenta existentă extinsă, apelantul și fișierele modificate. |
| Date | Surse, CRS, rezoluție, NoData, versiuni și hash-uri potrivite. |
| Execuție | Comenzi și parametri real executați; distinge model real, simulare și model de test. |
| Verificări | Rezultate exacte, dovezi vizuale dacă sunt relevante și limitele verificării. |
| Statut | Acceptat de proprietar, ipoteză, respins sau nerezolvat, explicit pentru cazurile vizate. |
| Git | Commituri locale, artefacte utile neincluse dacă există, publicare efectivă sau în așteptare. |
| Continuare | Probleme rămase și următorul pas concret, fără a pretinde că un plan este implementare. |

Nu copia întreaga conversație sau raționament intern în MD. Păstrează cerințele, criteriile observabile, deciziile și dovezile utile.

## Punctul de reluare după reorganizarea din 2026-10-18

Prima etapă arhivează 13 rapoarte, păstrează exact vechile intrări și unifică ghidurile. Codul produsului, proiectele QGIS, rezultatele și cele 16 modificări urmărite preexistente sunt protejate. [Dosarul etapei](../workspace/repository_cleanup_20261018/README.md) include inventarul și verificarea finală, când aceasta este încheiată.

Nu adopta automat cele 936 fișiere neversionate inventariate. Materialele arhitecturale locale și datele altor agenți necesită confirmarea provenienței și a stării înainte de consolidare. Proprietarul a aprobat ulterior publicarea progresului local în [draft PR #3](https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS/pull/3), fără merge; [rezultatul](../workspace/repository_cleanup_20261018/publication_result.json) și [inventarul rămas](../workspace/repository_cleanup_20261018/remaining_inventory.json) sunt versionate. Aceasta a fost aprobarea inițială. Proprietarul a autorizat ulterior explicit integrarea PR #3 în main după completarea și verificarea README-ului; [dosarul curent](../workspace/readme_publication_20261018/README.md) păstrează această autorizare. Nu extinde aprobarea la fișierele necomise ale altor agenți sau la modificarea istoricului. Urmează rezultatele CI și decizia asupra intervențiilor de cod, cu impactul prezentat proprietarului.

Continuarea CI a fost autorizată și implementată separat: vezi [dosarul CI](../workspace/ci_repair_20261018/README.md). Commitul `85a51ef` a trecut toate cele patru joburi, cu 459 teste fiecare și hash-urile originale păstrate. Jurnalele complete sunt versionate. Inițial versiunea nouă a fost publicată numai pe branch-ul `chore/stratumro-shared-checkpoint-20261018`. Integrarea este acum autorizată după verificări; verifică starea efectivă a PR #3 și remote main înainte de lucru, fără să tratezi snapshot-ul inițial drept stare live. Agenții locali trebuie să deschidă copia comună și să verifice HEAD, nu un worktree vechi.
