# Consolidare B, arhivare și publicare — 2026-10-19

## Cerința și domeniul

Proprietarul a cerut salvarea site-urilor și tuturor creațiilor utile în Git/GitHub; B rămâne activ, restul încercărilor B intră în junk. A aprobat lista exactă de șase foldere. Datele brute, loturile acceptate și modulele nelegate de B rămân pe loc. Nu s-a acordat merge în main.

## Rezultat

- 878 fișiere, 157,24 MiB în inventarul inițial: pagini HTML, imagini, TIFF-uri de evaluare, GPKG, rapoarte, surse și backupuri QGIS create în etapele B. Toate au fost adăugate efectiv în Git la `6dc2062` și publicate în ramura draft PR #4. `e6c042f` conține inventarul, nu fișierele; comanda inițială cu toate căile a depășit limita Windows, apoi a fost înlocuită cu pathspec-from-file și verificată.
- Nu au fost încărcate toate ortofotourile brute, modele grele, medii Python sau lucrări străine. Manifestul nu înlocuiește fișierele; rezultatele inventariate sunt efectiv în Git.
- Cele șase foldere aprobate, 401 fișiere, mutate în `junk/2026-10-19/option_b_history`. Fiecare SHA-256 verificat după mutare. Sunt păstrate snapshoturile istorice și manifestul de relocare; niciun rezultat nu a fost șters.
- Dependențele active rămân pe loc: `option_b_simple_variations_20261018_v2`, `option_b_refinement_20261018_final`, `run4`, `evaluation`. Nu au fost mutate fără actualizarea provenienței sau intrărilor.
- Un singur selector activ: `workspace/building_workflow/CURRENT.json`. [Fluxul și diagrama](../../docs/BUILDING_WORKFLOW.md).
- `RegionalRoofRefiner.simplify_shapes` conține generarea variantelor, gardurile optice și verificarea vecinilor înainte/după schimbarea tuturor obiectelor. CLI-ul produce doar pregătirea, exportul și planșele după QA. Nu există un al doilea nucleu.
- Replay CPU cu cititorul și imaginile reale: 216 rezultate și 1026 alternative, zero diferențe geometrice față de GPKG vizual livrat. 68 → 60 conflicte; B033/B203 păstrate sub verificarea comună. Nu au fost regenerate inutil imaginile și nu s-a rulat inferență GPU.
- 17 teste țintite trecute. Suita completă este în `full_suite_readable.txt`. Test nou: fiecare formă este sigură separat, dar două forme simplificate se intersectează împreună; batch-ul revine la observații și nu depinde de ordinea intrărilor. Testele nu sunt acceptare cadastrală.
- Paginile sunt salvate în repository cu resurse relative. `workspace/reviews/index.html` este intrarea comună. Servire locală: `venv/Scripts/python.exe -m http.server 8769 --bind 127.0.0.1 --directory workspace/reviews`. Nu s-a activat GitHub Pages; GitHub păstrează codul și resursele.

## Stare și limite

Acoperișuri propuse, toate în revizie; nu am corectat detectările lipsă ori B120 trunchiat doar prin reorganizare. Contractul vechi al uneltei MCP nu a fost schimbat implicit. Datele brute indicate în configurație rămân necesare pentru rerulare. QGIS comun și toate straturile acceptate rămân păstrate. Modificarea QGS preexistentă și comparison GPKG străin nu sunt adoptate în acest checkpoint.

Pentru reluare: citiți AGENTS, selectorul comun și BUILDING_WORKFLOW. Folosiți metoda batch pentru a obține aceleași reguli în CLI și ceilalți agenți. Nu selectați încercări arhivate după data folderului și nu promovați statusul în ACCEPTED fără verdict explicit.
