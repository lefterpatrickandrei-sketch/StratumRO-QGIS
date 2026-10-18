# Documentația StratumRO

Intrările curente sunt întreținute împreună; rapoartele datate rămân dovezi pentru etapa lor, nu promisiuni despre produsul de astăzi.

| Document | Rol |
|---|---|
| [README principal](../README.md) | Identitatea produsului și punctele de intrare |
| [AGENTS.md](../AGENTS.md) | Reguli comune, fără roluri exclusive impuse unui furnizor |
| [PROJECT_STATE.md](PROJECT_STATE.md) | Stare verificată, selecții active, limite și lucrări rămase |
| [SYSTEM_MAP.md](SYSTEM_MAP.md) | Diagrame ale implementării și ale direcției propuse |
| [METHODS_AND_SOURCES.md](METHODS_AND_SOURCES.md) | Formule explicate, convenții raster/geometrie și legături la cod și surse oficiale |
| [REPOSITORY_GUIDE.md](REPOSITORY_GUIDE.md) | Structură, responsabilități, Git și arhivare |
| [AGENT_HANDOFF.md](AGENT_HANDOFF.md) | Cum preia și predă un agent o sarcină |

## Reguli și dovezi specializate

- [Protocolul comun de decizie pentru clădiri](STRATUMRO_AGENT_DECISION_PROTOCOL.md).
- [Porți de evaluare înainte de inferență](STRATUMRO_EVALUATION_GATES.md).
- [Tot progresul util în Git](STRATUMRO_GIT_PROGRESS_POLICY.md).
- [Automatizarea regională și rolul opțional Hugging Face](STRATUMRO_REGIONAL_AUTOMATION_AND_HF_2026-10-17.md).
- [Predarea reparațiilor Lot3](STRATUMRO_LOT3_REPAIRS_HANDOFF_2026-10-17.md).
- [Lot4 și reverificarea vizuală Lot3](STRATUMRO_LOT4_AND_LOT3_VISUAL_RECHECK_2026-10-17.md).
- [Identitatea produsului și direcția desktop](STRATUMRO_PRODUCT_IDENTITY_AND_DESKTOP_DIRECTION_2026-10-17.md).
- [Auditul și aprobările reorganizării din 2026-10-18](../workspace/repository_cleanup_20261018/README.md).
- [Repararea CI și proveniența referințelor, 2026-10-18](../workspace/ci_repair_20261018/README.md).
- [README vizual, arhiva versiunii anterioare și autorizarea integrării](../workspace/readme_publication_20261018/README.md).
- [Arhiva și restaurarea](../junk/README.md).

## Documentație istorică și de arhitectură

Fișierele `RAPORT_*.md`, `MASTER_AUDIT_*.md`, `PROJECT_PROGRESS.md` și celelalte rapoarte datate descriu etape anterioare. Unele folosesc afirmații de performanță sau certificare care nu sunt susținute de verificarea curentă; nu le propaga ca stare prezentă.

Directorul `architecture/` conține și materiale locale neversionate ale altor agenți. Nu presupune că un document marcat PASS descrie implementarea actuală sau că este deja publicat. Verifică fișierul, importurile, testul și dovada invocate. Documentul curent de navigare arhitecturală este [SYSTEM_MAP.md](SYSTEM_MAP.md); consolidarea celorlalte materiale necesită inventar și ownership, nu ștergere în masă.
