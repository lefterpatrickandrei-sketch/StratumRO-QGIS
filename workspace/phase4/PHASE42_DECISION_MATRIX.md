# Phase 4.2 Decision Matrix — StratumRO

**Authoritative Decision Matrix for Component Ownership, Canonical Paths, and Consolidation Actions**  
*Status as of 2026-09-20 — Evaluated under Master Reorientation Governance*

---

## 1. Comprehensive Component Decision Matrix

| Component / Subsystem | Current Owner | Correct Owner | Canonical File (Target) | Duplicate File (Current) | Product / SDK | Action Later (Phase 4.3+) | Risk |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :---: |
| **Cadastral DXF Exporter** | Root (`cad_exporter.py`) | Domain (`cadastre_ro`) | `stratum_ro/domain/cadastre_ro/exporter.py` | `stratum_ro/cad_exporter.py` | **Product** | Convert root to forwarder re-exporting canonical class | Low |
| **Cadastral Product Gen** | Root (`cadastral_product.py`)| Domain (`cadastre_ro`) | `stratum_ro/domain/cadastre_ro/product.py` | `stratum_ro/cadastral_product.py` | **Product** | Convert root to forwarder re-exporting canonical class | Low |
| **Volumetric 3D Builder** | Root (`volumetric_3d.py`) | Domain (`city_3d`) | `stratum_ro/domain/city_3d/builder.py` | `stratum_ro/volumetric_3d.py` | **Product** | Convert root to forwarder re-exporting canonical class | Low |
| **LiDAR Processor** | Root (`lidar_processor.py`) | Domain (`lidar`) | `stratum_ro/domain/lidar/processor.py` | `stratum_ro/lidar_processor.py` | **Product** | Convert root to forwarder re-exporting canonical class | Med |
| **LiDAR Quality Gate** | Root (`lidar_quality_gate.py`)| Domain (`lidar`) | `stratum_ro/domain/lidar/quality_gate.py` | `stratum_ro/lidar_quality_gate.py` | **Product** | Convert root to forwarder re-exporting canonical class | Med |
| **Candidate Generator** | Root (`candidate_generator.py`)| Domain (`vision`) | `stratum_ro/domain/vision/candidates.py` | `stratum_ro/candidate_generator.py` | **Product** | Convert root to forwarder re-exporting canonical class | Low |
| **ONNX Vision Engine** | Root (`onnx_engine.py`) | Domain (`vision`) | `stratum_ro/domain/vision/engine.py` | `stratum_ro/onnx_engine.py` | **Product** | Convert root to forwarder re-exporting canonical class | Med |
| **Mask Fusion Engine** | Root (`mask_fusion.py`) | Domain (`vision`) | `stratum_ro/domain/vision/fusion.py` | `stratum_ro/mask_fusion.py` | **Product** | Convert root to forwarder re-exporting canonical class | Low |
| **Vegetation Filter** | Root (`vegetation_filter.py`)| Domain (`vision`) | `stratum_ro/domain/vision/vegetation.py` | `stratum_ro/vegetation_filter.py` | **Product** | Convert root to forwarder re-exporting canonical class | Low |
| **Topography Adapter** | Domain (`topography`) | Domain (`topography`) | `stratum_ro/domain/topography/adapter.py` | *None (No duplicate)* | **Product** | Retain as PARTIAL capability stub; do not expand | None |
| **Scientific Core (Geodesy)**| Core (`core/geodesy/`) | Core (`core/geodesy/`) | `stratum_ro/core/geodesy/` | *None (Unique)* | **Product Core** | Keep untouched; pure local Stereo 70 math | High |
| **Scientific Core (Geometry)**| Core (`core/geometry/`) | Core (`core/geometry/`) | `stratum_ro/core/geometry/` | *None (Unique)* | **Product Core** | Keep untouched; pure 90° CAD orthogonalization | High |
| **Scientific Core (Pointcloud)**| Core (`core/pointcloud/`)| Core (`core/pointcloud/`)| `stratum_ro/core/pointcloud/` | *None (Unique)* | **Product Core** | Keep untouched; LAS/LAZ ground filtering | Med |
| **Scientific Core (QA/QC)** | Core (`core/qa_qc/`) | Core (`core/qa_qc/`) | `stratum_ro/core/qa_qc/` | *None (Unique)* | **Product Core** | Keep untouched; geodetic validator & rules | High |
| **Scientific Core (Raster)** | Core (`core/raster/`) | Core (`core/raster/`) | `stratum_ro/core/raster/` | *None (Unique)* | **Product Core** | Keep untouched; windowed VRT / GeoTIFF reader | Med |
| **Interface Contracts** | Contracts (`contracts/`) | Contracts (`contracts/`) | `stratum_ro/contracts/` | *None (Unique)* | **Product Core** | Keep untouched; 9 abstract interface modules | High |
| **Anthropic Provider** | AI (`ai/providers/`) | Dev SDK | `stratum_ro/ai/providers/anthropic_provider.py` | *None* | **Dev SDK** | Logical segregation; used for coding/tests | Low |
| **OpenAI Provider** | AI (`ai/providers/`) | Dev SDK | `stratum_ro/ai/providers/openai_provider.py` | *None* | **Dev SDK** | Logical segregation; used for architecture | Low |
| **Union Alpha Provider** | AI (`ai/providers/`) | Dev SDK | `stratum_ro/ai/providers/union_alpha_provider.py` | *None* | **Dev SDK** | Logical segregation; used for Kilo audits | Low |
| **NVIDIA NIM Provider** | AI (`ai/providers/`) | Both (SDK / Product) | `stratum_ro/ai/providers/nvidia_nim_provider.py` | *None* | **Both** | Keep; dual-use visual inspection and VLM | Low |
| **Local Mock Provider** | AI (`ai/providers/`) | Product Runtime | `stratum_ro/ai/providers/local_provider.py` | *None* | **Product** | Keep; air-gapped deterministic baseline | Low |
| **Ollama Provider** | AI (`ai/providers/`) | Excluded System | `stratum_ro/ai/providers/ollama_provider.py` | *None* | **EXCLUDED** | Deprecate permanently per §13, §80 | Low |
| **QGIS Desktop Plugin** | Client (`stratum_ro/`) | Product Client | `stratum_ro/stratum_ro_dockwidget.py` | *None* | **Product** | Keep; update imports once forwarders active | Med |
| **QGIS Processing Algo** | Client (`stratum_ro/`) | Product Client | `stratum_ro/cadastral_algorithm.py` | *None* | **Product** | Keep; update imports once forwarders active | Med |
| **Ground Truth Data** | Data (`data/ground_truth/`)| Product Scientific Data | `data/ground_truth/tier1_teren.geojson` | *None* | **Product Data** | Immutably preserved; zero modification | High |
| **Cluj Demonstrator Data** | Data (`data/`) | Product Scientific Data | `data/cluj_combined_unique_150.geojson` | *None* | **Product Data** | Immutably preserved; benchmark demonstrator | High |
| **Closed-Loop Orchestrator** | AI (`ai/closed_loop.py`)| Dev SDK | `stratum_ro/ai/closed_loop.py` | *None* | **Dev SDK** | Keep; orchestrates test/Kilo audit pipeline | Low |
| **Dev API Runner Script** | Scripts (`scripts/`) | Dev SDK | `scripts/run_agent_with_custom_api.py` | *None* | **Dev SDK** | Keep; developer utility script | Low |
| **Project Validator Script** | Scripts (`scripts/`) | Both (Split Concern) | `scripts/validate_project.py` | *None* | **Both** | Split: CRS check (Product) / AI health (SDK) | Low |
