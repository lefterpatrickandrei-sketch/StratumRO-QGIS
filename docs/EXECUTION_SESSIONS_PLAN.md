# Plan de ExecuÈ›ie pe Sesiuni â€” Remediere Defecte StratumRO

**Data:** 2026-10-08
**Bazat pe:** audit independent cu mÄƒsurÄƒtori proprii (IoU vs `data/ground_truth/tier1_teren.geojson`, rasterizare VRT, extracÈ›ie nDSM, comparaÈ›ie WKT Ã®ntre etape)
**Principiu de rutare (AGENTS.md Â§6):** geometrie/matematicÄƒ â†’ determinist local, zero LLM Ã®n calea de calcul. Audits de raÈ›ionament â†’ OpenRouter. Verificare vizualÄƒ multimodalÄƒ â†’ NVIDIA NIM. Audit local â†’ Ollama.

---

## Catalog modele disponibile (verificat)

| Rol | Model ID |
|:---|:---|
| Coder geodezie/deterministic | `openrouter/deepseek/deepseek-v4-pro-0813` |
| Coder rapid / mecanic | `openrouter/z-ai/glm-5.3-prime` |
| Adversarial review (deep) | `openrouter/anthropic/claude-opus-5.5` |
| Adversarial review (standard) | `openrouter/anthropic/claude-sonnet-5.5` |
| Adversarial review (rapid) | `openrouter/anthropic/claude-haiku-5.5` |
| RaÈ›ionament arhitectural | `openrouter/openai/gpt-6.1-sol-pro` |
| Verificare vizualÄƒ multimodal | `nvidia/meta/llama-3.2-11b-vision-instruct` |
| RaÈ›ionament video (opÈ›ional) | `nvidia/nvidia/cosmos-reason2-8b` |
| Audit local 8B | `ollama/qwen3-agent:8b`, `ollama/dolphin3:8b` |
| VLM local (de verificat) | `ollama/minicpm-v:8b` |
| Editare documente simple | `opencode/space-bunny-free` |

---

## Descoperire de viabilitate: VLM local `llava:13b` existÄƒ deja

Am interogat direct daemonul Ollama (`http://localhost:11434/api/tags`):

```
llava:13b            7.5 GB   â† VIZIUNE, nu era Ã®n catalogul de modele
minicpm-v:8b         5.1 GB
qwen3-agent:8b       4.9 GB
qwen3:8b             4.9 GB
qwen3-embedding:0.6b 0.6 GB
dolphin3:8b          4.6 GB
```

DouÄƒ corecÈ›ii faÈ›Äƒ de planul iniÈ›ial:

1. **`llava:13b` e instalat local** È™i nu apare Ã®n catalogul `tools.opencode.models` (care listeazÄƒ doar 3 modele Ollama). E cel mai puternic VLM local disponibil, cu 13B parametri â€” mai bun decÃ¢t MiniCPM-V 8B care a halucinat.
2. **`bakllava` È™i `llava-llama3` NU sunt instalate.** Le-am menÈ›ionat ca opÈ›iuni Ã®n planul iniÈ›ial pe baza prefixelor din cod â€” greÈ™it. `VISION_MODEL_PREFIXES` din `ollama_provider.py` conÈ›ine `"llava"`, deci `llava:13b` **va** fi detectat corect ca VISION. Bucla e deja compatibilÄƒ.

**Cheie API disponibilÄƒ Ã®n `.env`:** `NVIDIA_API_KEY`, `OPENROUTER_API_KEY`, `UNION_ALPHA_API_KEY`, `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `SAMBANOVA_API_KEY`, `CEREBRAS_API_KEY`, `GEMINI_API_KEY`, `DEEPSEEK_API_KEY`.

---

## Fallback-uri pe rol â€” VERIFICATE PRIN SONDAJ REAL

Toate modelele din catalog raporteazÄƒ cost $0.00, deci **costul nu e criteriu de departajare**. Fallback-ul se bazeazÄƒ pe *independenÈ›a furnizorului*: dacÄƒ un furnizor e picat, altul trebuie sÄƒ acopere.

### Rezultatele sondajului de viabilitate (2026-10-08, `max_tokens=16`, cerere realÄƒ)

Am trimis cereri reale la fiecare furnizor cu cheia din `.env`. Rezultate mÄƒsurate:

| Model | Furnizor | LatenÈ›Äƒ | Status |
|:---|:---|---:|:--|
| `z-ai/glm-5.3-prime` | openrouter | 922 ms | âœ… VIABIL |
| `openai/gpt-6-luna` | openrouter | 928 ms | âœ… VIABIL |
| `perceptron/perceptron-mk1.5` | openrouter | 954 ms | âœ… VIABIL |
| `qwen/qwen3.8-omni-flash` | openrouter | 1136 ms | âœ… VIABIL |
| `ibm-granite/granite-4.2-8b` | openrouter | 415 ms | âœ… VIABIL |
| `cohere/command-a-plus` | openrouter | 372 ms | âœ… VIABIL |
| `deepseek/deepseek-v4-pro-0813` | openrouter | 1337 ms | âœ… VIABIL |
| `mistralai/mistral-large-4-0` | openrouter | 1021 ms | âœ… VIABIL |
| `anthropic/claude-sonnet-5.5` | openrouter | 1449 ms | âœ… VIABIL |
| `moonshotai/kimi-k3` | openrouter | 608â€“1582 ms | âœ… VIABIL |
| `anthropic/claude-fable-5.1` | openrouter | 1798 ms | âœ… VIABIL |
| `x-ai/grok-4.7` | openrouter | 2066 ms | âœ… VIABIL |
| `google/gemini-3.8-flash` | openrouter | 1843 ms | âœ… VIABIL |
| `xiaomi/mimo-v2.6-pro` | openrouter | 3803 ms | âœ… VIABIL |
| `openai/gpt-6.1-sol-pro` | openrouter | 3631 ms | âœ… VIABIL |
| `qwen/qwen3.8-max-prime` | openrouter | 8676 ms | âœ… VIABIL |
| `anthropic/claude-opus-5.5` | openrouter | 5709 ms | âœ… VIABIL |
| `nvidia/nemotron-3.5-lightning-30b-a3b` | nvidia | 1308 ms | âœ… VIABIL |
| `z-ai/glm-5.3` | nvidia | â€” | âœ… rÄƒspunde (gol la 8 tokeni) |
| `meta/llama-3.2-11b-vision-instruct` | nvidia | â€” | âœ… VIABIL |
| `llava:13b` | ollama local | â€” | âœ… instalat, 7.5 GB |

### âŒ Modele EXCLUSE â€” nu sunt viabile

| Model | Motivul excluderii |
|:---|:---|
| `openrouter/deepseek/deepseek-v4-pro-0813` (direct) | **HTTP 402 Payment Required** â€” credit insuficient |
| `openrouter/z-ai/glm-5.3-prime` (direct) | **HTTP 402 Payment Required** â€” credit insuficient |
| `nvidia/deepseek-ai/deepseek-v4.1-flash` | **timeout >40 s** |
| `nvidia/z-ai/glm-5.3-flash` | **timeout >25 s** |
| `nvidia/moonshotai/kimi-k3` | **timeout 25 s** (merge pe openrouter) |
| `nvidia/google/google-paligemma` | **FAIL** pe ambele rute |
| `google/google-paligemma` (openrouter) | **FAIL** |
| `nvidia/synthetic-video-detector` | **FAIL** pe openrouter |
| `sakana/fugu-max` | **FAIL** |
| `inclusionai/ling-3.1-flash` | **FAIL** |
| `ollama/minicpm-v:8b` | rÄƒspunde, dar **a demonstrat halucinaÈ›ie** â€” exclus din rol de poartÄƒ |

**ConsecinÈ›Äƒ majorÄƒ:** planul iniÈ›ial pusese `openrouter/deepseek/deepseek-v4-pro-0813` drept model primar pentru 6 sesiuni de coder. **Nu e viabil** â€” contul DeepSeek direct nu are credit. ÃŽnlocuit cu `openrouter/deepseek/deepseek-v4-pro-0813` (acelaÈ™i model, alt furnizor, 1337 ms).

### Rol: Coder geodezie / determinist
| Nivel | Model | Furnizor | LatenÈ›Äƒ |
|:--|:---|:---|---:|
| 1 | `openrouter/deepseek/deepseek-v4-pro-0813` | openrouter | 1337 ms |
| 2 | `openrouter/xiaomi/mimo-v2.6-pro` | openrouter | 3803 ms |
| 3 | `openrouter/mistralai/mistral-large-4-0` | openrouter | 1021 ms |
| 4 | `openrouter/qwen/qwen3.8-max-prime` | openrouter | 8676 ms |

### Rol: Coder rapid / mecanic
| Nivel | Model | Furnizor | LatenÈ›Äƒ |
|:--|:---|:---|---:|
| 1 | `openrouter/z-ai/glm-5.3-prime` | openrouter | 922 ms |
| 2 | `openrouter/openai/gpt-6-luna` | openrouter | 928 ms |
| 3 | `openrouter/perceptron/perceptron-mk1.5` | openrouter | 954 ms |
| 4 | `openrouter/ibm-granite/granite-4.2-8b` | openrouter | 415 ms |

### Rol: Adversarial review profund
| Nivel | Model | Furnizor | LatenÈ›Äƒ |
|:--|:---|:---|---:|
| 1 | `openrouter/anthropic/claude-opus-5.5` | openrouter | 5709 ms |
| 2 | `openrouter/x-ai/grok-4.7` | openrouter | 2066 ms |
| 3 | `openrouter/moonshotai/kimi-k3` | openrouter | 608â€“1582 ms |
| 4 | `openrouter/qwen/qwen3.8-max-prime` | openrouter | 8676 ms |

**RegulÄƒ criticÄƒ pentru acest rol:** fallback-ul **nu poate fi acelaÈ™i model de familie**. DacÄƒ `claude-opus-5.5` a ratat ceva, `claude-sonnet-5.5` va rata la fel â€” erorile sunt corelate prin training. De aceea nivelul 2 e Grok, nu Claude.

### Rol: Adversarial review standard
| Nivel | Model | Furnizor | LatenÈ›Äƒ |
|:--|:---|:---|---:|
| 1 | `openrouter/anthropic/claude-sonnet-5.5` | openrouter | 1449 ms |
| 2 | `openrouter/moonshotai/kimi-k3` | openrouter | 608â€“1582 ms |
| 3 | `openrouter/google/gemini-3.8-flash` | openrouter | 1843 ms |
| 4 | `openrouter/xiaomi/mimo-v2.6-pro` | openrouter | 3803 ms |

### Rol: RaÈ›ionament arhitectural
| Nivel | Model | Furnizor | LatenÈ›Äƒ |
|:--|:---|:---|---:|
| 1 | `openrouter/openai/gpt-6.1-sol-pro` | openrouter | 3631 ms |
| 2 | `openrouter/anthropic/claude-fable-5.1` | openrouter | 1798 ms |
| 3 | `openrouter/moonshotai/kimi-k3` | openrouter | 608â€“1582 ms |
| 4 | `openrouter/google/gemini-3.8-flash` | openrouter | 1843 ms |

### Rol: Verificare vizualÄƒ multimodal (S2.4, S3.3)
| Nivel | Model | Furnizor | Note |
|:--|:--|:--|:--|
| 1 | `ollama/llava:13b` | local | 7.5 GB, ruleazÄƒ pe RTX 4050 |
| 2 | `nvidia/meta/llama-3.2-11b-vision-instruct` | nvidia | la distanÈ›Äƒ |
| 3 | `openrouter/qwen/qwen3.8-omni-flash` | openrouter | multimodal confirmat |

**NotÄƒ de guvernanÈ›Äƒ:** `minicpm-v:8b` **nu e fallback acceptabil** pentru o poartÄƒ de decizie, e doar pentru comparaÈ›ie. `paligemma` a fost exclus â€” e singurul model cu vedere din afara celor trei de mai sus È™i nu e instalabil acum. DacÄƒ toate trei eÈ™ueazÄƒ, P3 se Ã®ncheie UNVERIFIED.

### Rol: Audit local 8B
| Nivel | Model | Note |
|:--|:--|:--|
| 1 | `ollama/qwen3-agent:8b` | 4.9 GB |
| 2 | `ollama/qwen3:8b` | 4.9 GB |
| 3 | `ollama/dolphin3:8b` | 4.6 GB |

### Rol: Documente / editare simplÄƒ
| Nivel | Model |
|:--|:--|
| 1 | `opencode/space-bunny-free` |
| 2 | `opencode/mimo-v2.6-flash-free` |
| 3 | `opencode/ling-3.1-flash-free` |

### Rol: Securitate / validare ieÈ™ire model
| Nivel | Model | Note |
|:--|:--|:--|
| 1 | `nvidia/meta/llama-guard-4-12b` | nvidia |
| 2 | `openrouter/ibm-granite/granite-4.2-8b` | openrouter, 415 ms |

---

## ProcedurÄƒ de fallback (obligatorie)

CÃ¢nd modelul primar al unei sesiuni e indisponibil sau rateazÄƒ poarta:

1. **Nu rescrie obiectivul.** Fallback-ul primeÈ™te acelaÈ™i task, aceleaÈ™i poarte, aceleaÈ™i interdicÈ›ii.
2. **ÃŽnregistreazÄƒ schimbarea** Ã®n livrabil: `Model primar: X (indisponibil, motiv)` â†’ `Model folosit: Y`.
3. **DacÄƒ e rol de audit**, fallback-ul trebuie sÄƒ fie din altÄƒ familie de modele (vezi regula de mai sus).
4. **DacÄƒ e rol de coder**, fallback-ul poate fi din aceeaÈ™i familie â€” corectitudinea e verificatÄƒ de teste, nu de diversitate.
5. **Maxim 2 niveluri de fallback.** Trecerea prin 4 modele Ã®nseamnÄƒ de obicei cÄƒ task-ul e prost definit, nu cÄƒ modelul e prost.
6. **DacÄƒ toate nivelurile picteazÄƒ**, sesiunea se raporteazÄƒ ca BLOCATÄ‚. Nu se executÄƒ cu un model â€žaproape bun".

## Fallback pentru lipsa de subagent

Am observat cÄƒ subagentele eÈ™ueazÄƒ cu â€žexceed available credits" la paralelism mare. Alternative:

| Rol subagent | AlternativÄƒ cÃ¢nd creditele nu permit |
|:---|:---|
| `stratumro-coder` | `openrouter/deepseek/deepseek-v4-pro-0813` direct, sesiune unicÄƒ |
| `stratumro-reviewer` | `openrouter/anthropic/claude-opus-5.5` direct |
| `stratumro-geospatial` | determinist: `venv\Scripts\python` + rasterio/shapely |
| paralelism | max 2â€“3 subagent(e); restul secvenÈ›ial |

---

## P1 â€” ÃŽnÄƒlÈ›imi fictive â†’ mÄƒsurate din nDSM

**Defect:** `inaltime_max_m = 7.8` constant, `inaltime_med_m = 5.2` constant pentru toate cele 118 clÄƒdiri. nDSM real: min 0,9 / max 25,8 / mean 8,6 / std 4,4. 49/118 au Ã®nÄƒlÈ›ime realÄƒ > 8 m. `CLADIRI_SOL_ANCPI` e derivat din date inventate.

### Sesiunea S1.1 â€” Proiectare script mÄƒsurare
- **Model:** `openrouter/deepseek/deepseek-v4-pro-0813`
- **Subagent:** `stratumro-coder`
- **Task:** scrie `tools/recompute_heights_ndsm.py` care, pentru fiecare poligon din `CLADIRI_CADASTRU_CLEAN`, citeÈ™te `workspace/output/ndsm_stereo70.tif`, aplicÄƒ mascÄƒ de geometrie, calculeazÄƒ percentilele 50/90 È™i scrie `inaltime_med_m` / `inaltime_max_m`.
- **Livrabil:** script + tabel CSV `workspace/output/heights_before_after.csv`
- **PoartÄƒ:** niciun LLM Ã®n calea de calcul, doar numpy/rasterio

### Sesiunea S1.2 â€” Recalcularea amprentelor la sol
- **Model:** `openrouter/deepseek/deepseek-v4-pro-0813`
- **Subagent:** `stratumro-coder`
- **Task:** recalculeazÄƒ `CLADIRI_SOL_ANCPI` cu retragerea de streaÈ™inÄƒ pe baza Ã®nÄƒlÈ›imilor noi; verificÄƒ dacÄƒ retragerea trebuie sÄƒ fie dependentÄƒ de Ã®nÄƒlÈ›ime sau rÄƒmÃ¢ne fixÄƒ la âˆ’0,40 m (decizie documentatÄƒ).
- **Livrabil:** GeoPackage rescris + raport `raport_inaltimi_reale.md`
- **PoartÄƒ:** `area_sol_m2 < area_m2` pentru toate, `eave_offset_m` constant È™i unitar

### Sesiunea S1.3 â€” Audit adversarial Ã®nÄƒlÈ›imi
- **Model:** `openrouter/anthropic/claude-opus-5.5`
- **Task:** auditÄƒ scriptul S1.1/S1.2 cuå’Œå…¶å®ƒ dovezi: verificÄƒ masca, fereastra rasterului, tratamentul nodata, dacÄƒ percentilul 90 e corect pentru o streaÈ™inÄƒ.
- **Livrabil:** verdict scris cu dovezi citate
- **PoartÄƒ:** auditul nu poate spune â€žcorect" fÄƒrÄƒ verificare numericÄƒ proprie

### Sesiunea S1.4 â€” Regression gate
- **Model:** â€” (determinist, `venv\Scripts\python -m unittest discover stratum_ro/test`)
- **Livrabil:** 241 passed / 9 skipped / 0 failed din 250
- **PoartÄƒ:** orice eÈ™ec blocheazÄƒ P2

---

## P2 â€” Criteriul de safe margin distructiv

**Defect:** din 61 `CLADIRI_ELIMINATE_MARGINE_UNSAFE`, **40 sunt integral Ã®n interiorul rasterului real (>97%)**. Criteriul actual taie clÄƒdiri valide È™i pierde 5 din 29 clÄƒdiri ground truth (IoU 0,000), toate fiind detectate corect Ã®n `CLADIRI_HIBRID`. Parametrul âˆ’10 m e corect; **logica de filtrare e greÈ™itÄƒ**.

### Sesiunea S2.1 â€” Proiectare criteriu nou
- **Model:** `openrouter/deepseek/deepseek-v4-pro-0813`
- **Subagent:** `stratumro-geospatial`
- **Task:** implementeazÄƒ criteriul â€žpoligon intersectat de marginea rasterului (fracÈ›iune pixeli valizi < 97%)" Ã®n locul â€žcentru Ã®n afara poligonului de siguranÈ›Äƒ".
- **Livrabil:** `tools/apply_safe_margin_full_ortho.py` actualizat
- **PoartÄƒ:** **nicio comparaÈ›ie cu `data/ground_truth/`** â€” interdicÈ›ie absolutÄƒ de metric leakage

### Sesiunea S2.2 â€” MÄƒsurarea efectului
- **Model:** `openrouter/z-ai/glm-5.3-prime`
- **Task:** raporteazÄƒ: cÃ¢te poligoane se mutÄƒ din ELIMINATED Ã®n CLEAN, recall-ul GT (aÈ™teptat ~29/29), IoU median, bias de suprafaÈ›Äƒ.
- **Livrabil:** `raport_safe_margin_v2.md`
- **PoartÄƒ:** recall trebuie sÄƒ creascÄƒ; dacÄƒ scade, criteriul e greÈ™it

### Sesiunea S2.3 â€” Audit adversarial leakage
- **Model:** `openrouter/anthropic/claude-opus-5.5`
- **Task:** cautÄƒ orice loc unde codul foloseÈ™te `ref_id`, `tier`, `validare`, `sam2_score`, `conf_final` ca intrare de filtrare. ComparÄƒ cu `data/ground_truth/`.
- **Livrabil:** verdict explicit DA/NU pe leakage
- **PoartÄƒ:** verdict scris, nu implicat

### Sesiunea S2.4 â€” Verificare vizualÄƒ independentÄƒ
- **Model:** `nvidia/meta/llama-3.2-11b-vision-instruct`
- **Task:** primeÈ™te `inspectie_ortofoto_complet_safe_margin_v2.png` È™i o listÄƒ explicitÄƒ de clÄƒdiri numite; Ã®ntreabÄƒ despre **acele** clÄƒdiri, nu despre imagine Ã®ntreagÄƒ.
- **Livrabil:** verdict per clÄƒdire
- **PoartÄƒ:** raportul trebuie sÄƒ conÈ›inÄƒ cel puÈ›in `building_id` Ã®n rÄƒspuns, altfel e respins

---

## P3 â€” Stratul â€žVLM" care nu ruleazÄƒ VLM

**Defect:** `tools/generate_vlm_visual_results.py:69` apeleazÄƒ direct `verifier._heuristic_fallback(..., chip=None)`. Zero inferenÈ›Äƒ. `vlm_verdict = {'APPROVED': 416}` â€” 100%. `vlm_verdict` e funcÈ›ie de `area > 45 mÂ²` (`vlm_verifier.py:387-393`). Geometrie identicÄƒ cu `STAGE_1_RAW_CONTOUR` (415/415 WKT). **183 din 184 `ARTEFACTE_RESPINSE_SAM2` au fost aprobate.**

### Sesiunea S3.1 â€” Proiectare runner VLM real
- **Model:** `openrouter/deepseek/deepseek-v4-pro-0813`
- **Subagent:** `stratumro-coder`
- **Task:** scrie `tools/run_real_vlm_audit.py` care: decupeazÄƒ cipuri per clÄƒdire, trimite la `ollama/llava:13b` (sau NIM ca fallback), È™i **aplicÄƒ o guardie**: respinge rÄƒspunsul dacÄƒ e sub 200 caractere, dacÄƒ ecouleazÄƒ promptul, sau dacÄƒ nu conÈ›ine un `building_id` explicit.
- **Livrabil:** script + `vlm_guard.py` (funcÈ›ie testabilÄƒ)
- **PoartÄƒ:** guardia trebuie acoperitÄƒ de teste unitaire

### Sesiunea S3.2 â€” Implementare + teste ale guardiei
- **Model:** `openrouter/deepseek/deepseek-v4-pro-0813`
- **Subagent:** `stratumro-coder`
- **Task:** teste pentru: rÄƒspuns gol, ecou de prompt, rÄƒspuns fÄƒrÄƒ id, rÄƒspuns cu diacritice corupte, rÄƒspuns valid.
- **Livrabil:** extensie `stratum_ro/test/test_vlm_verifier.py`
- **PoartÄƒ:** toate trec; numÄƒrul total creÈ™te peste 250

### Sesiunea S3.3 â€” Run VLM real pe clÄƒdiri-critic
- **Model primar:** `ollama/llava:13b` (local, 7.5 GB, instalat)
- **Fallback:** `nvidia/meta/llama-3.2-11b-vision-instruct`
- **Task:** ruleazÄƒ pe 30 de clÄƒdiri: 15 din `CLADIRI_CADASTRU_CLEAN`, 15 din `ARTEFACTE_RESPINSE_SAM2`. Scorul: separare Ã®ntre cele douÄƒ clase.
- **Livrabil:** matrice de confuziune + separare
- **PoartÄƒ:** **dacÄƒ modelul nu separÄƒ cele douÄƒ clase, stratul nu e validat** â€” se raporteazÄƒ UNVERIFIED È™i atÃ¢t

### Sesiunea S3.4 â€” Baseline local pentru comparaÈ›ie
- **Model:** `ollama/minicpm-v:8b` â€” **doar pentru comparaÈ›ie, nu ca poartÄƒ de decizie**
- **Task:** aceleaÈ™i 30 de clÄƒdiri, acelaÈ™i prompt, pentru a demonstra dacÄƒ regresia vine din model sau din arhitectura de verificare.
- **Livrabil:** `raport_vlm_comparatie.md`

### Sesiunea S3.5 â€” Decizie de denumire (governance)
- **Model:** `openrouter/openai/gpt-6.1-sol-pro`
- **Task:** decide Ã®ntre (a) ramblare cu VLM real, (b) redenumiire Ã®n `HEURISTIC_AUDITED` È™i scoatere din livrabile, (c) eliminare completÄƒ.
- **Livrabil:** decizie + justificare Ã®n formatul celor 8 reguli
- **PoartÄƒ:** decizia e documentatÄƒ, nu implicitÄƒ

---

## P4 â€” `STAGE_5_FINAL_CONFIDENCE` no-op

**Defect:** 483/483 poligoane bit-cu-bit identice cu `STAGE_4_LIDAR_CONSTRAINED`. Etapa finalÄƒ nu face nimic. S4 vs S3: 427/483 identice (88% no-op). S2 adaugÄƒ 67 obiecte peste 416 (fracturare nedeclaratÄƒ).

### Sesiunea S4.1 â€” Localizarea cauzei
- **Model:** `openrouter/deepseek/deepseek-v4-pro-0813`
- **Task:** urmÄƒreÈ™te codul care scrie STAGE_4 È™i STAGE_5; identificÄƒ de ce copiazÄƒ, de ce S2 mÄƒreÈ™te numÄƒrul.
- **Livrabil:** hartÄƒ cod cu `fiÈ™ier:linie`
- **PoartÄƒ:** cauza demonstratÄƒ, nu ipotetizatÄƒ

### Sesiunea S4.2 â€” Implementare filtrare realÄƒ de Ã®ncredere
- **Model:** `openrouter/deepseek/deepseek-v4-pro-0813`
- **Subagent:** `stratumro-coder`
- **Task:** implementeazÄƒ praguri reale (suprafaÈ›Äƒ minimÄƒ, compactitate, raport nDSM, raport optic/lidar) care produc o selecÈ›ie nenulÄƒ È™i justificabilÄƒ.
- **Livrabil:** `STAGE_5_FINAL_CONFIDENCE` cu `n < 483`, coloanÄƒ `confidence` nenulÄƒ È™i nedegeneratÄƒ
- **PoartÄƒ:** **dacÄƒ rezultatul e tot 483, filtrarea nu funcÈ›ioneazÄƒ**

### Sesiunea S4.3 â€” Audit adversarial no-op
- **Model:** `openrouter/anthropic/claude-sonnet-5.5`
- **Task:** verificÄƒ independent cÄƒ STAGE_5 diferÄƒ acum de STAGE_4 prin comparaÈ›ie WKT.
- **Livrabil:** verdict cu numÄƒrÄƒtoare
- **PoartÄƒ:** auditul trebuie sÄƒ recalculeze singur, sÄƒ nu preia cifra din raport

---

## P5 â€” Artefacte respinse care rÄƒmÃ¢n Ã®n pipeline

**Defect:** 184 `ARTEFACTE_RESPINSE_SAM2` sunt Ã®ncÄƒ prezente Ã®n `STAGE_5_FINAL_CONFIDENCE` (184/184 cu overlap >50%).

### Sesiunea S5.1 â€” De ce nu sunt eliminate
- **Model:** `openrouter/deepseek/deepseek-v4-pro-0813`
- **Task:** urmÄƒreÈ™te codul; stratul e scris ca diagnostic sau ca filtru? DacÄƒ diagnostic, de ce nu se aplicÄƒ?
- **Livrabil:** explicaÈ›ie cu `fiÈ™ier:linie`

### Sesiunea S5.2 â€” Aplicarea filtrului
- **Model:** `openrouter/deepseek/deepseek-v4-pro-0813`
- **Subagent:** `stratumro-coder`
- **Task:** filtreazÄƒ artefactele din STAGE_5, pÄƒstrÃ¢nd un strat de diagnostic separat
- **Livrabil:** STAGE_5 fÄƒrÄƒ artefacte
- **PoartÄƒ:** **atenÈ›ie â€” nu elimina GT real.** VerificÄƒ explicit cÄƒ niciuna din cele 29 clÄƒdiri GT nu e eliminatÄƒ

### Sesiunea S5.3 â€” Validare recall dupÄƒ filtrare
- **Model:** `openrouter/z-ai/glm-5.3-prime`
- **Task:** recalculeazÄƒ IoU vs GT, comparÄƒ cu baseline-ul 24/29
- **Livrabil:** tabel recall
- **PoartÄƒ:** recall-ul nu poate scÄƒdea sub 24/29

---

## P6 â€” `AGENTS.md` stale

**Defect:** liniile 23 È™i 56 declarÄƒ 206 teste (197 trecute). Real: **241 trecute, 9 sÄƒrite, 0 eÈ™uate din 250**.

### Sesiunea S6.1 â€” Corectare documente
- **Model:** `opencode/space-bunny-free`
- **Task:** corecteazÄƒ cele douÄƒ rÃ¢nduri, adaugÄƒ data verificÄƒrii 2026-10-08
- **Livrabil:** diff Ã®n `AGENTS.md`
- **PoartÄƒ:** rulat È™i reconfirmat imediat Ã®nainte de scriere

### Sesiunea S6.2 â€” Reconciliere Â§6 provideri
- **Model:** `openrouter/anthropic/claude-sonnet-5.5`
- **Task:** `registry.py` Ã®nregistreazÄƒ 6 provideri (`AnthropicProvider` adÄƒugat), dar Â§6 documenteazÄƒ 5 È™i un rol Claude Desktop retras. AliniazÄƒ textul cu codul.
- **Livrabil:** Â§6 corect
- **PoartÄƒ:** numÄƒrul de provideri din doc = cel din `registry.py`

---

## P7 â€” IgienÄƒ repo È™i commit

**Defect:** `projects/` = 817 MB conÈ›ine `pyparsing`/`planetary_computer` vendorizate Ã®n `data/cache/`. Nimic sub `projects/` sau `workspace/` e ignorat. Nimic comitat din 2026-09-24.

### Sesiunea S7.1 â€” `.gitignore`
- **Model:** `openrouter/z-ai/glm-5.3-prime`
- **Task:** adaugÄƒ `**/data/cache/`, `workspace/**/*.gpkg`, `workspace/**/*.png`
- **Livrabil:** reguli verificate cu `git check-ignore`
- **PoartÄƒ:** niciun fiier sursÄƒ ignorat

### Sesiunea S7.2 â€” Staging selectiv
- **Model:** determinist
- **Task:** stageazÄƒ cod + config + rapoarte, exclude build outputs
- **Livrabil:** `git status` curat È™i explicabil
- **PoartÄƒ:** `cladiri_stereo70.gpkg` (18,5 MB) **nu** intrÄƒ

### Sesiunea S7.3 â€” Commit + raport
- **Model:** determinist
- **Livrabil:** un commit, mesaj care listeazÄƒ ce s-a reparat È™i ce rÄƒmÃ¢ne necunoscut

---

## Reguli de execuÈ›ie

1. **UndÄƒ 1 (paralel, ieftin):** S1.1, S6.1, S7.1
2. **UndÄƒ 2 (paralel):** S1.2, S6.2, S7.2
3. **UndÄƒ 3 (paralel):** S1.3, S2.1, S4.1, S5.1 â€” cu `claude-opus-5.5` È™i `deepseek-v4-pro`
4. **UndÄƒ 4:** S1.4 poartÄƒ, apoi S2.2, S2.3, S4.2, S5.2
5. **UndÄƒ 5 (vizual, costisitor, secvenÈ›ial):** S3.1 â†’ S3.2 â†’ S3.3 â†’ S3.4
6. **UndÄƒ 6:** S2.4, S4.3, S5.3, S3.5
7. **UndÄƒ 7:** S7.3

**Limitare de capacitate:** subagentele eÈ™ueazÄƒ cu â€žexceed available credits" cÃ¢nd ruleazÄƒ multe Ã®n paralel. RespectÄƒ 3â€“4 subagent(e) simultan, nu mai mult.

**InterdicÈ›ie absolutÄƒ:** nicio sesiune nu are voie sÄƒ citeascÄƒ `data/ground_truth/` pentru a regla parametri. Ground truth se foloseÈ™te **doar** la evaluare, dupÄƒ ce parametrii sunt fixaÈ›i. Singura excepÈ›ie e S2.3/S1.3, care *auditeazÄƒ* dacÄƒ cineva a Ã®ncÄƒlcat regula.

**Regula modelului zero-LLM:** S1.1, S1.2, S2.1, S2.2, S4.2, S5.2, S5.3, S7.2 â€” LLM scrie codul, dar niciun LLM nu intervine Ã®n calculul geometric. La fel: rotaÈ›ii, tampoane, arii, perimetre, percentili raster.

**Regula honestitÄƒÈ›ii:** dacÄƒ o poartÄƒ eÈ™ueazÄƒ, sesiunea se opreÈ™te È™i raporteazÄƒ. Nu se reparÄƒ prin relabelling. Exemplu: dacÄƒ S3.3 aratÄƒ cÄƒ VLM-ul nu separÄƒ artefactele de clÄƒdiri, P3 se Ã®ncheie cu â€žUNVERIFIED" È™i stratul e eliminat â€” **nu** se rescrie raportul ca sÄƒ parÄƒ reuÈ™it.
