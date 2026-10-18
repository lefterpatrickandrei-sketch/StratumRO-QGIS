# Arhivă de proiect — `junk/`

Acest folder păstrează conținut retras din navigarea curentă, la cererea proprietarului. Este versionat în același Git. Conținutul istoric nu dovedește starea actuală și nu reprezintă instrucțiuni active pentru agenți.

## Migrarea din 2026-10-18

- 13 rapoarte mutate din rădăcină în `2026-10-18/root_reports/`.
- Copii exacte ale README, AGENTS, CLAUDE, indexului `docs/README.md` și regulilor Kilo, în `2026-10-18/source_snapshots/`.
- [Lista exactă, cu SHA-256 și căi originale](../workspace/repository_cleanup_20261018/migration_manifest.json).
- [Execuția mutărilor și copia suplimentară a indexului docs](../workspace/repository_cleanup_20261018/migration_applied.json).
- [Aprobarea intrărilor Kilo/Gemini și copia regulilor Kilo](../workspace/repository_cleanup_20261018/agent_entries_approval.json).

Fișierele `AGENTS.original.txt`, `CLAUDE.original.txt` și `kilorules.original.txt` au extensie de arhivă pentru a evita descoperirea lor ca reguli active. `.gitattributes` păstrează octeții originali ai rapoartelor și copiilor, inclusiv terminatorii de linie.

## Restaurare

Verifică hash-ul din manifest și că nu există lucru nou la calea originală. Pentru un raport, mută fișierul arhivat înapoi la `source` și actualizează trimiterile. Pentru un document înlocuit, compară versiunea curentă cu snapshot-ul înainte de a restaura: nu suprascrie automat instrucțiunile noi. Arhivarea este reversibilă prin aceste căi și prin istoricul Git.

Legăturile și afirmațiile din interiorul rapoartelor păstrează contextul istoric. Căile din corpul lor pot indica vechiul amplasament; folosește manifestul pentru rezolvare. Rapoartele cu nume similare din `docs/` nu au fost presupuse copii identice și nu au fost șterse.

Nu depozita aici chei, fișiere `.env`, cache-uri, medii Python, worktree-uri sau date active. Mutarea în acest folder nu reduce istoricul ori dimensiunea obiectelor Git.

Intrarea actuală a proiectului: [README](../README.md), [stare verificată](../docs/PROJECT_STATE.md), [reguli comune](../AGENTS.md).

## README anterior prezentării vizuale

La cererea proprietarului, [README-ul de la e6011fa](2026-10-18/readme_before_visual/README.md) este păstrat integral înaintea înlocuirii versiunii principale. [Manifestul](../workspace/readme_publication_20261018/archive_manifest.json) include hash-ul, originea și restaurarea. Originalele arhivate anterior rămân pe loc.
