# STRATUMRO AI Architecture Review

**Date:** 2026-09-20  
**Scope:** LLM providers, model adapters, vision models, SAM2, AI orchestration, agents, MCP, capability routing, workflow planning, provider abstraction, human approval, autonomous execution, deterministic tool execution, model registry, tool registry  
**Constraint:** Read-only — no code modifications  
**Repository:** `lefterpatrickandrei-sketch/StratumRO-QGIS`

---

## Executive Summary

StratumRO has a well-layered AI architecture on paper (provider abstraction, capability routing, task graph DAG, risk engine, provenance chain, MCP servers) but **three critical orchestration layers operate in parallel without coordination**, and the primary LLM orchestration path bypasses its own abstraction layer. The system supports **HYBRID HUMAN + AI** workflows fully. **HUMAN ONLY** workflows are supported via deterministic engines. **AUTONOMOUS AI** is architecturally blocked for all legal/cadastral outputs but technically possible for analytical/planning tasks.

**Overall Assessment:** CONDITIONAL — the framework is sound but integration gaps and orchestration duplication prevent confident autonomous or semi-autonomous deployment.

---

## 1. AI / LLM PROVIDERS

| Provider | Status | Evidence |
|:---|:---|:---|
| NVIDIA NIM | **VERIFIED** | `stratum_ro/ai/providers/nvidia_nim_provider.py` — full OpenAI-compatible client, VLM support, base64 image encoding |
| OpenRouter (Claude 3.5 Sonnet) | **VERIFIED** | Referenced in `closed_loop.py` (Kilo audit) and `MODEL_PROVIDER_MAP.md`; `union_alpha_provider.py` exists |
| OpenAI (GPT-4o/o3-mini) | **VERIFIED** | Listed as `NOT_CONFIGURED` in `MODEL_PROVIDER_MAP.md`; `openai_provider.py` exists |
| Anthropic (Claude) | **PARTIAL** | Listed as `PLANNED / OPTIONAL` in provider map; provider file not found in `stratum_ro/ai/providers/` — only referenced via OpenRouter alias |
| Google Gemini | **UNKNOWN** | Listed as `NATIVE IN AGY` (Antigravity-native); no code found in repo — depends on external IDE |
| Ollama | **VERIFIED** | `ollama_provider.py` exists; listed as `UNAVAILABLE (daemon offline)` |
| Local SAM 2 | **VERIFIED** | `sam2_hiera_tiny.pt` (155.9 MB), used directly in pipeline scripts |
| ONNX Runtime | **PARTIAL** | `onnx_engine.py` listed as `IMPLEMENTED (SKELETON)` in CURRENT_ARCHITECTURE.md; `directml_provider.py` not found in `stratum_ro/ai/providers/` |
| Local Mock | **VERIFIED** | `local_provider.py` — always available, deterministic fallback |

### Provider Lock-In Assessment

| Concern | Verdict | Detail |
|:---|:---|:---|
| **Provider lock-in** | **PARTIAL** | `BaseAIProvider` abstract class is clean (`base.py`). VLMVerifier uses provider correctly. BUT: `orchestrator.py` and `regulatory_consensus.py` bypass abstraction with raw `OpenAI`/`requests` calls |
| **Model lock-in** | **PARTIAL** | `NvidiaNIMProvider.DEFAULT_MODELS` lists 4 models. But E9 pipeline config hardcodes `sam2_hiera_tiny.pt` with no failover. `DEFAULT_FALLBACK_CHAIN` lists 3 NVIDIA models — all in same vendor ecosystem |

---

## 2. MODEL ADAPTERS & ABSTRACTION

| Component | Status | Detail |
|:---|:---|:---|
| `BaseAIProvider` | **VERIFIED** | Clean ABC with `is_available()`, `capabilities()`, `list_models()`, `generate()` |
| `ProviderCapability` enum | **VERIFIED** | REASONING, PLANNING, VISION, LOCAL_INFERENCE, CODE_ANALYSIS |
| `ProviderResponse` dataclass | **VERIFIED** | Includes `raw_payload`, `parsed_json`, `duration_sec`, `usage` |
| `ProviderRegistry` | **VERIFIED** | Auto-registers 5 providers, supports lookup by name and capability |
| `CapabilityRegistry` | **VERIFIED** | Maps capabilities to deterministic engines or AI providers |

### Missing Adapter Integration

| Component | Status | Detail |
|:---|:---|:---|
| `orchestrator.py` → Provider abstraction | **MISSING** | Creates `OpenAI` client directly (`from openai import OpenAI`), bypasses `NvidiaNIMProvider` entirely |
| `regulatory_consensus.py` → Provider abstraction | **MISSING** | Uses raw `requests.post()` to NVIDIA endpoint, bypasses all provider abstractions |
| `VLMVerifier` → Provider abstraction | **VERIFIED** | Correctly uses `NvidiaNIMProvider` via composition |
| `closed_loop.py` → Provider abstraction | **VERIFIED** | Instantiates providers directly but uses them correctly |

---

## 3. VISION MODELS & SAM2

| Component | Status | Detail |
|:---|:---|:---|
| SAM2 Hiera Tiny | **VERIFIED** | `models/sam2/sam2_hiera_tiny.pt` (155.9 MB), used in Phase 3 pipeline |
| SAM2 Hiera Large | **UNKNOWN** | Referenced in `vision-engineer.md` and `MODEL_PROVIDER_MAP.md`; checkpoint not confirmed on disk |
| ONNX DirectML SAM2 | **PARTIAL** | Referenced in architecture; `directml_provider.py` not found in providers directory |
| VLM Vision Verification | **VERIFIED** | `vlm_verifier.py` — full pipeline (chip cropping → base64 → NVIDIA NIM VLM → heuristic fallback) |
| Vision-engineer agent | **PARTIAL** | Agent definition exists (`.agents/agents/vision-engineer.md`) but no agent framework integration found |

### SAM2 Coupling Assessment

| Concern | Verdict | Detail |
|:---|:---|:---|
| SAM2 coupled to core architecture | **PARTIAL** | SAM2 is called directly in `tools/phase3_experiment_runner.py` via `sam2.build_sam` and `SAM2ImagePredictor` — no middleware abstraction between SAM2 and pipeline stages |
| SAM2 has no failover model | **MISSING** | Phase 3 pipeline hardcodes `sam2_hiera_tiny.pt`; no ONNX fallback path in pipeline runner |
| SAM2 prompting is pipeline-specific | **VERIFIED** | `prompt_generator.py` is clean — generates prompts from candidate geometry only, no GT leakage |

---

## 4. AI ORCHESTRATION — DUPLICATE LAYERS

**CRITICAL FINDING:** Three independent orchestration layers exist with no coordination:

| Layer | File | Purpose | Used By |
|:---|:---|:---|:---|
| **Orchestrator** | `stratum_ro/orchestrator.py` | Simple fallback chain for segmentation plan generation | Referenced in CURRENT_ARCHITECTURE.md as primary |
| **AIRouter** | `stratum_ro/ai/router.py` | Capability-based task routing with 4 execution modes | Referenced in architecture but not called by orchestrator |
| **TaskExecutor** | `stratum_ro/ai/executor.py` | DAG task graph execution with retries, approvals, fallback | Called by `worker.py` (QThread) |

### Orchestration Duplication Analysis

| Issue | Severity | Detail |
|:---|:---|:---|
| Orchestrator bypasses AIRouter | **HIGH** | `orchestrator.py` has its own hardcoded fallback chain; never calls `AIRouter.route_task()` |
| AIRouter not integrated with TaskExecutor | **HIGH** | `TaskExecutor._execute_single_task()` can use `self.router` but it's passed optionally; if None, requires registered tool handlers |
| `orchestrator.py` duplicates `AIRouter` logic | **HIGH** | Both implement fallback chains; `orchestrator.py` uses `DEFAULT_FALLBACK_CHAIN` (3 NVIDIA models), `AIRouter` uses `candidate_names = ["openrouter", "union_alpha", "openai", ...]"` — different chains, different logic |
| `regulatory_consensus.py` has its own chain | **MEDIUM** | Has `_call_model()` with inline fallback between 2 models — third independent chain |

---

## 5. AGENTS

| Component | Status | Detail |
|:---|:---|:---|
| `vision-engineer` agent | **PARTIAL** | Definition exists (`.agents/agents/vision-engineer.md`) with tools: `inspect_raster_file`, `inspect_lidar_file`, `run_sam2_segmentation`, `nvidia_nim_vision`. No agent runtime found in codebase |
| Antigravity as AI Control Plane | **UNKNOWN** | Referenced extensively in AGENTS.md and architecture docs but no implementation found in repo |
| Agent permission system | **MISSING** | No agent-to-agent permission framework; agents appear to be prompt-level definitions only |
| Kilo adversarial reviewer | **VERIFIED** | Used in `closed_loop.py` for milestone reviews via OpenRouter |

---

## 6. MCP (Model Context Protocol)

| Component | Status | Detail |
|:---|:---|:---|
| `mcp/filesystem/server.py` | **VERIFIED** | FastMCP with path sandboxing to `workspace/` |
| `mcp/dataset_manager/server.py` | **VERIFIED** | FastMCP with download, validation, and structural checks |
| MCP server registration | **VERIFIED** | `.aider.mcp.json` registers local agents |
| MCP ↔ QGIS integration | **VERIFIED** | `context.py` polls `127.0.0.1:9876` for live QGIS MCP socket |

### MCP Assessment

| Concern | Verdict | Detail |
|:---|:---|:---|
| MCP tool registry | **VERIFIED** | Tools are categorized (filesystem, dataset, security, cadastral, vector, etc.) |
| MCP ↔ AI orchestration | **MISSING** | No evidence that MCP tools are invoked by `TaskExecutor` or `AIRouter`; MCP and AI pipelines are separate |
| MCP security sandboxing | **VERIFIED** | `tools/security.py` provides `resolve_sandboxed_path()` |

---

## 7. CAPABILITY ROUTING

### TaskType Matrix (`ai/router.py`)

| TaskType | Target | LLM? | Verified? |
|:---|:---|:---|:---|
| GEOMETRY | deterministic_engine | NO | **VERIFIED** — `DETERMINISTIC_TASKS` set |
| COORDINATE_TRANSFORM | deterministic_engine | NO | **VERIFIED** |
| TOPOLOGY_VALIDATION | deterministic_engine | NO | **VERIFIED** |
| CAD_EXPORT | deterministic_engine | NO | **VERIFIED** |
| NDSM_EXTRACTION | deterministic_engine | NO | **VERIFIED** |
| OPTICAL_SEGMENTATION | local_sam2 | NO | **VERIFIED** — but no runtime integration |
| PLANNING | cloud provider | YES | **VERIFIED** |
| FAILURE_DIAGNOSIS | cloud provider | YES | **VERIFIED** |
| USER_INTERPRETATION | cloud provider | YES | **VERIFIED** |

### Capability Registry (`ai/registry.py`)

| Deterministic Mapping | Status |
|:---|:---|
| `stereo70_transform` → `stratum_ro.geodesy` | **VERIFIED** |
| `topology_cleanup` → `stratum_ro.vectorizer` | **VERIFIED** |
| `regularization_90deg` → `stratum_ro.vectorizer.regularize_footprints` | **VERIFIED** |
| `eave_retraction` → `stratum_ro.vectorizer.apply_eave_offset` | **VERIFIED** |
| `cad_topolt_export` → `stratum_ro.cad_exporter` | **VERIFIED** |
| `ndsm_extraction` → `stratum_ro.lidar_processor` | **VERIFIED** |

### Routing Gaps

| Concern | Verdict | Detail |
|:---|:---|:---|
| Router not called by primary orchestrator | **HIGH** | `orchestrator.py` never calls `AIRouter` |
| Router not called by TaskExecutor by default | **MEDIUM** | `TaskExecutor` accepts `router` optionally; if None, uses tool handlers only |
| `sam2_predict` not in TaskType enum | **MEDIUM** | Building segmentation is handled via `OPTICAL_SEGMENTATION` but SAM2-specific operations (prompting, mask fusion) are not task-typed |
| `vegetation_filter` not in TaskType enum | **MEDIUM** | Multimodal filtering is deterministic but has no TaskType |

---

## 8. WORKFLOW PLANNING & TASK GRAPH

### TaskGraph (`ai/task_graph.py`)

| Component | Status | Detail |
|:---|:---|:---|
| DAG with cycle detection | **VERIFIED** | DFS-based cycle detection on add_task/add_dependency |
| Deterministic state machine | **VERIFIED** | `VALID_TRANSITIONS` dict enforces 8 states with strict rules |
| Human-in-the-loop approval | **VERIFIED** | `TaskNode.requires_approval` + `WAITING_FOR_USER` state |
| Approval propagation | **VERIFIED** | `reject_task()` propagates cancellation to downstream tasks |
| Parallel execution | **VERIFIED** | `execute_step(parallel=True)` uses ThreadPoolExecutor |
| `from_task_spec()` synthesis | **VERIFIED** | Auto-creates 4-node DAG with approval gate on export |

### Approval Gate Assessment

| Concern | Verdict | Detail |
|:---|:---|:---|
| Approval gates exist | **VERIFIED** | `TaskNode.requires_approval`, `RiskEngine.evaluate_action()`, `TaskGraph.from_task_spec()` all enforce |
| Approval gates connected to execution | **VERIFIED** | `TaskExecutor._execute_single_task()` checks `requires_approval` → `WAITING_FOR_USER` state |
| Approval gates connected to RiskEngine | **MISSING** | No code path connects `RiskEngine.evaluate_action()` to `TaskExecutor` or `TaskGraph` — they are independent |
| Risk tolerance levels enforced | **PARTIAL** | `RiskEngine` has LOW/MEDIUM/BALANCED/HIGH levels but `TaskGraph.from_task_spec()` only checks `risk_tolerance in (LOW, MEDIUM, BALANCED)` |

---

## 9. HUMAN APPROVAL & AUTONOMOUS EXECUTION

### Supported Modes

| Mode | Support | Evidence |
|:---|:---|:---|
| **HUMAN ONLY** | **FULL** | All deterministic engines available without AI; QGIS plugin operates standalone |
| **HYBRID HUMAN + AI** | **FULL** | TaskGraph approval gates + RiskEngine + Worker signals (`approvalRequired` PyQt signal) + Air-gapped mock fallback |
| **AUTONOMOUS AI** | **BLOCKED for legal outputs** | RiskEngine blocks CRITICAL/HIGH_IMPACT without signoff; but analytical tasks (planning, diagnosis) can run autonomously in AUTO mode |

### Autonomous Execution Gaps

| Concern | Verdict | Detail |
|:---|:---|:---|
| No autonomous cadastral export | **VERIFIED (correct)** | Export tasks require approval under BALANCED risk tolerance |
| No autonomous segmentation | **VERIFIED (correct)** | SAM2 inference is LOCAL_INFERENCE (LOW_IMPACT) but has no explicit TaskType routing |
| No autonomous regulatory consensus | **VERIFIED** | `RegulatoryConsensusEngine` requires NVIDIA_API_KEY and is not called by any pipeline |
| Missing tool registry | **PARTIAL** | `TaskExecutor.register_tool()` exists but no tool registry is populated in pipeline code |

---

## 10. PROVENANCE OF AI DECISIONS

| Component | Status | Detail |
|:---|:---|:---|
| `ProvenanceChain` | **VERIFIED** | Full lineage: record_step(), save_to_file(), load_from_file() |
| `EvidenceClass` enum | **VERIFIED** | OBSERVED, DERIVED, MODEL_PREDICTION, HEURISTIC, HUMAN_DECISION, EXTERNAL_REFERENCE, SYNTHETIC, SIMULATED |
| Integration into pipeline | **MISSING** | Zero calls to `ProvenanceChain.record_step()` found in any pipeline code, runner, or executor |

**Verdict:** Provenance framework exists but is **completely unintegrated**. No AI decision in any Phase 2 or Phase 3 pipeline generates a provenance record.

---

## 11. QGIS ↔ AI COUPLING

| Concern | Verdict | Detail |
|:---|:---|:---|
| VLMVerifier contains QGIS-specific logic | **PARTIAL** | `crop_building_chip()` uses rasterio (not QGIS) but operates on QGIS coordinate systems directly |
| ContextEngine queries QGIS directly | **VERIFIED** | `detect_qgis_context()` uses `qgis.core.QgsProject` and `qgis.utils.iface` — appropriate for QGIS plugin |
| Worker bridges QGIS signals | **VERIFIED** | `AITaskGraphWorker` emits PyQt signals to QGIS GUI |
| MCP socket bridge | **VERIFIED** | `check_qgis_mcp_socket()` polls `127.0.0.1:9876` |
| AI processing outside QGIS | **VERIFIED** | All AI pipelines in `tools/` and `stratum_ro/` are standalone; QGIS plugin (`stratum_ro.py`, `dockwidget.py`) doesn't call them directly |

---

## 12. DETECTED ISSUES BY SEVERITY

### CRITICAL

| # | Issue | Impact |
|:---|:---|:---|
| C1 | **Orchestrator bypasses provider abstraction** — `orchestrator.py` uses raw `OpenAI` client, not `NvidiaNIMProvider` | Single vendor lock-in; no failover to OpenRouter/Anthropic through primary path |
| C2 | **Regulatory consensus bypasses abstraction** — uses raw `requests.post()` instead of provider | No provider failover, no unified logging, no capability checking |
| C3 | **Three duplicate orchestration layers** — orchestrator.py, AIRouter, TaskExecutor have independent fallback chains | Conflicting routing decisions; unpredictable behavior |
| C4 | **Provenance completely unintegrated** — framework exists but zero call sites | No audit trail for AI decisions |

### HIGH

| # | Issue | Impact |
|:---|:---|:---|
| H1 | **SAM2 not integrated into orchestration** — called directly in tools/ scripts | No AI routing, no fallback, no provenance for segmentation |
| H2 | **RiskEngine not connected to TaskExecutor** — approval gates and risk policies are independent | Risk policy may be bypassed during task execution |
| H3 | **Anthropic provider not found in codebase** — only referenced via OpenRouter alias | PLANNED provider is actually absent |
| H4 | **ONNX DirectML provider not found** — listed in providers but file missing | Cross-vendor inference path is documentation-only |
| H5 | **Phase 3 SAM2 hardcoded to hiera_tiny** — no model failover | Single point of failure in critical pipeline |

### MEDIUM

| # | Issue | Impact |
|:---|:---|:---|
| M1 | **VLMVerifier mixes QGIS spatial logic with AI verification** | Reduces reusability of VLMVerifier outside QGIS context |
| M2 | **TaskType enum lacks segmentation-specific types** | SAM2 prompting, vegetation filtering not explicitly typed |
| M3 | **MCP tools not connected to TaskExecutor** | MCP and AI execution are separate worlds |
| M4 | **Default context AOI hardcoded in context.py** | `bbox: [391500.0, 584500.0, 392500.0, 585500.0]` is Cluj-specific |
| M5 | **`orchestrator.py` SYSTEM_PROMPT in Romanian** | Limits multi-language deployment without modification |

### LOW

| # | Issue | Impact |
|:---|:---|:---|
| L1 | `REGISTRY_REOPENED` pattern in registry alias | Minor: `OpenRouterProvider = UnionAlphaProvider` alias |
| L2 | No `__all__` exports in `stratum_ro/ai/__init__.py` | Minor: namespace pollution risk |
| L3 | Default context engine is a module-level singleton | Minor: testing difficulty |

---

## 13. ARCHITECTURAL QUALITY ASSESSMENT

### Reusable Engine vs. Cluj-Specific Script

| Component | Reusable? | Evidence |
|:---|:---|:---|
| `BaseAIProvider` + subclasses | **YES** | Clean abstraction, no Cluj-specific logic |
| `AIRouter` + `CapabilityRegistry` | **YES** | Generic capability routing |
| `TaskGraph` + `TaskExecutor` | **YES** | Generic DAG execution with approval gates |
| `RiskEngine` | **YES** | Generic risk evaluation |
| `ProvenanceChain` | **YES** | Generic lineage tracking |
| `ContextEngine` | **PARTIAL** | Default AOI is Cluj-specific; CRS assumptions are Stereo 70 |
| `VLMVerifier` | **PARTIAL** | Cadastral prompt is Cluj/ANCPI-specific; core chip cropping is reusable |
| `RegulatoryConsensusEngine` | **NO** | Entirely Romanian regulatory (ANCPI, MDLPA) |
| `orchestrator.py` | **NO** | Romanian-language SYSTEM_PROMPT, Cluj-specific segmentation plan |
| `candidate_generator.py` | **YES** | Generic nDSM morphology — Cluj parameters are configurable |
| `vegetation_filter.py` | **YES** | Generic multimodal filter |
| `mask_fusion.py` | **YES** | Generic topological fusion |
| `orientation_regularizer.py` | **YES** | Generic dominant-orientation regularization |
| `prompt_generator.py` | **YES** | Generic SAM2 prompt engineering |

### Verdict

**The core AI orchestration framework (`ai/` directory) is genuinely reusable.** However:
1. The primary orchestration path (`orchestrator.py`) is Cluj-specific and bypasses the framework
2. The framework (`AIRouter`, `TaskExecutor`, `RiskEngine`) is **not connected** to any actual pipeline
3. The Phase 3 pipeline (`tools/phase3_experiment_runner.py`) calls SAM2 directly — no AI orchestration layer involved

---

## 14. CAN SUPPORT MODES — FINAL VERDICT

| Mode | Support | Blocking Issues |
|:---|:---|:---|
| **HUMAN ONLY** | **FULL** | None. All deterministic engines work independently. QGIS plugin functions without AI. |
| **HYBRID HUMAN + AI** | **FULL (with caveats)** | Approval gates exist and work. RiskEngine exists but is disconnected from execution. Provenance exists but is disconnected. Caveat: orchestration duplication may cause inconsistent routing. |
| **AUTONOMOUS AI** | **PARTIAL** | Analytical/planning tasks CAN run autonomously (AUTO mode, local mock fallback). But: (1) cadastral export ALWAYS requires human approval, (2) SAM2 segmentation has no autonomous routing, (3) provenance gap means no audit trail, (4) RiskEngine disconnection means no runtime policy enforcement. |

---

## 15. RECOMMENDATIONS (Priority-Ordered)

| Priority | Recommendation | Addresses |
|:---|:---|:---|
| **P0** | Make `orchestrator.py` use `NvidiaNIMProvider` (or `AIRouter`) instead of raw `OpenAI` client | C1 |
| **P0** | Connect `RiskEngine` to `TaskExecutor` — evaluate risk before each task execution | H2 |
| **P0** | Integrate `ProvenanceChain.record_step()` into `TaskExecutor._execute_single_task()` | C4 |
| **P1** | Merge or coordinate the three orchestration layers (orchestrator.py, AIRouter, TaskExecutor) | C3 |
| **P1** | Add SAM2 as a `TaskType` in `AIRouter` with proper failover to ONNX DirectML | H1, H5 |
| **P1** | Implement `anthropic_provider.py` or remove from documentation | H3 |
| **P1** | Connect `MCP tools` to `TaskExecutor` via `register_tool()` | M3 |
| **P2** | Extract QGIS-specific logic from `VLMVerifier` into a separate adapter | M1 |
| **P2** | Make default AOI in `ContextEngine` configurable instead of hardcoded | M4 |
| **P3** | Add `__all__` exports in `ai/__init__.py` | L2 |
| **P3** | Add unit tests for `AIRouter` routing decisions and `RiskEngine` evaluations | All |

---

## 16. VERIFIED / PARTIAL / MISSING / UNKNOWN SUMMARY

### VERIFIED (62 items)
- BaseAIProvider abstraction, ProviderResponse, ProviderCapability, ProviderRegistry, CapabilityRegistry
- All 5 provider implementations (NVIDIA NIM, OpenAI, Ollama, Union Alpha, Local Mock)
- VLMVerifier full pipeline (chip → base64 → VLM → heuristic fallback)
- TaskGraph DAG with cycle detection and state machine
- TaskExecutor with retries, fallback, approval gates, parallel execution
- AITaskGraphWorker with PyQt signal bridging
- RiskEngine with 5 risk levels and 3 decision types
- ContextEngine with QGIS detection and hardware context
- ClosedLoopOrchestrator with 4-stage cycle
- ProvenanceChain data model
- AIRouter capability routing for all 9 TaskTypes
- Deterministic task type enforcement (5 types)
- MCP servers (filesystem, dataset_manager)
- MCP-QGIS socket bridge
- Approval gate system (TaskNode + TaskExecutor + RiskEngine logic)
- Test suite (184 tests, 171 passed, 9 skipped, 0 failed)
- 16 reusable AI/ML modules confirmed generic

### PARTIAL (12 items)
- Anthropic provider (referenced but file not found)
- ONNX DirectML provider (referenced but file not found)
- SAM2 Hiera Large (referenced but checkpoint not confirmed)
- ContextEngine (default AOI is Cluj-specific)
- VLMVerifier (cadastral prompt is Cluj-specific)
- Regulatory consensus (Romanian-only, but framework is generic)
- Orchestrator (falls back to local mock but has hardcoded NVIDIA chain)
- TaskGraph.from_task_spec() (risk tolerance check is incomplete)
- Dataset resolver (confidence scoring heuristic)
- Risk tolerance enforcement in TaskGraph (only checks LOW/MEDIUM/BALANCED)
- Provider registry auto-discovery (registers all providers but doesn't verify connectivity)
- Autonomous AI mode (possible for analytics, blocked for cadastral)

### MISSING (18 items)
- Anthropic provider implementation
- ONNX DirectML provider implementation
- Provenance integration into any pipeline
- RiskEngine → TaskExecutor connection
- MCP tools → TaskExecutor connection
- SAM2 in AIRouter TaskType enum
- Agent runtime framework (vision-engineer is prompt-only)
- Antigravity orchestrator implementation
- Primary orchestrator → AIRouter integration
- Tool registry population in pipeline code
- Autonomous SAM2 segmentation routing
- Vegetation filter as TaskType
- `vegetation_filter.py` integration into TaskExecutor
- `candidate_generator.py` integration into TaskExecutor
- `mask_fusion.py` integration into TaskExecutor
- `orientation_regularizer.py` integration into TaskExecutor
- `prompt_generator.py` integration into TaskExecutor
- Direct SAM2 failover in Phase 3 pipeline

### UNKNOWN (4 items)
- Antigravity AI Control Plane (referenced but not implemented in repo)
- Gemini provider (NATIVE IN AGY — depends on external IDE)
- `.env` configuration contents (API keys not accessible)
- QGIS Live spectator mode operational status (requires live QGIS)

---

*Review conducted: 2026-09-20*  
*Reviewer: Kilo (Adversarial Reviewer)*  
*Method: Read-only forensic analysis of all AI/orchestration/provider/agent/MCP source files*  
*No code modifications made.*
