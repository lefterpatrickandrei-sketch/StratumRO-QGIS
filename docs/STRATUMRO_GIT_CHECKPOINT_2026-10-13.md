# Checkpoint Git StratumRO — 2026-10-13

Proprietarul a cerut explicit salvarea progresului în Git. Acest document, codul, testele și dovezile selectate fac parte din checkpointul local. Identificați commitul cu `git log -1 --oneline`; nu presupuneți că acesta a fost publicat pe GitHub.

## Verdictul uman curent

Proprietarul a identificat explicit planșa `six_before_after.png`, în ordinea ei stânga-dreapta, sus-jos:

| Poziție | Caz | Verdict |
|---|---|---|
| 1 | T05, două corpuri | ACCEPTAT |
| 2 | T06 | ACCEPTAT |
| 3 | T07 | ACCEPTAT |
| 4 | T08 | RESPINS |
| 5 | T09 | RESPINS |
| 6 | T10 | PARȚIAL EXECUTAT, NEACCEPTAT CA REZULTAT FINAL |

Primul lot rămâne8/8 acceptat; T01–T04 din lotul suplimentar rămân acceptate. Acestea sunt verdicte vizuale asupra unor scene de dezvoltare, nu precizie cadastrală sau generalizare. T08/T09 nu au primit contur nou susținut; mica structură la marginea T08 rămâne nerecuperată. Niciun procent de clădiri corecte nu se deduce din aceste scene care pot conține mai multe corpuri.

Sursa autoritativă a verdictelor: `workspace/reviews/retry_six_release_20261013/owner_feedback.json`. Atributele PENDING ale GPKG-ului reflectă momentul inferenței și sunt suprascrise semantic de acest feedback separat, fără rescrierea geometriilor/dovezilor istorice. Nu relansați automat modificări pe cazurile acceptate.

## De ce conturul mov arată ciudat

Movul este **masca veche respinsă**, păstrată pentru comparație. Conturarea celulelor raster produce trepte; unele măști au unit corpuri, teren și vegetație. În încercarea anterioară de reluare se moștenea și un punct SAM din afara copilului, ceea ce putea respinge segmentarea și readuce masca LiDAR nesimplificată. Movul nu este referința GMW și nu este rezultatul nou livrat ca bun. Verde/cyan arată ipotezele rectificate; T10 rămâne doar parțial acceptat.

## Ce se salvează

- Implementarea relevantă de evaluare, integritatea punctelor SAM2, evidența LiDAR, separarea corpurilor, simplificarea geometrică, reluarea cu puncte proprii și integrarea opțională în pipeline.
- Testele de regresie și runner-ele diagnostice reproductibile.
- Documentația și intrarea de continuare în `AGENTS.md`. Regula `.gitignore` a fost limitată la rădăcină (`/STRATUMRO_*.md`), pentru ca rapoartele din `docs/` să poată fi versionate.
- GPKG-urile compacte de inspecție necesare proiectului, proiectul QGIS și imaginile finale selectate, feedbackul uman, corespondența T01–T10, manifestele și logul testelor.
- Starea simplificării din `geometric_reconstruction_v2.py` exista deja modificată în checkout înaintea acestui checkpoint. Este păstrată ca parte a stării de cod testate; nu este atribuită drept schimbare nouă a acestei operații de salvare.

Nu sunt incluse în checkpoint livrabilele active mari `workspace/output/cladiri_stereo70.gpkg` și `workspace/output/cadastru_ancpi.dxf`, ștergerea vechiului raport din rădăcină sau alte lucrări fără legătură. Aceste modificări rămân în working tree. Nu au fost resetate, șterse sau suprascrise. Ortofotourile/LiDAR și modelele mari sunt dependențe locale, nu sunt incluse în commit.

## Verificare și continuare

În manifestul critic exista deja o nepotrivire pentru `volumetric_3d.py`. Fișierul de cod a fost verificat byte-cu-byte ca identic cu HEAD; s-a corectat doar metadatumul SHA256 în manifest, cu vechea valoare și motivul păstrate. Nu s-a modificat implementarea3D.

Ultima suită completă executată pe această implementare: **373 descoperite,364 trecute,9 omise,0 eșecuri,44.447s,exit0**. Logul și manifestul sunt în `workspace/reviews/retry_six_release_20261013/`. Operația curentă de salvare schimbă documentație/feedback și regula Git, fără modificare nouă de algoritm.

Deschideți `workspace/reviews/retry_six_release_20261013/inspectie_completa_8_orto_loturi.qgs`: toate8 ortofotourile disponibile și etichete Lot1/T01–T10. Acoperirea completă a fundalului nu înseamnă inferență nouă completă pe AOI; aceasta nu a fost executată în modul final. Pentru cod și reluare, citiți `docs/STRATUMRO_SIX_RETRY_HANDOFF_2026-10-13.md`.

Următorul agent trebuie să păstreze T05/T06/T07, să corecteze partea încă greșită a T10 și să investigheze separat recuperarea construcției mici la T08/falsul candidat T09. Nu numiți aceste trei situații finalizate și nu transformați retragerea presupusă de streașină în amprentă la sol măsurată.
