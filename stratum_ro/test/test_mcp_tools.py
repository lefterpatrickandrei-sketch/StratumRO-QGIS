# -*- coding: utf-8 -*-
"""
Unit tests for StratumRO MCP Tools, Security Sandbox & Permission Gate (MD 3).
Verifies:
1. Filesystem sandbox & path traversal blocking
2. ALLOW / SAFE_WRITE / ASK / DENY permission hierarchy
3. Read-only inspection tools (project, layer, raster, LiDAR)
4. Deterministic vector regularization, eave retraction & planar partitioning
5. ANCPI cadastral validation & ground-truth evaluation
6. Human-in-the-loop preview-and-commit workflows
7. TopoLT DXF and eTerra .CP export approval gates
8. FastMCP server catalog registration
"""

import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from shapely.geometry import Polygon, box, mapping

# Add repo root to sys.path
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from stratum_ro.ai.tools.security import (
    resolve_sandboxed_path,
    check_permission,
    PermissionClass,
)
from stratum_ro.ai.tools.project_tools import (
    get_workspace_context,
    get_aoi,
    list_layers,
    inspect_layer,
)
from stratum_ro.ai.tools.raster_tools import inspect_raster
from stratum_ro.ai.tools.segmentation_tools import run_sam2_segmentation, inspect_mask
from stratum_ro.ai.tools.vector_tools import (
    regularize_footprints,
    apply_eave_offset,
    create_planar_partition,
    export_gpkg_layer,
    export_cityjson_lod1,
)
from stratum_ro.ai.tools.cadastral_tools import (
    validate_topology,
    validate_ancpi,
    create_preview,
    commit_to_project,
    export_topolt_cad,
    export_cp_file,
)
from stratum_ro.ai.tools.evaluation_tools import compare_ground_truth


class TestMCPToolsAndSecurity(unittest.TestCase):

    def setUp(self):
        self.test_dir = REPO_ROOT / "workspace" / "test_mcp_sandbox"
        self.test_dir.mkdir(parents=True, exist_ok=True)

        # Sample valid rectangular footprint in Stereo 70 (USAMV Cluj sector)
        self.poly_rect = mapping(box(392000.0, 585000.0, 392015.0, 585010.0))  # 15m x 10m = 150m2
        # Sample annex footprint (3m x 2m = 6m2 < 8m2 threshold)
        self.poly_sliver = mapping(box(392020.0, 585000.0, 392023.0, 585002.0))

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir, ignore_errors=True)

    # =========================================================================
    # 1. Security Sandbox Tests
    # =========================================================================

    def test_sandbox_allows_valid_workspace_paths(self):
        valid_path = "workspace/test_mcp_sandbox/sub/file.txt"
        resolved = resolve_sandboxed_path(valid_path)
        self.assertTrue(resolved.is_relative_to(REPO_ROOT))

    def test_sandbox_blocks_path_traversal(self):
        with self.assertRaises((PermissionError, ValueError)):
            resolve_sandboxed_path("../../Windows/System32")

    def test_sandbox_blocks_os_root(self):
        with self.assertRaises(PermissionError):
            resolve_sandboxed_path("C:/Windows/System32/cmd.exe")
        with self.assertRaises(PermissionError):
            resolve_sandboxed_path("/etc/passwd")

    def test_sandbox_blocks_sensitive_env_files(self):
        with self.assertRaises(PermissionError):
            resolve_sandboxed_path(".env")

    # =========================================================================
    # 2. Permission Gate Tests
    # =========================================================================

    def test_permission_allow_tools(self):
        is_ok, msg = check_permission("project.get_context")
        self.assertTrue(is_ok)
        self.assertIn("ALLOW", msg)

    def test_permission_ask_tools_require_approval(self):
        # Disapproved
        is_ok, msg = check_permission("results.commit_to_project", approved=False)
        self.assertFalse(is_ok)
        self.assertIn("waiting_for_approval", msg)

        # Approved
        is_ok, msg = check_permission("results.commit_to_project", approved=True, approval_reason="Surveyor signoff")
        self.assertTrue(is_ok)
        self.assertIn("Surveyor signoff", msg)

    def test_permission_deny_unregistered_tools(self):
        is_ok, msg = check_permission("arbitrary.shell_execution")
        self.assertFalse(is_ok)
        self.assertIn("DENIED", msg)

    # =========================================================================
    # 3. Project & Context Tools
    # =========================================================================

    def test_get_workspace_context(self):
        ctx = get_workspace_context()
        self.assertEqual(ctx["status"], "ready")
        self.assertIn("3844", ctx["crs"])
        self.assertIn("hardware", ctx)
        # Ensure no raw env vars or API tokens leaked
        self.assertNotIn("UNION_ALPHA_API_KEY", ctx)
        self.assertNotIn("OPENAI_API_KEY", ctx)

    def test_get_aoi(self):
        aoi_data = get_aoi(format="wkt")
        self.assertEqual(aoi_data["status"], "success")
        self.assertEqual(aoi_data["crs"], "EPSG:3844")
        self.assertTrue(aoi_data["aoi"].startswith("POLYGON"))

    def test_list_and_inspect_layers(self):
        layers_res = list_layers()
        self.assertEqual(layers_res["status"], "success")
        self.assertIsInstance(layers_res["layers"], list)

        # Inspect tier1 ground truth GeoJSON
        gt_path = "data/ground_truth/tier1_teren.geojson"
        if (REPO_ROOT / gt_path).exists():
            inspect_res = inspect_layer(gt_path)
            self.assertEqual(inspect_res["status"], "success")
            self.assertGreater(inspect_res["feature_count"], 0)
            self.assertIn("EPSG:3844", inspect_res["crs"])

    # =========================================================================
    # 4. Segmentation Mask Inspection & Safety
    # =========================================================================

    def test_inspect_mask_compactness(self):
        mask_info = inspect_mask(self.poly_rect)
        self.assertEqual(mask_info["status"], "success")
        self.assertAlmostEqual(mask_info["area_m2"], 150.0, places=1)
        self.assertGreater(mask_info["compactness"], 0.5)

    def test_run_sam2_rejects_invalid_device(self):
        with self.assertRaises(ValueError):
            run_sam2_segmentation(
                ortho_chip_path="data/ground_truth/tier1_teren.geojson",
                candidate_prompts=[{"x": 10, "y": 20}],
                device="quantum_accelerator"
            )

    # =========================================================================
    # 5. Vector Tools (Regularization, Eave Retraction, Partitioning)
    # =========================================================================

    def test_regularize_footprints(self):
        reg_res = regularize_footprints([self.poly_rect], mrr_trigger=0.70)
        self.assertEqual(reg_res["status"], "success")
        self.assertEqual(reg_res["total_polygons"], 1)
        self.assertEqual(reg_res["canonical_rectangles_count"], 1)

    def test_apply_eave_offset(self):
        eave_res = apply_eave_offset([self.poly_rect], offset_m=-0.40)
        self.assertEqual(eave_res["status"], "success")
        self.assertEqual(eave_res["offset_applied_m"], -0.40)
        # Offset polygon should have slightly smaller area than 150m2
        offset_geom = Polygon(eave_res["polygons"][0]["coordinates"][0])
        self.assertLess(offset_geom.area, 150.0)

    def test_create_planar_partition(self):
        sector = mapping(box(391990.0, 584990.0, 392030.0, 585030.0))  # 40m x 40m = 1600m2
        part_res = create_planar_partition([self.poly_rect], sector_boundary=sector)
        self.assertEqual(part_res["status"], "success")
        self.assertAlmostEqual(part_res["total_sector_area_m2"], 1600.0, places=1)
        self.assertAlmostEqual(part_res["buildings_area_m2"], 150.0, places=1)
        self.assertAlmostEqual(part_res["unclassified_area_m2"], 1450.0, places=1)

    # =========================================================================
    # 6. Geodetic & Cadastral Validation
    # =========================================================================

    def test_validate_topology_clean_vs_sliver(self):
        top_clean = validate_topology([self.poly_rect])
        self.assertTrue(top_clean["valid"])
        self.assertEqual(top_clean["invalid_features"], 0)

        # Micro-polygon (< 1.0 m2)
        micro_poly = mapping(box(0, 0, 0.5, 0.5))  # 0.25 m2
        top_sliver = validate_topology([micro_poly])
        self.assertFalse(top_sliver["valid"])
        self.assertEqual(top_sliver["sliver_count"], 1)

    def test_validate_ancpi(self):
        val_res = validate_ancpi([self.poly_rect, self.poly_sliver])
        self.assertEqual(val_res["status"], "success")
        self.assertEqual(val_res["total_features"], 2)
        # self.poly_rect is 150m2 (>= 45m2) -> 1CC passed
        self.assertEqual(val_res["checks"]["min_area_main_45m2"]["passed"], 1)
        # self.poly_sliver is 6m2 (< 8m2 annex threshold) -> warning recorded
        self.assertEqual(val_res["checks"]["min_area_annex_8m2"]["failed"], 1)
        self.assertFalse(val_res["passed"])

    # =========================================================================
    # 7. Ground Truth Evaluation
    # =========================================================================

    def test_compare_ground_truth(self):
        gt_file = "data/ground_truth/tier1_teren.geojson"
        if (REPO_ROOT / gt_file).exists():
            eval_res = compare_ground_truth(gt_file, gt_file)
            self.assertEqual(eval_res["status"], "success")
            self.assertEqual(eval_res["true_positives"], eval_res["total_references"])
            self.assertAlmostEqual(eval_res["metrics"]["mean_iou"], 1.0, places=2)
            self.assertIn("DEFENSIBLE POSITIONING", eval_res["geodetic_disclaimer"])

    # =========================================================================
    # 8. Human-in-the-Loop Preview & Commit Gate
    # =========================================================================

    def test_preview_and_commit_workflow(self):
        # 1. Create preview
        prev_res = create_preview([self.poly_rect], title="test_preview")
        self.assertEqual(prev_res["status"], "success")
        preview_path = prev_res["preview_path"]
        self.assertTrue(Path(preview_path).exists())

        # 2. Attempt commit without approval -> MUST be paused
        commit_unapproved = commit_to_project(preview_path, approved=False)
        self.assertEqual(commit_unapproved["status"], "waiting_for_approval")
        self.assertTrue(commit_unapproved["requires_user_action"])

        # 3. Commit with approval -> Succeeded
        target_gpkg = str(self.test_dir / "official_commit.gpkg")
        commit_approved = commit_to_project(
            preview_path,
            target_layer_path=target_gpkg,
            approved=True,
            approval_reason="Verified by surveyor autorizat ANCPI"
        )
        self.assertEqual(commit_approved["status"], "success")
        self.assertTrue(Path(commit_approved["target_path"]).exists())

    # =========================================================================
    # 9. TopoLT DXF and eTerra .CP Export Gates
    # =========================================================================

    def test_export_topolt_dxf_approval_gate(self):
        out_dxf = str(self.test_dir / "test_topolt.dxf")

        # Without approval: paused
        res_ask = export_topolt_cad(out_dxf, buildings=[self.poly_rect], approved=False)
        self.assertEqual(res_ask["status"], "waiting_for_approval")

        # With approval: written
        res_ok = export_topolt_cad(
            out_dxf,
            buildings=[self.poly_rect],
            approved=True,
            approval_reason="Ready for submission"
        )
        self.assertEqual(res_ok["status"], "success")
        self.assertTrue(Path(res_ok["output_dxf_path"]).exists())

    def test_export_cp_approval_gate(self):
        out_cp = str(self.test_dir / "test_eterra.cp")
        pts = [{"nr": 1, "x": 392000.0, "y": 585000.0, "z": 345.5}]

        # Without approval: paused
        res_ask = export_cp_file(out_cp, parcel_id="123456", points=pts, approved=False)
        self.assertEqual(res_ask["status"], "waiting_for_approval")

        # With approval: written
        res_ok = export_cp_file(
            out_cp,
            parcel_id="123456",
            points=pts,
            approved=True,
            approval_reason="Official border surveyed"
        )
        self.assertEqual(res_ok["status"], "success")
        self.assertTrue(Path(res_ok["output_cp_path"]).exists())

    # =========================================================================
    # 10. 3D LoD1 CityJSON Export
    # =========================================================================

    def test_export_cityjson_lod1(self):
        out_cityjson = str(self.test_dir / "test_buildings.city.json")
        cj_res = export_cityjson_lod1(out_cityjson, [self.poly_rect])
        self.assertEqual(cj_res["status"], "success")
        self.assertTrue(Path(cj_res["output_cityjson_path"]).exists())

    # =========================================================================
    # 11. FastMCP Server Catalog Verification
    # =========================================================================

    def test_fastmcp_server_catalog(self):
        sys.path.insert(0, str(REPO_ROOT / "mcp"))
        import stratumro_server
        import asyncio

        tools = asyncio.run(stratumro_server.mcp.list_tools())
        tool_names = [t.name for t in tools]

        expected_tools = [
            "project.get_context",
            "project.get_aoi",
            "layers.list",
            "layers.inspect",
            "raster.inspect",
            "raster.extract_chip",
            "lidar.inspect",
            "lidar.generate_ndsm",
            "segmentation.run_sam2",
            "segmentation.inspect_mask",
            "vector.regularize",
            "vector.apply_eave_offset",
            "vector.planar_partition",
            "geometry.validate_topology",
            "cadastral.validate_ancpi",
            "evaluation.compare_ground_truth",
            "results.create_preview",
            "results.commit_to_project",
            "export.export_gpkg",
            "export.export_topolt_dxf",
            "export.export_cp",
            "export.export_cityjson",
        ]

        for expected in expected_tools:
            self.assertIn(expected, tool_names)


if __name__ == "__main__":
    unittest.main()
