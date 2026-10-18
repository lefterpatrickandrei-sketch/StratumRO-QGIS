# README vizual și integrarea checkpointului comun

## Cerință și autorizare

Proprietarul a cerut ca README-ul să includă grafice, formule explicate, surse și documente și să fie disponibil în `main`. La 2026-10-18 a răspuns explicit **„Da, integrează după verificări”** la întrebarea care preciza că PR #3 include și progresul anterior, nu doar README-ul. Aceasta înlocuiește restricția anterioară „draft PR, fără merge” pentru acest PR, după verificări. Nu autorizează rescrierea istoricului sau publicarea fișierelor altor agenți.

Ulterior proprietarul a precizat: **„dont affect the old readme just move it and put the newer one”**. Versiunea README de la `e6011fa` este păstrată byte-identic în [arhivă](../../junk/2026-10-18/readme_before_visual/README.md). [Manifestul](archive_manifest.json) păstrează originea, hash-ul, motivul și restaurarea. Snapshot-ul inițial, anterior curățeniei, rămâne de asemenea în arhiva existentă.

## Schimbare

README-ul principal prezintă platforma, fluxul experimental, cazuri vizuale reale, datele scanării regionale, formule și trimiteri la implementare. [Metodele detaliate](../../docs/METHODS_AND_SOURCES.md) explică convențiile și limitele măsurătorilor. Documentele active de stare și predare consemnează autorizarea actuală; rapoartele istorice de publicare rămân snapshot-uri neschimbate.

[Generatorul figurilor](build_figures.py) produce trei figuri în SVG și PNG din rapoarte și un exemplu didactic. [Manifestul](figure_manifest.json) leagă graficele de surse prin SHA-256. Capturile originale T10 și regional nu sunt editate. Nu este rulat un nou model și nu sunt schimbate codul produsului, selecțiile, verdictele ori proiectul QGIS.

## Verificare și publicare

Verificarea documentației urmărește legăturile locale, prezența țintelor în Git, integritatea arhivei, hash-urile figurilor și păstrarea celor 16 modificări urmărite preexistente. Randarea efectivă pe GitHub se verifică separat, inclusiv formulele, Mermaid și imaginile. CI trebuie să treacă pentru HEAD-ul exact al PR-ului înainte de merge. [Raportul local](verification.json) este generat de [verificator](verify_publication.py).

PR: [#3](https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS/pull/3). Înainte de merge verifică rezultatele și HEAD-ul live; starea din rapoartele datate nu ține locul acestei verificări. Istoricul PR-ului consemnează integrarea efectivă și SHA-ul de merge.

## Reproducere

Din rădăcina repository-ului, într-un mediu care conține matplotlib:

```text
python workspace/readme_publication_20261018/build_figures.py
python workspace/readme_publication_20261018/verify_publication.py
```

Generatorul figurilor este exclusiv un instrument de documentație, fără inferență, pornire QGIS sau acces la servicii AI. Rularea sa recreează fișierele de figură; hash-urile SVG/PNG pot varia între versiuni matplotlib.
