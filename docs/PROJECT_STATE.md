# Starea verificată a StratumRO

Actualizare: 2026-10-18. Bază inspectată înaintea reorganizării: `170407c`, local `main`. Acest document distinge citirea codului, dovezile unei rulări anterioare și obiectivele neimplementate. Reorganizarea documentației nu reprezintă o nouă validare a algoritmilor.

## Produs și prioritate

StratumRO este platforma care coordonează lucrul geodezului între date, instrumente și aplicații specializate, inclusiv QGIS. Reutilizarea acestora este parte a arhitecturii. Proprietarul dorește o aplicație proprie, cu sarcini formulate prin prompt și execuție automată până la livrabile. Prioritatea curentă este fluxul cadastral; platforma poate deservi și alte domenii.

Această direcție nu înseamnă că există deja automatizare generală, fără erori, pentru orice zonă. Cazurile incerte și lipsa datelor trebuie raportate, nu ascunse printr-un contur forțat sau un verdict automat.

## Ce există și ce dovedește

| Componentă | Dovadă în repository | Limită actuală |
|---|---|---|
| Plugin QGIS și provider de procesare | `stratum_ro/__init__.py`, `stratum_ro/processing_provider.py`, `stratum_ro/metadata.txt` | Metadata este experimentală; afirmațiile de conformitate din ea nu sunt o certificare verificată de acest audit. |
| Nucleu și contracte | `stratum_ro/core/`, `stratum_ro/contracts/` | Existență și structură inspectate static; integrarea tuturor apelanților nu este demonstrată. |
| Serviciu platformă, API și acces QGIS | `stratum_ro/api/service.py`, `start_platform.py` | Cod de conectare existent; nu s-a pornit serverul și nu s-a verificat live conectivitatea în auditul de documentație. |
| Flux de acoperișuri revizuite | `stratum_ro/cadastral_roof_workflow.py`, `PlatformService.create_cadastral_roof_workflow` | Flux explicit opt-in; nu este detector regional semantic validat. |
| Scanare regională automată | `stratum_ro/regional_roofs.py`, `stratum_ro/regional_review.py`, `tools/run_regional_roofs.py` | Rulare reală și audit vizual existente; nepregătită pentru producție, fără acuratețe/recall măsurate independent. |
| Pachete cadastru și PUG | `stratum_ro/cadastral_product.py`, `stratum_ro/pug_product.py`, `tools/build_dual_products.py` | Generare existentă; estimările și statutul profesional al exporturilor necesită corecții și verificări. |
| Aplicație desktop proprie distribuită | Direcție acceptată în documentul de identitate | Un `.exe` final instalabil nu a fost verificat în această etapă; launcherul Python/web nu dovedește acest livrabil. |
| Hugging Face / Rust | Opțiuni discutate în handoff-ul regional | Nu sunt condiții obligatorii ale fluxului actual; fără migrare Rust sau backend cloud implementat prin acest audit. |

## Proiectul QGIS și selecțiile active

Proiectul comun este [inspectie_corectii.qgs](../workspace/reviews/body_recovery_20261013/inspectie_corectii.qgs). Ultimul handoff de produs consemnează 69 straturi; nu este un număr recitit live în auditul din 2026-10-18.

- Lot1 și cazurile acceptate din Lot2 își păstrează verdictele. T10 acceptat rămâne separat de clădirea joasă gri din vest; T08/T09 rămân respinse/nerecuperate.
- Lot3: selecția este [selected_v3, prin CURRENT_SELECTION.json](../workspace/reviews/lot3_repairs_20261017/CURRENT_SELECTION.json), 20 ipoteze de acoperiș pentru T11–T20, fără acceptare globală nouă. T14 și mai multe identități/joncțiuni necesită verificare; curtea T17 nu este dovedită integral liberă. Vezi [handoff](STRATUMRO_LOT3_REPAIRS_HANDOFF_2026-10-17.md).
- Lot4: [CURRENT_SELECTION.json](../workspace/reviews/lot4_20261017/CURRENT_SELECTION.json), T21–T30: nouă ipoteze, T22 nerezolvat. T21/T24/T29 necesită finisare; plauzibilitatea evaluată de agent nu înseamnă acceptarea proprietarului. Vezi [auditul vizual](STRATUMRO_LOT4_AND_LOT3_VISUAL_RECHECK_2026-10-17.md).
- Regional: [CURRENT_REVIEW.json](../workspace/reviews/regional_roofs_20261017/CURRENT_REVIEW.json) selectează `masked_review_v2`. 144 ferestre planificate, 67 cu date valide și 77 fără date în nucleu; circa 0,420 km² acoperire validă. Cele 380 ipoteze cu sprijin contextual, 644 optic incerte și 1057 vegetație probabilă nu sunt un inventar de clădiri validate.

Inferența regională reală a folosit codul de la `1d9685e`. Rutarea ulterioară și masca finală au fost aplicate observațiilor reale salvate; ultima versiune combinată nu a fost rulată din nou cu model real pe întreaga zonă. Scenariile T10 cu offset de 0,25/0,50 m sunt ilustrative, nu măsurători ale amprentei la sol. [Dovezi și limite complete](STRATUMRO_REGIONAL_AUTOMATION_AND_HF_2026-10-17.md).

Contururile aparent întrerupte din unele capturi aveau și o cauză de afișare: rastere de detaliu peste vectori. `stratum_ro/qgis_render_order.py` și dovezile din `render_order_fix/` consemnează corecția ordinii. Aceasta nu repară greșelile geometrice ale conturului.

## Probleme confirmate prin citire, nereparate aici

1. `CadastralProductGenerator` are definiții atât în `stratum_ro/cadastral_product.py`, cât și în `stratum_ro/domain/cadastre_ro/product.py`. Generatorul dual importă încă varianta din rădăcina pachetului. Consolidarea cere verificarea apelanților și compatibilității; nu se mută sau șterge arbitrar una dintre ele.
2. `CoreRasterReader.read_window` returnează o bandă și transformarea unei ferestre dintr-un fișier. Nu constituie singur contractul complet pentru mozaic RGB și mască validă. `contracts/raster.py` și `contracts/pointcloud.py`, menționate de un raport local de fază 3, nu existau în inventarul verificat. Raportul nu poate înlocui această verificare.
3. Generatorul cadastral atribuie direct `validare_ancpi = "ADMIS"`. Acesta este un atribut generat de cod, fără dovadă de validare externă. Stările exportului trebuie revizuite într-o sarcină de cod distinctă.
4. `engine/time_study_benchmark.py` generează timpi manuali/revizie prin distribuții aleatoare. Afirmațiile istorice de economie de timp nu sunt demonstrate printr-un studiu de operatori citit în acest audit.
5. PUG estimează nivelurile folosind 3 m, folosește celule de 150 × 150 m denumite `UTR_GRID` și o valoare fixă pentru starea sanitară a arborilor. Acestea nu dovedesc UTR-uri oficiale sau inspecție fitosanitară.
6. Workflow-ul manual `.github/workflows/test-llm-orchestrator.yml` include `|| true` după test. Poate masca o eroare; schimbarea CI rămâne de aprobat și verificat separat.
7. Licența root și antetele unor surse ale pluginului diferă. Nu au fost schimbate și nu s-a certificat compatibilitatea distribuției.

## Git și documentație

La începutul reorganizării: 2015 fișiere urmărite, 936 neversionate neignorate, 16 modificări urmărite preexistente și nouă worktree-uri. GitHub `main`, verificat prin citire, era la `08524df`; local erau 35 commituri suplimentare înaintea checkpointurilor acestei curățenii. LFS este instalat, dar lista fișierelor LFS era goală.

[Inventarul și hash-urile](../workspace/repository_cleanup_20261018/README.md) documentează protejarea lucrului preexistent. Cele 13 rapoarte istorice și snapshot-urile documentelor sunt în [junk/](../junk/README.md). Nu s-au șters surse, date ori istoric. Proprietarul a ales ulterior publicarea în [draft PR #3](https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS/pull/3), fără merge. Branch-ul publicat include progresul local anterior și reorganizarea; `main` a rămas la `08524df` la verificarea publicării. [Dovada publicării](../workspace/repository_cleanup_20261018/publication_result.json) conține snapshot-ul inițial al PR-ului. Verificările CI erau încă în curs, fără verdict de succes.

## Următoarele decizii

Etapa aprobată de documentație a trecut verificarea hash-urilor și a celor 67 legături; publicarea este într-un draft PR. Urmează citirea rezultatelor CI și alegerea priorităților de cod: consolidarea apelanților, stările exporturilor, contractul comun raster, erorile vizuale și evaluarea regională independentă. Cele 936 fișiere neversionate au [inventar separat](../workspace/repository_cleanup_20261018/remaining_inventory.json), fără adoptare sau arhivare în masă. Nu presupune autorizată prin curățenie o rescriere, migrare Rust, instalare de skilluri sau un nou serviciu extern.

Prima execuție CI publicată a eșuat pe Linux. Jobul Python 3.10 raportează 443 teste, 4 failures, 19 errors și 9 skipped: lipsesc `anthropic`, `fastapi` și `torch`, există verificări de hash nereconciliate și un test care presupune Windows. [Jurnalul și diagnosticul inițial](../workspace/repository_cleanup_20261018/ci_initial_failure_summary.json) păstrează detaliile. Acestea nu au fost reparate în reorganizarea documentației; nu modifica automat hash-uri sau dezactiva teste pentru a obține verde. Proprietarul a autorizat ulterior o etapă distinctă de audit/reparare CI; modificările vor avea checkpoint și dovezi separate.

Etapa CI autorizată are [dosar separat](../workspace/ci_repair_20261018/README.md): dependențe comune cu runtime-ul, torch CPU, teste portabile, hash-uri originale verificate cu tratarea LF/CRLF și receipt al implementării 3D identice cu sursa istorică. Cele 62 teste locale selectate au trecut. La commitul de cod `85a51ef`, [rularea completă](https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS/actions/runs/39119653317) a trecut pe Windows/Linux și Python 3.10/3.11: 459 teste în fiecare job, cu 450 trecute și 9 omise pentru context QGIS, plus verificarea rapidă și etapa independentă. Manifestele originale, datele, algoritmii produsului și lucrările preexistente sunt păstrate. Rezultatul este legat de acel commit; starea unui commit ulterior se citește pe PR. Nu stabilește acuratețea contururilor sau automatizarea completă a platformei.
