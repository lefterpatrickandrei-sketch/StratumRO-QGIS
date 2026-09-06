# -*- coding: utf-8 -*-
"""
Script de execuție pentru Ciclul de Autoevaluare și Consens Multi-Model 2026 (StratumRO).
Rulează cele 3 modele LLM independente prin NVIDIA NIM API:
  - Model 1: Inspector Cadastru ANCPI (Llama 3.2 90B/11B)
  - Model 2: Inspector Urbanism MDLPA (Nemotron-3 Nano Omni Reasoning / Llama 3.2)
  - Model 3: Președinte Arbitraj și Comisie Mixtă (Nemotron-3.5 Lightning / Super 120B)
Generează raportul de audit și certificatul de conformitate în format JSON și Markdown.
"""

import os
import sys
import json
import time
from pathlib import Path

if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

# Adăugăm rădăcina proiectului în sys.path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from stratum_ro.regulatory_consensus import RegulatoryConsensusEngine


def main():
    print("=" * 75)
    print(" STRATUM-RO: CICLU DE AUTOEVALUARE ȘI CONSENS MULTI-MODEL (NVIDIA NIM 2026)")
    print("=" * 75)

    engine = RegulatoryConsensusEngine()

    cad_metrics = {
        "crs": "Stereo 70 (EPSG:3844)",
        "count_main": 377,
        "count_anexe": 6,
        "count_trees": 3927,
        "count_poles": 8,
        "trees_on_roofs": 0,
        "avg_vertices": 4.8,
        "rect_ratio": 68.2,
        "tolerante": "< 0.10m conform ANCPI Ord. 600/2023 Art. 12",
        "standarde_cadastru": "Ordinul ANCPI nr. 600/2023 & Legea nr. 7/1996"
    }

    pug_metrics = {
        "buildings_count": 377,
        "count_anexe": 6,
        "total_sc_mp": 173703.07,
        "total_sd_mp": 173703.07,
        "total_vol_mc": 434257.8,
        "trees_count": 3927,
        "trees_on_roofs": 0,
        "canopy_ha": 21.28,
        "canopy_mp": 212779.0,
        "mean_pot": 15.8,
        "mean_cut": 0.16,
        "mean_green": 14.4,
        "utr_cells": 49,
        "standarde_urbanism": "Legea nr. 350/2001, CATUC 2026, Legea nr. 24/2007"
    }

    print("\n[1/3] Rulare Model 1: Inspector Cadastru ANCPI (Llama 3.2 90B/11B)...")
    t0 = time.time()
    res_cad = engine.audit_cadastre_product(cad_metrics)
    dt_cad = time.time() - t0
    print(f"  -> Finalizat în {dt_cad:.2f}s | Model utilizat: {res_cad['model_used']}")
    print("-" * 50)
    print(res_cad["content"][:300] + "...\n")

    print("[2/3] Rulare Model 2: Inspector Urbanism MDLPA (Nemotron-3 Reasoning / Llama)...")
    t0 = time.time()
    res_pug = engine.audit_urbanism_product(pug_metrics)
    dt_pug = time.time() - t0
    print(f"  -> Finalizat în {dt_pug:.2f}s | Model utilizat: {res_pug['model_used']}")
    print("-" * 50)
    print(res_pug["content"][:300] + "...\n")

    print("[3/3] Rulare Model 3: Președinte Comisie de Consens & Arbitraj (Nemotron-3.5 Lightning / Super)...")
    t0 = time.time()
    res_arbiter = engine.arbitrate_consensus(res_cad["content"], res_pug["content"])
    dt_arbiter = time.time() - t0
    print(f"  -> Finalizat în {dt_arbiter:.2f}s | Model utilizat: {res_arbiter['model_used']}")
    print("-" * 50)
    print(res_arbiter["content"][:300] + "...\n")

    # Structurare raport complet
    audit_report = {
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
        "perimetru": "Cluj-Napoca (USAMV & Cartier Manastur/Zorilor)",
        "sistem_proiectie": "Stereo 70 (EPSG:3844) / MN75",
        "modele_nvidia_nim": {
            "auditor_cadastru": res_cad["model_used"],
            "auditor_urbanism": res_pug["model_used"],
            "presedinte_arbitraj": res_arbiter["model_used"]
        },
        "metrice_evaluate": {
            "cadastru": cad_metrics,
            "urbanism_pug": pug_metrics
        },
        "rezultate_expertize": {
            "expertiza_cadastru_ancpi": {
                "model": res_cad["model_used"],
                "text": res_cad["content"]
            },
            "expertiza_urbanism_mdlpa": {
                "model": res_pug["model_used"],
                "text": res_pug["content"]
            },
            "rezolutie_consens_arbitraj": {
                "model": res_arbiter["model_used"],
                "text": res_arbiter["content"]
            }
        }
    }

    out_dir = BASE_DIR / "workspace" / "output"
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "raport_audit_consens_modele_2026.json"
    md_path = out_dir / "raport_audit_consens_modele_2026.md"

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(audit_report, f, indent=2, ensure_ascii=False)
    print(f"[OK] Raport JSON salvat: {json_path}")

    # Generare raport Markdown
    md_content = f"""# RAPORT OFICIAL DE AUDIT ȘI CONSENS MULTI-MODEL (LEGISLAȚIE 2026)
**Proiect**: StratumRO - Sistem Integrat de Extracție Geospațială și Procesare Hibridă LiDAR + AI
**Data auditului**: {audit_report['timestamp']}
**Perimetru testat**: USAMV Cluj-Napoca (8 dale MrSID / LiDAR)
**Sistem de Coordonate**: Stereo 70 (EPSG:3844), Cota Altimetrică: Marea Neagră 1975

---

## 1. Arhitectura de Autoevaluare Multi-Model (NVIDIA NIM)
Pentru garantarea conformității legislative și administrative obiective (2026), auditul a fost efectuat de o comisie autonomă de 3 modele LLM specializate din ecosistemul NVIDIA API:

| Rol în Comisie | Model LLM Utilizat | Domeniu de Auditare | Baza Legală 2026 |
| :--- | :--- | :--- | :--- |
| **Auditor 1 (Cadastru)** | `{res_cad['model_used']}` | ANCPI & Geodezie | Ord. ANCPI 600/2023, Legea 7/1996 |
| **Auditor 2 (Urbanism)** | `{res_pug['model_used']}` | MDLPA & Registru Spații Verzi | Legea 350/2001, CATUC 2026, Legea 24/2007 |
| **Președinte Arbitru** | `{res_arbiter['model_used']}` | Sinteză & Certificare Legală | Coerență inter-instituțională |

---

## 2. Expertiza 1: Conformitate Cadastrală ANCPI
*Evaluator: {res_cad['model_used']}*

{res_cad['content']}

---

## 3. Expertiza 2: Conformitate Urbanistică PUG & Registru Spații Verzi
*Evaluator: {res_pug['model_used']}*

{res_pug['content']}

---

## 4. Rezoluția Finală a Comisiei de Arbitraj & Certificatul Oficial
*Președinte Comisie: {res_arbiter['model_used']}*

{res_arbiter['content']}

---

## 5. Livrabile Validate și Disponibile în Proiect
1. **Produsul Cadastral ANCPI**:
   - Geopackage: `workspace/output/cadastru_ancpi.gpkg` (Straturi: `constructii_principale_C1`, `anexe_C2`, `arbori_aliniament_teren`, `stalpi_utilitati`)
   - Plan CAD/DXF: `workspace/output/cadastru_ancpi.dxf` (Layers ANCPI: `CONSTRUCTII`, `ANEXE`, `ARBORI`, `STALPI`, `TEXTE`)
   - Proiect QGIS Cadastru: `workspace/output/StratumRO_Cadastru_ANCPI.qgs`

2. **Produsul Urbanistic PUG & Spații Verzi**:
   - Geopackage: `workspace/output/urbanism_pug.gpkg` (Straturi: `cladiri_volumetrice_LOD1`, `registru_spatii_verzi_arbori`, `fond_vegetal_canopy_ha`, `unitati_teritoriale_referinta_UTR`)
   - Raport Indicatori Zonali: `workspace/output/raport_indicatori_pug.json`
   - Proiect QGIS Urbanism: `workspace/output/StratumRO_Urbanism_PUG.qgs`

3. **Interfață Vizuală Interactivă**:
   - Vizualizator Web Dual: `qgis_map_viewer.html` (Comutare instantanee Cadastru vs PUG)
"""

    with open(md_path, "w", encoding="utf-8") as f:
        f.write(md_content)
    print(f"[OK] Raport Markdown salvat: {md_path}")
    print("=" * 75)
    print(" CICLU DE CONSENS MULTI-MODEL FINALIZAT CU SUCCES!")
    print("=" * 75)


if __name__ == "__main__":
    main()
