# StratumRO

**StratumRO este o platformă de lucru pentru geodez, care coordonează date, algoritmi și programe specializate precum QGIS.** Direcția produsului este o aplicație în care utilizatorul formulează sarcina, iar sistemul pregătește și execută fluxul, arată rezultatele și livrează fișierele cu proveniență și verificări. Cadastrul este prioritatea curentă; nu limitează scopul întregii platforme.

Reutilizarea instrumentelor QGIS și a bibliotecilor existente este intenționată. Aplicația proprie nu presupune rescrierea lor. Funcționarea automată completă, pentru orice zonă și orice sarcină, rămâne un obiectiv; rezultatele experimentale actuale nu justifică această promisiune.

## Începe de aici

Progresul local și reorganizarea sunt publicate pentru revizie în [draft PR #3](https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS/pull/3), fără merge în `main`. Starea CI se verifică pe PR; documentația nu declară anticipat că verificările au trecut.

| Pentru | Document |
|---|---|
| Ce funcționează, ce este experimental și ce lipsește | [Starea proiectului](docs/PROJECT_STATE.md) |
| Componente existente și arhitectura dorită, distincte | [Diagrame și dovezi în cod](docs/SYSTEM_MAP.md) |
| Structură, Git, arhive și lucru în același proiect | [Ghidul repository-ului](docs/REPOSITORY_GUIDE.md) |
| Continuare de către Codex, Antigravity, Gemini, Kilo sau alt agent | [AGENTS.md](AGENTS.md), apoi [predarea comună](docs/AGENT_HANDOFF.md) |
| Rapoarte și reguli specializate | [Indexul documentației](docs/README.md) |
| Ce s-a mutat și cum se restaurează | [Arhiva `junk/`](junk/README.md) |

## Implementarea existentă

- Plugin și provider de procesare QGIS în `stratum_ro/`, cu instrumente de calcul, vizualizare și export. Metadata pluginului îl marchează experimental.
- Nucleu reutilizabil în `stratum_ro/core/`, contracte în `stratum_ro/contracts/` și componente de domeniu în `stratum_ro/domain/`. Existența acestor directoare nu dovedește că toate fluxurile au fost migrate către ele.
- Serviciu de platformă și API în `stratum_ro/api/`; launcherul `start_platform.py` pornește backendul existent și interfața web. Acesta nu este încă dovada unui instalator desktop final.
- Fluxuri pentru propuneri de acoperișuri din ortofoto, cu SAM2 și suport LiDAR opțional. Scanarea regională demonstrată produce ipoteze și cozi de revizie, nu un inventar validat.
- Generatoare cadastrale și PUG, plus exporturi GIS/CAD. Calitatea și statutul fiecărui livrabil trebuie verificate; un câmp exportat nu dovedește acceptare profesională.

Detaliile și limitările au surse locale în [starea proiectului](docs/PROJECT_STATE.md). Nu prezentăm timpi simulați drept economii măsurate, geometria acoperișului drept amprentă la sol măsurată sau un test trecut drept precizie cadastrală.

## Mediul de lucru existent

Repository-ul comun de pe stația proprietarului este `C:/Users/lefpa/Downloads/QGIS-AI`. Proiectul QGIS comun este [inspectie_corectii.qgs](workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs). Păstrează datele, straturile și verdictele existente; nu crea automat un proiect paralel.

Pe această stație se folosește mediul Python existent. Pentru a porni interfața de platformă, dacă aceasta este sarcina dorită:

```powershell
.\venv\Scripts\python.exe start_platform.py
```

Pentru verificarea relevantă a unei modificări, selectează suita potrivită din `stratum_ro/test/`; verificările QGIS necesită mediul și sesiunea QGIS. Comanda generală utilizată de CI este:

```powershell
.\venv\Scripts\python.exe -m unittest discover stratum_ro/test
```

Curățenia documentației din 2026-10-18 a verificat integritatea fișierelor și trimiterilor; nu a executat din nou această suită, inferență sau servicii externe. Nu este documentată aici o instalare nouă verificată pe o mașină curată. Ortofotourile, norii de puncte, modelele și secretele nu sunt toate incluse într-un clone Git; vezi politica de date din [ghid](docs/REPOSITORY_GUIDE.md).

## Contribuții și continuare

Citește [AGENTS.md](AGENTS.md) înainte de editare. Extinde implementarea existentă și indică precis punctul de integrare. Salvează în commituri delimitate codul, textele, imaginile, datele și dovezile utile ale sarcinii; păstrează modificările celorlalți. Commitul local și publicarea pe GitHub sunt operații diferite.

Licența din rădăcină este [Apache 2.0](LICENSE); unele surse ale pluginului au antete GPL. Situația licențelor componentelor trebuie clarificată înainte de distribuție; acest audit nu a modificat licențele și nu certifică o licență unică pentru întregul produs.
