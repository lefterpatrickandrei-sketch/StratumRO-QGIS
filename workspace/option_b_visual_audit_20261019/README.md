# Audit vizual integral B — 19 octombrie 2026

Au fost inspectate toate cele **216 planșe** din rularea activă `option_b_simple_variations_20261018_v2`: geometria anterioară, selecția și cele **1.026 alternative afișate**. Fiecare caz are o observație proprie în `cases.jsonl`, legată de SHA-256-ul planșei în `audit.json`. Scriptul `build_report.py` doar ambalează observațiile scrise; nu produce verdicte din scoruri și nu editează geometrii.

| Concluzie de inspecție | Cazuri |
|---|---:|
| Eroare vizibilă în rezultatul prezentat | 59 |
| Necesită verificare suplimentară | 134 |
| Plauzibil vizual la scara planșei | 23 |

**B nu este verificat pentru livrare automată.** Aceste numere nu sunt acuratețe, precision sau recall. REVIEW nu este verdict de respingere. PLAUSIBLE nu înseamnă acceptat de proprietar sau validat cadastral. Cele 216 înregistrări includ componente și relații parte–întreg, nu 216 clădiri distincte dovedite.

[Raport complet cu toate imaginile și observațiile](../reviews/option_b_visual_audit_20261019/index.html). Cu serverul de review de pe portul 8769: <http://127.0.0.1:8769/option_b_visual_audit_20261019/index.html>.

## Probleme și ordinea recomandată a corecțiilor

1. **Identitate și completitudine înainte de forme:** B120, B143, B176, B204 sunt fragmente din acoperișuri mai mari. B024/B066 urmăresc arbori, B192 o platformă/alee și B210 un șantier. Rectangularizarea nu rezolvă detecția.
2. **Relații între ipoteze:** B126/B174, B154/B169/B215 și B151/B190 descriu întregul și părți ale lui. Controlul suprapunerilor nu poate stabili singur identitatea de clădire. Nu uni automat corpurile alipite și nu șterge arbitrar componentele.
3. **NoData și ocluzie:** B180–B184, B197 și B213 includ limite determinate de lipsa imaginii. Recitește sursele vecine și extinde fereastra înainte de regularizare; dacă lipsesc date, păstrează explicit starea incompletă.
4. **Goluri și accesorii:** goluri mici de echipament sau zgomot determină COURTYARD la B043/B068/B110/B157. Un inel interior nu dovedește o curte. Nu elimina automat toate golurile: curțile reale trebuie păstrate.
5. **Selecție de forme:** B035/B049/B055/B096/B109 arată retrageri pierdute. Pragurile globale de suprafață și Hausdorff permit pierderea unor detalii locale relevante. Minimul de noduri nu trebuie să câștige dacă înlocuiește retragerea cu teren inclus sau un vârf.
6. **Reevaluare:** după corecția implementării comune, rerulează aceleași cazuri și comparațiile, apoi verifică regional clădirile lipsă. Auditul nu inventariază exhaustiv omisiunile din afara cazurilor furnizate și nu stabilește etichete curate de antrenare.

Ordinea este o propunere rezultată din audit, **nu cod implementat aici**. Nu s-a pornit inferență/antrenare, nu s-a modificat proiectul QGIS, selecția B sau acceptările proprietarului.

## Metodă și limite

Inspecția a folosit planșele originale 1710 × 855; nu înlocuiește măsurători pe sursa nativă sau terenul. Toate geometriile alternativelor afișate au fost privite în contextul cazului, dar observația scrisă este per caz; nu există 1.026 verdicte individuale de acceptare. Unele legende se suprapun în imaginile originale; motivele integrale ale algoritmului rămân în JSON-ul sursă. Nu se certifică toate rulările experimentale istorice din junk.

`build_report.py` verifică 216 ID-uri unice, potrivirea cu scope/manifest/decisions, suma celor 1.026 alternative, hash-urile celor 216 imagini și egalitatea byte-identică a GeoPackage-ului activ cu HEAD. `summary.json` conține hash-urile surselor. `audit.json` separă observațiile vizuale de deciziile algoritmului. Controalele verifică proveniența/completitudinea raportării, nu corectitudinea în teren.

Reproducere din rădăcina repository-ului:

```powershell
venv/Scripts/python.exe workspace/option_b_visual_audit_20261019/build_report.py
```

Checkpointuri publicate pe branch-ul draftului PR #4: `9cfd387` (1–60), `ab049c7` (61–120), `ba1a0ca` (121–180). Checkpointul final se identifică în istoricul Git al dosarului. Publicarea nu autorizează merge și nu integrează corecții inexistente.
