# Reparare CI — 2026-10-18

Proprietarul a autorizat explicit auditul și repararea CI după publicarea draft PR #3, cu investigarea provenienței înainte de orice schimbare de referință. Etapa este separată de curățenia de documentație (`055d236`, `728cf7e`, `d335fd6`).

## Cauze demonstrate și corecții

| Problemă | Dovadă | Corecție |
|---|---|---|
| CI instala o listă incompletă, diferită de runtime | Jurnalul inițial: lipsesc torch, FastAPI, Anthropic | `requirements-ci.txt` reutilizează `requirements.txt`, adaugă SDK-ul mockuit și clientul de test. CI instalează torch CPU înainte, verifică dependențele și păstrează matricea Windows/Linux, Python 3.10/3.11. |
| Testul snapshot presupunea Windows | Assertion `windows` pe un runner Linux | Compară cu platforma reală și respectă caracterul opțional al RAM raportat. Nu s-a modificat detectorul hardware. |
| Testul resolver cerea modelul de pe calculatorul proprietarului | Test cere fișier local SAM2 de peste 100 MB | Verifică lipsa explicită a datelor și metadatele pentru GT versionat plus un mic fișier de test declarat ca atare. Fără download/inferență sau pretenție că fixture-ul este model valid. |
| Hash-uri LF/CRLF | `frozen_input_provenance.json` | Compară cu hash-urile înghețate acceptând exclusiv conversia LF/CRLF a checkoutului; nu reserializează JSON și nu elimină spații. Testul refuză o coordonată modificată. |
| Hash al forwarderului comparat cu implementarea | Manifestul a înregistrat deja `volumetric_3d.py` ca forwarder | Verifică exact calea manifestului. Testează identitatea aliasurilor și adaugă receipt separat pentru implementarea relocată. |
| Un test cu model dublu necesita SAM2 instalat | Patch-urile încercau să importe pachetul opțional | Testul regional furnizează cele două contracte de import prin module de test izolate. Aceeași verificare completă de NoData/unknown/export rămâne activă. |

## Integritate și proveniență

`audit_frozen_inputs.py` a comparat variantele raw/LF/CRLF și istoricul fără a rescrie manifestele. `manifest_ground_truth.json` și `manifest_critical_modules.json` au rămas identice cu versiunea comisă.

Implementarea `stratum_ro/domain/city_3d/builder.py` este byte-identică (9350 bytes, SHA-256 `3a9a4e5e5de513a5b0f304fa80c1288f72556de44f23c7228c09ba1ee4ecec09`) cu `stratum_ro/volumetric_3d.py` din commitul istoric `0f9078257cb9304ef32ca83be0e6deb0556cdbb7`. Receipt-ul nou `workspace/baseline/approved_module_relocations.json` păstrează această relație; nu înlocuiește hash-ul original al forwarderului și nu este o regenerare a etichetelor/metricilor.

`volumetric_extraction.diff` arată comparația greșită care cauza eroarea: forwarder versus implementare completă. `volumetric_implementation_provenance.json` consemnează comparația corectă între implementarea istorică și cea relocată, care sunt identice.

## Verificări locale

- `local_targeted_tests.txt`: 25 teste de freeze, resolver și orchestrare, toate trecute.
- `local_dependency_regressions.txt`: 37 teste providers mockuite, roof workflow, prompt SAM2 și runner regional cu model dublu, toate trecute.
- `dependency_resolution.json`: rezolvare `pip --dry-run` reușită în mediul existent, fără instalare sau modificarea acestuia. Aceasta nu dovedește singură instalare curată pe Linux.
- Cele 16 căi urmărite modificate preexistent, inclusiv fișierele celorlalți agenți și GIS, au fost reverificate și nu au fost schimbate.
- Codul de producție al geometriei, segmentării și datelor nu a fost modificat în această etapă.

Suita completă este verificată de runner-ele CI pe commitul publicat, cu checkout curat. Nu înlocuiți acest rezultat cu testarea locală selectată sau cu o afirmație despre acuratețea extragerii clădirilor. PR-ul rămâne draft, fără merge.

## Rezultat complet publicat

[Rularea 39119653317](https://github.com/lefterpatrickandrei-sketch/StratumRO-QGIS/actions/runs/39119653317), la commitul de cod `85a51efa0f0ca8806ae703265f9d0d7feb909738`, a trecut pe toate cele patru combinații Windows/Linux și Python 3.10/3.11. Fiecare job a executat verificarea rapidă (17 teste), suita completă (459 teste: 450 trecute, 9 omise pentru context QGIS) și verificarea independentă existentă.

[Rezultatul structurat](run_39119653317_attempt1.json) leagă commitul, joburile, etapele, numărul de teste și hash-urile jurnalelor. Cele patru fișiere `github_job_*.txt` păstrează jurnalele publice complete; `collect_ci_evidence.py` le poate colecta prin citire, fără schimbarea joburilor. Formatarea lor brută este păstrată prin `.gitattributes`.

Acesta este rezultatul verificărilor software și de integritate, nu o măsurare nouă de acuratețe cadastrală sau o inferență reală a ultimului model. Avertismentele platformei despre versiuni viitoare de runner/actions nu au eșuat joburile și nu au determinat actualizări suplimentare în această etapă.

## Referințe tehnice

[PyTorch — instalare CPU](https://pytorch.org/get-started/locally/) pentru runner-ele fără GPU și [Git — conversia textului la checkout](https://git-scm.com/docs/gitattributes) pentru diferențele LF/CRLF. Nu s-a instalat un nou model sau serviciu AI.
