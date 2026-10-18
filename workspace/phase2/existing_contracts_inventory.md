# STRATUMRO — EXISTING CONTRACTS INVENTORY

**Project:** StratumRO Industrial-Grade Geomatics & GeoAI Platform  
**Phase:** Phase 2 — Formal Contracts & Compatibility Boundaries  
**Total Existing Contracts/Data Models Found:** 46  

---

## 1. INVENTORY OVERVIEW

Înainte de a defini noi contracte formale, s-a scanat întregul codebase `stratum_ro/` pentru a inventaria toate clasele de bază (ABCs), modelele Pydantic, dataclass-urile, enumerările și structurile de specificație existente.

| Modul | Clasă / Contract | Baze Moștenite | Decoratori | Linie | Descriere |
| :--- | :--- | :--- | :--- | :---: | :--- |
| `stratum_ro/ai/closed_loop.py` | **`TestResults`** | `None` | `dataclass` | 28 | Fără docstring |
| `stratum_ro/ai/closed_loop.py` | **`QGISLiveStatus`** | `None` | `dataclass` | 39 | Fără docstring |
| `stratum_ro/ai/closed_loop.py` | **`ProviderVerification`** | `None` | `dataclass` | 49 | Fără docstring |
| `stratum_ro/ai/closed_loop.py` | **`KiloAuditResult`** | `None` | `dataclass` | 59 | Fără docstring |
| `stratum_ro/ai/closed_loop.py` | **`ClosedLoopReport`** | `None` | `dataclass` | 70 | Fără docstring |
| `stratum_ro/ai/context.py` | **`ResourceSnapshot`** | `None` | `dataclass` | 127 | Hardware, network, socket, and runtime resource availability |
| `stratum_ro/ai/context.py` | **`ProjectContext`** | `None` | `dataclass` | 185 | Backward-compatible Project Context configuration container. |
| `stratum_ro/ai/data_profiler.py` | **`ValidationLevel`** | `str, Enum` | `None` | 21 | Fără docstring |
| `stratum_ro/ai/data_profiler.py` | **`ValidationReport`** | `None` | `dataclass` | 31 | Fără docstring |
| `stratum_ro/ai/events.py` | **`EventType`** | `str, Enum` | `None` | 15 | Fără docstring |
| `stratum_ro/ai/events.py` | **`Event`** | `None` | `dataclass` | 40 | Fără docstring |
| `stratum_ro/ai/provenance.py` | **`EvidenceClass`** | `str, Enum` | `None` | 17 | Fără docstring |
| `stratum_ro/ai/provenance.py` | **`ProvenanceRecord`** | `None` | `dataclass` | 29 | Fără docstring |
| `stratum_ro/ai/providers/base.py` | **`ProviderCapability`** | `str, Enum` | `None` | 18 | Fără docstring |
| `stratum_ro/ai/providers/base.py` | **`ProviderResponse`** | `None` | `dataclass` | 27 | Fără docstring |
| `stratum_ro/ai/providers/base.py` | **`BaseAIProvider`** | `ABC` | `None` | 96 | Abstract contract for model providers in StratumRO. |
| `stratum_ro/ai/providers/local_provider.py` | **`LocalProvider`** | `BaseAIProvider` | `None` | 14 | Guaranteed local provider with deterministic mock templates. |
| `stratum_ro/ai/providers/nvidia_nim_provider.py` | **`NvidiaNIMProvider`** | `BaseAIProvider` | `None` | 13 | NVIDIA NIM inference provider using OpenAI-compatible REST e |
| `stratum_ro/ai/providers/ollama_provider.py` | **`OllamaProvider`** | `BaseAIProvider` | `None` | 14 | Local Ollama inference provider. |
| `stratum_ro/ai/providers/openai_provider.py` | **`OpenAIProvider`** | `BaseAIProvider` | `None` | 13 | OpenAI Platform provider for advanced reasoning and multi-st |
| `stratum_ro/ai/providers/union_alpha_provider.py` | **`UnionAlphaProvider`** | `BaseAIProvider` | `None` | 14 | Union Alpha provider via OpenRouter endpoint. |
| `stratum_ro/ai/registry.py` | **`CapabilityMatch`** | `None` | `dataclass` | 19 | Resolved provider mapping for a specific capability requirem |
| `stratum_ro/ai/risk.py` | **`ActionRiskLevel`** | `str, Enum` | `None` | 18 | Fără docstring |
| `stratum_ro/ai/risk.py` | **`RiskDecisionType`** | `str, Enum` | `None` | 26 | Fără docstring |
| `stratum_ro/ai/risk.py` | **`RiskDecision`** | `None` | `dataclass` | 33 | Fără docstring |
| `stratum_ro/ai/router.py` | **`TaskType`** | `str, Enum` | `None` | 16 | Fără docstring |
| `stratum_ro/ai/router.py` | **`ExecutionMode`** | `str, Enum` | `None` | 33 | Fără docstring |
| `stratum_ro/ai/router.py` | **`RoutingDecision`** | `None` | `dataclass` | 41 | Fără docstring |
| `stratum_ro/ai/task_graph.py` | **`TaskStatus`** | `str, Enum` | `None` | 18 | Fără docstring |
| `stratum_ro/ai/task_graph.py` | **`TaskNode`** | `None` | `dataclass` | 68 | Fără docstring |
| `stratum_ro/ai/task_spec.py` | **`RiskTolerance`** | `str, Enum` | `None` | 17 | Fără docstring |
| `stratum_ro/ai/task_spec.py` | **`WorkflowMode`** | `str, Enum` | `None` | 24 | Fără docstring |
| `stratum_ro/ai/task_spec.py` | **`DeliverableType`** | `str, Enum` | `None` | 39 | Fără docstring |
| `stratum_ro/ai/task_spec.py` | **`TaskSpec`** | `None` | `dataclass` | 50 | Authoritative specification for an executable StratumRO work |
| `stratum_ro/ai/tools/security.py` | **`PermissionClass`** | `str, Enum` | `None` | 29 | Fără docstring |
| `stratum_ro/ai/vlm_verifier.py` | **`VLMVerificationResult`** | `None` | `dataclass` | 27 | Fără docstring |
| `stratum_ro/api/app.py` | **`WorkflowRunRequest`** | `BaseModel` | `None` | 55 | Fără docstring |
| `stratum_ro/api/app.py` | **`ZoomRequest`** | `BaseModel` | `None` | 63 | Fără docstring |
| `stratum_ro/api/app.py` | **`KiloReviewRequest`** | `BaseModel` | `None` | 67 | Fără docstring |
| `stratum_ro/dataset_resolver.py` | **`DatasetMetadata`** | `None` | `dataclass` | 23 | Fără docstring |
| `stratum_ro/simulation/perturbation.py` | **`PerturbationConfig`** | `None` | `dataclass` | 17 | Fără docstring |
| `stratum_ro/stratum_ro_dockwidget.py` | **`StratumRODockWidget`** | `QtWidgets.QDockWidget, Ui_StratumRODockWidgetBase` | `None` | 279 | Fără docstring |
| `stratum_ro/stratum_ro_dockwidget_base.py` | **`Ui_StratumRODockWidgetBase`** | `object` | `None` | 6 | Fără docstring |
| `stratum_ro/test/test_task_spec.py` | **`TestTaskSpec`** | `unittest.TestCase` | `None` | 18 | Fără docstring |
| `stratum_ro/test/test_task_spec.py` | **`TestCapabilityResolution`** | `unittest.TestCase` | `None` | 125 | Fără docstring |
| `stratum_ro/test/test_vlm_verifier.py` | **`MockMultimodalProvider`** | `BaseAIProvider` | `None` | 26 | Fără docstring |

---

## 2. CATEGORIZAREA CONTRACTELOR EXISTENTE

### 2.1 AI & Task Orchestration
- `stratum_ro/ai/task_spec.py`: `TaskSpec`, `TaskType` (Enum), `TaskStatus` (Enum), `ExecutionMode` (Enum), `CapabilityMatch`.
- `stratum_ro/ai/task_graph.py`: `TaskNode`, `TaskGraph`.
- `stratum_ro/ai/providers/base.py`: `BaseAIProvider` (ABC).
- `stratum_ro/ai/registry.py`: `ProviderRegistry`, `CapabilityRegistry`.
- `stratum_ro/ai/risk.py`: `RiskPolicy` (ABC), `RiskAssessment`, `RiskLevel` (Enum).
- `stratum_ro/ai/provenance.py`: `ProvenanceChain`, `ProvenanceRecord`.
- `stratum_ro/ai/data_profiler.py`: `QualityReport`, `QualityLevel` (Enum).

### 2.2 Geodesy & Geometry
- `stratum_ro/vectorizer.py`: `CadastralVectorizer` (clasa principală cu API implicit).
- `stratum_ro/cad_exporter.py`: `CadExporter` (API implicit pentru TopoLT CAD și .CP).
- `stratum_ro/volumetric_3d.py`: `Volumetric3D` (LoD1 extrusion și CityJSON v1.1).

### 2.3 API & Web Service
- `stratum_ro/api/service.py`: `PlatformService`.
- `stratum_ro/api/app.py`: Endpoint-uri FastAPI cu modele Pydantic de cerere/răspuns.

---

## 3. CE LIPSEȘTE ȘI TREBUIE FORMALIZAT ÎN FAZA 2

Deși stratul AI (`stratum_ro/ai/`) are contracte Pydantic și Enum-uri bine definite (`TaskSpec`, `RiskAssessment`), **nucleul geospațial și pachetele de domeniu duc lipsă de contracte formale**:
1. **`CommonGeoObject`**: Nu există un contract unificat pentru reprezentarea obiectelor spațiale vectoriale (geometrie + CRS + atribute + proveniență).
2. **`IGeometryEngine`**: Operațiile pe poligoane (regularizare 90°, validare GEOS, snapping) nu sunt legate printr-un Protocol sau ABC formal.
3. **`ICRSManager` & `ITransformer`**: Transformările de coordonate sunt apelate ad-hoc prin PyPROJ fără un contract cu validare a axelor și metadatelor.
4. **`BaseDomainPack` & `DomainCapability`**: Nu există o clasă de bază abstractă pentru Domain Packs (`cadastre_ro`, `topography`, `city_3d`).
5. **`IVisionEngine`**: SAM 2 nu are o interfață dedicată separată de furnizorii de text LLM.
6. **`IValidator`**: Porțile de validare (L0-L5) nu implementează o interfață comună de raportare.
7. **`IProvenanceRecorder`**: Contract abstract pentru audit trail W3C PROV-O.
8. **`IQgisAdapter` & `ILegacyAdapter`**: Granițe clare de compatibilitate pentru clienți.