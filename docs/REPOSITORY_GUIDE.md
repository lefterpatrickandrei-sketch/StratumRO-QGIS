# Ghidul repository-ului comun

## Structura păstrată

| Cale | Responsabilitate actuală | Regula de curățenie |
|---|---|---|
| `stratum_ro/` | Plugin, module produs, API, AI, teste | Păstrează importurile și intrările; consolidarea de cod cere o sarcină distinctă. |
| `stratum_ro/core/`, `contracts/`, `domain/` | Nucleu, contracte și componente de domeniu | Verifică implementarea și apelanții înainte să presupui migrarea completă. |
| `tools/`, `scripts/`, `engine/` | Intrări de lucru, verificări și unelte existente | Nu muta după nume; scripturile pot fi apelate din CI, documentație ori alte programe. |
| `docs/` | Reguli, stare curentă, rapoarte istorice | Pornește din index; separă dovezile datate de regulile active. |
| `workspace/reviews/` | GIS, proiecte QGIS, capturi, manifeste, feedback | Sunt dovezi utile, nu cache implicit. Păstrează selecțiile active și istoricul. |
| `data/`, `datasets/`, `national_server/`, `projects/` | Date și proiecte | Verifică proveniența, licența, dimensiunea și referințele înainte de orice schimbare. |
| `.github/workflows/` | Verificări GitHub | Existența unui workflow nu înseamnă că a trecut pe commitul actual. |
| `junk/` | Arhivă versionată, aprobată | Păstrează hash, motiv, origine și restaurare; fără secrete sau date active. |

`docs/README.md` este indexul curent. Rapoartele arhitecturale din `docs/architecture/` nu au fost mutate în masă: sunt și fișiere neversionate ale altor agenți, iar afirmațiile lor trebuie confruntate cu codul.

## Ce s-a mutat în prima etapă

Toate cele 13 fișiere de mai jos au fost mutate din rădăcină în `junk/2026-10-18/root_reports/`, cu numele păstrat:

| Fișier | Motiv |
|---|---|
| `KILO_CONFIGURATION_AUDIT.md` | Audit de configurație dintr-o etapă anterioară. |
| `LOCAL_DATA_AUDIT_REPORT.md` | Inventar istoric de date; se păstrează citările și dovada. |
| `MASTER_AUDIT_FINAL_VALIDARE.md` | Raport istoric; titlul nu certifică starea actuală. |
| `RAPORT_AUDIT_5_REZOLUTIE.md` | Raport de etapă. |
| `RAPORT_AUDIT_6_REZOLUTIE.md` | Raport de etapă. |
| `RAPORT_AUDIT_7_REZOLUTIE.md` | Raport de etapă. |
| `RAPORT_AUDIT_8_REZOLUTIE.md` | Raport de etapă. |
| `RAPORT_AUDIT_10_REZOLUTIE.md` | Raport de etapă. |
| `RAPORT_AUDIT_11_REZOLUTIE.md` | Raport de etapă. |
| `RAPORT_AUDIT_12_REZOLUTIE.md` | Raport de etapă. |
| `RAPORT_AUDIT_FINAL_CONSOLIDAT.md` | Consolidare istorică, păstrată pentru audit. |
| `RAPORT_FINAL_CERTIFICARE_CADASTRALA.md` | Afirmații istorice de validare, fără transfer de statut asupra rezultatelor actuale. |
| `walkthrough.md` | Parcurs de implementare anterior. |

[Manifestul](../workspace/repository_cleanup_20261018/migration_manifest.json) include căile, hash-urile și mențiunile găsite. Rapoartele omonime din `docs/` nu sunt byte-identice; nu s-au șters ca presupuse duplicate. Originalele intrărilor README/AGENTS/CLAUDE/Kilo și ale indexului docs au copii exacte în arhivă. [Restaurare](../junk/README.md).

## Git local și GitHub

1. Inspectează branch, HEAD, index și fișierele modificate înainte de lucru. La începutul acestei etape existau 16 modificări urmărite ale altor sesiuni și nouă worktree-uri. Nu sunt implicit ale agentului curent.
2. Delimitează căile sarcinii. Adaugă explicit fișierele proprii și verifică diff-ul staged. Evită `git add -A` într-un proiect comun cu lucru concurent.
3. Versionează toate artefactele utile create pentru sarcină, conform [politicii proprietarului](STRATUMRO_GIT_PROGRESS_POLICY.md). Un commit doar cu cod nu este suficient când rezultatul depinde de imagini, GPKG sau parametri neincluși.
4. Pentru o schimbare semnificativă, închide un checkpoint cu dovezi și limite. Commiturile nu trebuie să amestece reparații de algoritm, reorganizare și lucrările altui agent.
5. Verifică separat ce există pe GitHub. În auditul din 2026-10-18, `origin/main` și ramura publică erau la `08524df`, iar local existau 35 commituri în plus înainte de curățenie.
6. Publicarea se decide separat. Un PR pornit din local main ar include și commiturile anterioare. Nu pretinde că GitHub este actualizat printr-un simplu commit local și nu rescrie istoricul pentru a ascunde diferența.

## Date mari, fișiere ignorate și secrete

Inventarul nu certifică faptul că toate datele sunt în Git. `.gitignore` exclude printre altele medii Python, modele mari, LAS/LAZ și anumite rezultate; fiecare artefact util nou trebuie verificat explicit. La audit, LFS era instalat, dar nu avea fișiere urmărite. Nu s-a activat LFS și nu s-a migrat istoricul.

Nu publica `.env`, tokenuri sau configurații locale cu secrete și nu le muta în `junk/`. Inventarul acestei etape a păstrat căi și metadate, fără valori ale secretelor. Arhivarea unor rapoarte nu micșorează cei aproximativ 834 MiB de obiecte Git observați; nu promite curățare de spațiu fără o operație de istoric distinctă.

## Schimbări care necesită o decizie nouă

Mutarea codului cu importuri, ștergerea datelor, eliminarea worktree-urilor, migrarea istoricului/LFS, publicarea, modificarea licențelor, instalarea unor unelte și modificarea fluxurilor de produs nu fac parte din această reorganizare de documentație. Prezintă necesitatea și impactul concret proprietarului înainte de extinderea sarcinii.
