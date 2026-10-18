# -*- coding: utf-8 -*-
"""
Automated Unit Tests for StratumRO Phase 4 Orchestration Architecture.
Verifies:
  - ContextEngine & ResourceSnapshot
  - CapabilityRegistry & AIRouter delegation
  - TaskGraph generation from TaskSpec with approval gates
  - RiskEngine policy enforcement & secret scrubbing
  - DataProfiler L0-L5 geodetic validation levels
  - ProvenanceChain lineage tracking
  - Simulation PerturbationEngine
"""

import json
import os
import sys
import tempfile
import unittest

from stratum_ro.ai.context import (
    ContextEngine,
    ResourceSnapshot,
    get_resource_snapshot,
)
from stratum_ro.ai.data_profiler import DataProfiler, ValidationLevel
from stratum_ro.ai.provenance import EvidenceClass, ProvenanceChain
from stratum_ro.ai.registry import CapabilityRegistry, ProviderRegistry
from stratum_ro.ai.risk import ActionRiskLevel, RiskDecisionType, RiskEngine
from stratum_ro.ai.router import AIRouter, TaskType
from stratum_ro.ai.task_graph import (
    RiskTolerance,
    TaskGraph,
    TaskGraphStatus,
    TaskNodeStatus,
    TaskSpec,
    WorkflowMode,
)
from stratum_ro.simulation.perturbation import (
    PerturbationConfig,
    PerturbationEngine,
)


class TestPhase4Orchestration(unittest.TestCase):

    def setUp(self):
        self.provider_registry = ProviderRegistry(auto_register=True)
        self.cap_registry = CapabilityRegistry(self.provider_registry)
        self.router = AIRouter(self.provider_registry, self.cap_registry)
        self.risk_engine = RiskEngine()
        self.data_profiler = DataProfiler()

    # 1. Context & Resource Snapshot Tests
    def test_resource_snapshot(self):
        snapshot = get_resource_snapshot()
        self.assertIsInstance(snapshot, ResourceSnapshot)
        self.assertEqual(snapshot.os, sys.platform)
        expected_platform = "windows" if sys.platform.startswith("win") else sys.platform
        self.assertEqual(snapshot.os_platform, expected_platform)
        self.assertGreater(snapshot.cpu_logical_cores, 0)
        # RAM detection is explicitly optional in ResourceSnapshot. A headless
        # platform must report missing evidence rather than require Windows RAM APIs.
        if snapshot.ram_total_mb is not None:
            self.assertGreater(snapshot.ram_total_mb, 0)
        # Verify JSON serializability
        d = snapshot.to_dict()
        self.assertIn("gpu_available", d)
        self.assertIn("ram_available_gb", d)

    def test_context_engine_profile_task(self):
        engine = ContextEngine()
        spec = TaskSpec(
            task_id="test_aoi_01",
            description="Process Cluj AOI",
            inputs={"ortho": "data/test.tif"},
            risk_tolerance=RiskTolerance.BALANCED,
        )
        ctx = engine.profile_task(spec)
        self.assertEqual(ctx["task_id"], "test_aoi_01")
        self.assertEqual(ctx["workflow_mode"], "CADASTRAL_PRECADASTRAL")
        self.assertIn("resource_snapshot", ctx)
        self.assertIn("qgis_mcp_socket_available", ctx)

    # 2. Capability Registry & Router Tests
    def test_deterministic_capability_routing(self):
        """Mathematical/cadastral operations must resolve to local deterministic code."""
        det_caps = [
            "stereo70_transform",
            "topology_cleanup",
            "regularization_90deg",
            "eave_retraction",
            "cad_topolt_export",
            "ndsm_extraction",
        ]
        for cap in det_caps:
            res = self.cap_registry.resolve_capability(cap)
            self.assertEqual(res["type"], "deterministic")
            self.assertFalse(res["is_llm"])
            self.assertTrue(res["available"])

        # Also verify via router
        res_router = self.router.resolve_capability("stereo70_transform")
        self.assertEqual(res_router["type"], "deterministic")

    def test_optical_segmentation_capability_routing(self):
        res = self.cap_registry.resolve_capability("optical_segmentation")
        self.assertEqual(res["type"], "local_model")
        self.assertFalse(res["is_llm"])
        self.assertIn("SAM2", res["target"])

    # 3. TaskGraph from TaskSpec & Approval Gates
    def test_task_graph_from_task_spec_balanced(self):
        spec = TaskSpec(
            task_id="spec_cadastre_balanced",
            description="Run assisted pre-cadastral workflow",
            workflow_mode=WorkflowMode.CADASTRAL_PRECADASTRAL,
            risk_tolerance=RiskTolerance.BALANCED,
        )
        graph = TaskGraph.from_task_spec(spec)
        self.assertEqual(graph.graph_id, "graph_spec_cadastre_balanced")
        node_names = [n.name for n in graph.nodes]
        self.assertIn("profile_data_sources", node_names)
        self.assertIn("building_candidate_segmentation", node_names)
        self.assertIn("vectorization_and_orthogonalization", node_names)
        self.assertIn("export_cad_deliverables", node_names)

        # Under BALANCED risk tolerance, CAD export requires approval gate
        export_node = [n for n in graph.nodes if n.name == "export_cad_deliverables"][0]
        self.assertTrue(export_node.requires_approval)

    def test_task_graph_from_task_spec_high_risk(self):
        spec = TaskSpec(
            task_id="spec_cadastre_high",
            description="Run research automated run",
            workflow_mode=WorkflowMode.CADASTRAL_PRECADASTRAL,
            risk_tolerance=RiskTolerance.HIGH,
        )
        graph = TaskGraph.from_task_spec(spec)
        export_node = [n for n in graph.nodes if n.name == "export_cad_deliverables"][0]
        self.assertFalse(export_node.requires_approval)

    # 4. Risk Engine Tests
    def test_risk_forbidden_command(self):
        decision = self.risk_engine.evaluate_action(
            "run_command",
            {"command": "rmdir /s /q C:\\Windows"},
            risk_tolerance=RiskTolerance.HIGH,
        )
        self.assertEqual(decision.decision, RiskDecisionType.DENY)
        self.assertEqual(decision.risk_level, ActionRiskLevel.CRITICAL)

    def test_risk_ground_truth_protection(self):
        decision = self.risk_engine.evaluate_action(
            "write_file",
            {"TargetFile": "data/ground_truth/tier1_teren.geojson"},
            risk_tolerance=RiskTolerance.HIGH,
        )
        self.assertEqual(decision.decision, RiskDecisionType.DENY)
        self.assertIn("frozen baselines", decision.rationale)

    def test_risk_secret_scrubbing(self):
        raw_text = "Connecting with key sk-abcdef123456789012345678 and nvapi-998877665544332211001122"
        scrubbed = self.risk_engine.scrub_secrets(raw_text)
        self.assertNotIn("sk-abcdef", scrubbed)
        self.assertNotIn("nvapi-9988", scrubbed)
        self.assertIn("[REDACTED_SECRET]", scrubbed)

    # 5. Data Profiler L0-L5 Tests
    def test_data_profiler_l0_to_l4(self):
        # Create a valid Stereo 70 GeoJSON fixture in temp file
        fixture = {
            "type": "FeatureCollection",
            "crs": {"type": "name", "properties": {"name": "EPSG:3844"}},
            "features": [
                {
                    "type": "Feature",
                    "properties": {"cadastral_id": "CAD_001"},
                    "geometry": {
                        "type": "Polygon",
                        "coordinates": [[
                            [391000.0, 585000.0],
                            [391020.0, 585000.0],
                            [391020.0, 585015.0],
                            [391000.0, 585015.0],
                            [391000.0, 585000.0],
                        ]],
                    },
                }
            ],
        }
        with tempfile.NamedTemporaryFile("w", suffix=".geojson", delete=False) as f:
            json.dump(fixture, f)
            temp_path = f.name

        try:
            report = self.data_profiler.profile_vector_file(temp_path, is_field_verified=True)
            self.assertEqual(report.highest_level_passed, ValidationLevel.L5_FIELD_VALIDATED)
            self.assertIn(ValidationLevel.L0_FILE_VALID, report.passed_levels)
            self.assertIn(ValidationLevel.L1_DATASET_VALID, report.passed_levels)
            self.assertIn(ValidationLevel.L2_SPATIALLY_CONSISTENT, report.passed_levels)
            self.assertIn(ValidationLevel.L4_PURPOSE_SUITABLE, report.passed_levels)
            self.assertIn(ValidationLevel.L5_FIELD_VALIDATED, report.passed_levels)
            self.assertTrue(report.is_cadastral_ready)

            # Test cross source agreement
            raster_bbox = (390500.0, 584500.0, 391500.0, 585500.0)
            agrees = self.data_profiler.check_cross_source_agreement(report, raster_bbox)
            self.assertTrue(agrees)
            self.assertIn(ValidationLevel.L3_CROSS_SOURCE_AGREED, report.passed_levels)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_data_profiler_detects_wgs84_misprojection(self):
        fixture = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[23.58, 46.77], [23.59, 46.77], [23.59, 46.78], [23.58, 46.77]]],
                },
            }],
        }
        with tempfile.NamedTemporaryFile("w", suffix=".geojson", delete=False) as f:
            json.dump(fixture, f)
            temp_path = f.name

        try:
            report = self.data_profiler.profile_vector_file(temp_path)
            self.assertNotIn(ValidationLevel.L2_SPATIALLY_CONSISTENT, report.passed_levels)
            self.assertTrue(any("WGS84 degrees" in issue for issue in report.issues))
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    # 6. Provenance Lineage Tests
    def test_provenance_chain(self):
        chain = ProvenanceChain("task_p4_audit")
        chain.record_step(
            evidence_class=EvidenceClass.OBSERVED,
            step_name="acquire_orthophoto",
            operator="UAV_Flight",
            inputs=["raw_sensors"],
            outputs=["cluj_ortho_10cm.tif"],
            parameters={"gsd_cm": 10},
        )
        chain.record_step(
            evidence_class=EvidenceClass.MODEL_PREDICTION,
            step_name="sam2_segmentation",
            operator="Meta SAM2-Hiera",
            inputs=["cluj_ortho_10cm.tif"],
            outputs=["building_masks.geojson"],
            parameters={"box_prompt": True},
        )
        chain.record_step(
            evidence_class=EvidenceClass.HUMAN_DECISION,
            step_name="surveyor_signoff",
            operator="Ing_Geodez_Autorizat",
            inputs=["building_masks.geojson"],
            outputs=["official_pad.cp"],
            human_signed_off=True,
        )

        d = chain.to_dict()
        self.assertEqual(d["record_count"], 3)
        self.assertTrue(d["has_human_signoff"])
        self.assertEqual(d["lineage"][1]["evidence_class"], "MODEL_PREDICTION")

    # 7. Simulation & Perturbation Engine Tests
    def test_perturbation_translation_and_rotation(self):
        ring = [(0.0, 0.0), (10.0, 0.0), (10.0, 10.0), (0.0, 10.0), (0.0, 0.0)]
        engine = PerturbationEngine()
        config = PerturbationConfig(
            shift_x=5.0,
            shift_y=-2.0,
            rotation_deg=90.0,
            scale=1.0,
            seed=42,
        )
        perturbed = engine.perturb_ring(ring, config)
        self.assertEqual(len(perturbed), len(ring))
        # Verify closed ring maintained
        self.assertEqual(perturbed[0], perturbed[-1])
        # Centroid was at (5, 5). Shifted by (5, -2) -> new centroid is (10, 3)
        pxs = [p[0] for p in perturbed[:-1]]
        pys = [p[1] for p in perturbed[:-1]]
        new_cx = sum(pxs) / len(pxs)
        new_cy = sum(pys) / len(pys)
        self.assertAlmostEqual(new_cx, 10.0, places=2)
        self.assertAlmostEqual(new_cy, 3.0, places=2)


if __name__ == "__main__":
    unittest.main()
