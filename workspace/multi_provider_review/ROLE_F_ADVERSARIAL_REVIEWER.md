<!-- Metadata: Provider=openrouter, Model=meta-llama/llama-3.3-70b-instruct, Duration=18.60s -->

### Verified Facts
The proposed StratumRO architecture has a complex codebase with multiple components, but a closer examination reveals that not all parts are equally functional or well-integrated. 
- **Functional Components**: The core deterministic components (`vectorizer.py`, `cad_exporter.py`, `volumetric_3d.py`, `onnx_engine.py`) and parts of the detection & CV pipeline (`candidate_generator.py`, `vegetation_filter.py`, `mask_fusion.py`, `prompt_generator.py`, `sam2_engine.py`) are implemented and contribute to the system's functionality.
- **Non-Functional or Disconnected Components**: Despite the presence of `ProvenanceChain` and `RiskEngine`, these components lack integration into the operational CAD/GIS execution pipelines, rendering them non-functional in the current setup.
- **Orchestrators and Providers**: The existence of multiple orchestrators (`stratum_ro/orchestrator.py`, `stratum_ro/regulatory_consensus.py`, `stratum_ro/ai/closed_loop.py`, and the combination of `stratum_ro/ai/router.py`, `task_graph.py`, `task_executor.py`) and providers (`BaseAIProvider`, `NvidiaNIMProvider`, `UnionAlphaProvider`, `OpenAIProvider`, `OllamaProvider`, `LocalProvider`) indicates a potential for redundancy and inconsistency.

### The Illusions of Modularity
- **ProvenanceChain and RiskEngine**: These components are unit-tested but have zero call sites in operational pipelines, making them disconnected from the actual workflow. Their presence does not contribute to the system's current functionality.
- **Conflicting Orchestrators**: The coexistence of multiple orchestrators that bypass the `BaseAIProvider` (e.g., `stratum_ro/orchestrator.py` directly calling OpenAI, `stratum_ro/regulatory_consensus.py` directly requesting NVIDIA NIM) undermines the claimed modularity and provider-agnosticism.

### The Provider Lock-in Paradox
- Despite the architecture's claim of provider-agnosticism, the hardcoding of specific providers in certain components (e.g., OpenAI in `orchestrator.py`, NVIDIA in `regulatory_consensus.py`) introduces a paradox. This lock-in contradicts the principle of modularity and flexibility that the architecture aims to achieve.

### The QGIS Monolith Trap
- **Layer Separation Violation**: The `stratum_ro_dockwidget.py` file, with its 1300 lines, directly imports low-level geometric and AI tools, violating the principle of layer separation. This monolithic approach can lead to tight coupling and make maintenance and updates more challenging.

### The 6.15% Recall Reality Check
- The detector's recall of 6.15% indicates that 93.85% of buildings in the scene were missed. Marketing CAD compliance based on such performance could be misleading and does not reflect the system's actual capability in real-world scenarios.

### The Ground Truth & Evaluation Vulnerabilities
- **Overfitting Risk**: The system's performance is primarily evaluated on the Cluj USAMV campus dataset. Without multi-city validation, there's a significant risk of overfitting to this specific environment.
- **Lack of Meaningful Experiments**: Experiments like E5, which do not contribute meaningful insights or improvements, suggest inefficiencies in the evaluation process.

### Critical Failure Modes in Migration
- A hasty refactor into 13 Domain Packs could introduce massive dependency cycles, potentially breaking the QGIS GUI and other components. This could lead to a significant increase in technical debt and make the system more fragile.

### Safety Gates & Autonomous Execution Fallacy
- **Legal and Technical Concerns**: The concept of 'Autonomous AI' in cadastre, without physical RTK verification, poses legal and technical risks. Autonomous execution in such a critical domain requires rigorous safety gates and verifications to ensure accuracy and compliance.

### Adversarial Invariants & Non-Negotiable Preconditions
Before refactoring or touching production code, the following must be proven and frozen:
- **Functional Integrity**: All components must be fully functional and integrated into the workflow.
- **Modularity and Flexibility**: The architecture must demonstrate true provider-agnosticism and modularity.
- **Performance Metrics**: Recall and precision must be significantly improved to reflect real-world capabilities accurately.
- **Ground Truth and Validation**: Multi-city validation and diverse ground truth datasets must be established to ensure the system's generalizability.
- **Safety and Compliance**: Rigorous safety gates, physical verifications, and legal compliance must be ensured for autonomous execution in cadastre.