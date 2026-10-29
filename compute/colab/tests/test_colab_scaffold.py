"""Local, GPU-free tests for the Colab scaffold. Run: python -m unittest discover compute/colab/tests"""
from __future__ import annotations

import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
COLAB = HERE.parent
REPO = COLAB.parents[1]
sys.path.insert(0, str(COLAB))
sys.path.insert(0, str(COLAB / "scripts"))
sys.path.insert(0, str(REPO / "scripts"))

import job_plan  # noqa: E402
import l2a_data  # noqa: E402


class JobCardTests(unittest.TestCase):
    def test_all_cards_validate(self):
        cards = sorted(job_plan.JOBS_DIR.glob("*.yaml"))
        self.assertGreaterEqual(len(cards), 4)
        for p in cards:
            errors = job_plan.validate(job_plan.load_card(p.stem))
            self.assertEqual(errors, [], f"{p.name}: {errors}")

    def test_every_card_requires_owner_approval_and_crs(self):
        for p in job_plan.JOBS_DIR.glob("*.yaml"):
            card = job_plan.load_card(p.stem)
            self.assertIs(card["requires_owner_approval"], True)
            self.assertEqual(card["crs"], "EPSG:3844")

    def test_invalid_cards_rejected(self):
        good = job_plan.load_card("train_l2a")
        self.assertTrue(job_plan.validate({**good, "gpu": "RTX9000"}))
        self.assertTrue(job_plan.validate({**good, "time_limit_minutes": 5000}))
        self.assertTrue(job_plan.validate({**good, "requires_owner_approval": False}))
        self.assertTrue(job_plan.validate({**good, "script": "does/not/exist.py"}))
        self.assertTrue(job_plan.validate({k: v for k, v in good.items() if k != "gpu"}))

    def test_cli_exit_codes(self):
        self.assertEqual(job_plan.main(["train_l2a"]), 0)
        self.assertEqual(job_plan.main(["no_such_job"]), 1)


class L2aDataTests(unittest.TestCase):
    def test_prepare_input_shape_and_nodata(self):
        rgb = np.full((8, 8, 3), 255, dtype=np.uint8)
        ndsm = np.full((8, 8), 100.0, dtype=np.float32)
        ndsm[0, 0] = np.nan
        ndsm[1, 1] = -3.0
        x = l2a_data.prepare_input(rgb, ndsm)
        self.assertEqual(x.shape, (4, 8, 8))
        self.assertEqual(x.dtype, np.float32)
        self.assertEqual(float(x[3, 0, 0]), 0.0)   # NaN -> 0
        self.assertEqual(float(x[3, 1, 1]), 0.0)   # negative clipped to 0
        self.assertEqual(float(x[3, 4, 4]), 1.0)   # >40 m clipped to 1
        with self.assertRaises(ValueError):
            l2a_data.prepare_input(rgb, ndsm[:4])

    def test_augment_geometric_all_channels_photometric_rgb_only(self):
        rng = np.random.default_rng(1)
        x = np.random.default_rng(0).random((4, 16, 16)).astype(np.float32)
        mask = (x[3] > 0.5).astype(np.float32)  # mask is a function of the nDSM channel
        for _ in range(20):
            xa, ma = l2a_data.augment(x, mask, rng)
            # geometry stayed consistent between nDSM channel and mask => same transform on both
            np.testing.assert_array_equal(ma, (xa[3] > 0.5).astype(np.float32))
            # nDSM values are only permuted, never changed: sorted values identical
            np.testing.assert_allclose(np.sort(xa[3].ravel()), np.sort(x[3].ravel()))

    def test_bbox_gap(self):
        self.assertEqual(l2a_data.bbox_gap([0, 0, 10, 10], [5, 5, 20, 20]), 0.0)
        self.assertEqual(l2a_data.bbox_gap([0, 0, 10, 10], [40, 0, 50, 10]), 30.0)
        self.assertAlmostEqual(l2a_data.bbox_gap([0, 0, 10, 10], [13, 14, 20, 20]), 5.0)

    def _manifest(self, gap):
        return {
            "crs": "EPSG:3844", "buffer_m": 30.0,
            "tiles": [
                {"id": "a", "split": "train", "bounds": [0, 0, 100, 100]},
                {"id": "b", "split": "test", "bounds": [100 + gap, 0, 200 + gap, 100]},
            ],
        }

    def test_leakage_buffer_enforced(self):
        self.assertEqual(l2a_data.validate_manifest(self._manifest(30.0)), [])
        self.assertTrue(l2a_data.validate_manifest(self._manifest(10.0)))

    def test_manifest_crs_and_splits(self):
        m = self._manifest(50.0)
        self.assertTrue(l2a_data.validate_manifest({**m, "crs": "EPSG:4326"}))
        m["tiles"][0]["split"] = "random"
        self.assertTrue(l2a_data.validate_manifest(m))
        self.assertTrue(l2a_data.validate_manifest({"crs": "EPSG:3844", "tiles": []}))

    def test_sha256_verification(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "i.tif").write_bytes(b"image")
            (root / "m.tif").write_bytes(b"mask")
            tile = {
                "id": "a", "split": "train", "bounds": [0, 0, 1, 1], "image": "i.tif", "mask": "m.tif",
                "image_sha256": l2a_data.sha256_file(root / "i.tif"),
                "mask_sha256": l2a_data.sha256_file(root / "m.tif"),
            }
            m = {"crs": "EPSG:3844", "tiles": [tile]}
            self.assertEqual(l2a_data.validate_manifest(m, root, verify_hashes=True), [])
            (root / "m.tif").write_bytes(b"tampered")
            self.assertTrue(l2a_data.validate_manifest(m, root, verify_hashes=True))


@unittest.skipUnless(importlib.util.find_spec("torch"), "torch not installed")
class LossTests(unittest.TestCase):
    def test_dice_bce_loss_perfect_vs_wrong(self):
        import torch

        sys.modules.pop("train_l2a", None)
        import train_l2a

        target = torch.zeros(1, 1, 8, 8)
        target[..., 2:6, 2:6] = 1.0
        perfect = (target * 2 - 1) * 20.0
        wrong = -perfect
        good, bad = train_l2a.dice_bce_loss(perfect, target).item(), train_l2a.dice_bce_loss(wrong, target).item()
        self.assertLess(good, 0.05)
        self.assertGreater(bad, 1.0)
        self.assertAlmostEqual(train_l2a.iou_score(perfect, target), 1.0)
        self.assertAlmostEqual(train_l2a.iou_score(wrong, target), 0.0)


@unittest.skipUnless(importlib.util.find_spec("scipy"), "scipy not installed")
class Sam21HelperTests(unittest.TestCase):
    def test_mask_to_boxes_and_progress(self):
        import refine_sam21

        m = np.zeros((50, 50), dtype=np.uint8)
        m[5:15, 5:20] = 1      # 150 px component
        m[30:33, 30:33] = 1    # 9 px component, dropped by min area
        boxes = refine_sam21.mask_to_boxes(m, min_area_px=40)
        self.assertEqual(boxes.tolist(), [[5.0, 5.0, 19.0, 14.0]])
        self.assertEqual(refine_sam21.mask_to_boxes(np.zeros((5, 5))).shape, (0, 4))
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "progress.json"
            self.assertEqual(refine_sam21.load_progress(p), set())
            refine_sam21.save_progress(p, {"t2", "t1"})
            self.assertEqual(refine_sam21.load_progress(p), {"t1", "t2"})
            self.assertEqual(json.loads(p.read_text())["done"], ["t1", "t2"])


class McpMirrorTests(unittest.TestCase):
    def test_check_and_sync_in_temp_repo(self):
        import sync_mcp_mirrors as s

        servers = {"a": {"command": "x", "args": ["1"]}}
        with tempfile.TemporaryDirectory() as d:
            repo = Path(d)
            (repo / "mcp_config.json").write_text(json.dumps({"mcpServers": servers}))
            self.assertTrue(s.check(repo))            # .agents mirror missing
            s.sync(repo)
            self.assertEqual(s.check(repo, require_all=True), [])
            self.assertIn("servers", json.loads((repo / ".vscode" / "mcp.json").read_text()))
            (repo / ".mcp.json").write_text(json.dumps({"mcpServers": {"b": {}}}))
            self.assertTrue(s.check(repo))            # drift detected

    def test_repo_mirror_is_in_sync(self):
        import sync_mcp_mirrors as s

        self.assertEqual(s.check(REPO), [])


class Continuous2DA100Tests(unittest.TestCase):
    def test_continuous_2d_a100_card_is_valid_a100(self):
        card = job_plan.load_card("continuous_2d_a100")
        self.assertEqual(job_plan.validate(card), [])
        self.assertEqual(card["gpu"], "A100")
        self.assertEqual(card["crs"], "EPSG:3844")
        self.assertTrue(card["requires_owner_approval"])

    def test_build_2d_roof_dataset_masks_and_rgb_only_tensor(self):
        import build_2d_roof_dataset as b2d

        rgb = np.full((64, 64, 3), 120, dtype=np.uint8)
        rgb[:4, :] = 0  # Black NoData border
        t = b2d.prepare_rgb_2d_tensor(rgb)
        self.assertEqual(t.shape, (3, 64, 64))
        self.assertEqual(t.dtype, np.float32)

        roof_px = [[16.0, 16.0], [48.0, 16.0], [48.0, 48.0], [16.0, 48.0], [16.0, 16.0]]
        r_admis, e_admis, c_admis = b2d.build_multitask_masks_for_chip(rgb, roof_px, "ADMIS")
        self.assertEqual(int(r_admis[32, 32]), 1)
        self.assertEqual(int(r_admis[1, 1]), 255)  # NoData border masked as ignore_index=255
        self.assertGreater(int(e_admis.sum()), 10)
        self.assertGreater(int(c_admis.sum()), 4)

        r_aj, _, _ = b2d.build_multitask_masks_for_chip(rgb, roof_px, "AJUSTARE_TINTA_A100")
        self.assertEqual(int(r_aj[32, 32]), 255)  # Incomplete roof masked as ignore_index=255

    def test_multitask_2d_loss_ignores_255(self):
        import continuous_2d_roof_loop as loop2d

        target_r = np.zeros((16, 16), dtype=np.uint8)
        target_r[4:12, 4:12] = 1
        target_r[0:2, :] = 255
        target_e = np.zeros((16, 16), dtype=np.uint8)
        target_c = np.zeros((16, 16), dtype=np.uint8)

        pred_good = (target_r == 1).astype(np.float32) * 0.98 + 0.01
        pred_bad = 1.0 - pred_good
        zeros = np.full((16, 16), 0.01, dtype=np.float32)

        l_good = loop2d.compute_multitask_2d_loss_numpy(
            pred_good, zeros, zeros, target_r, target_e, target_c
        )
        l_bad = loop2d.compute_multitask_2d_loss_numpy(
            pred_bad, zeros, zeros, target_r, target_e, target_c
        )
        self.assertLess(l_good["total_loss"], 0.15)
        self.assertGreater(l_bad["total_loss"], 1.5)


if __name__ == "__main__":
    unittest.main()
