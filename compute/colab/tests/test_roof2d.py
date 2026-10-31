"""Unit tests for the Phase 1 georeferenced 2D roof pipeline (roof2d_data, train_roof2d, scan_roof2d_aoi)."""
from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path

import numpy as np

SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(REPO))

HAS_GEO = all(importlib.util.find_spec(m) for m in ("rasterio", "shapely", "cv2", "scipy"))


def grid(n=200, px=0.15, x0=1000.0, y0=2000.0):
    from rasterio.transform import Affine

    return Affine(px, 0, x0, 0, -px, y0), (n, n)


def world_box(transform, r0, c0, r1, c1):
    from shapely.geometry import box

    x0, y0 = transform * (c0, r0)
    x1, y1 = transform * (c1, r1)
    return box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


@unittest.skipUnless(HAS_GEO, "rasterio/shapely/cv2/scipy missing")
class LabelPolicyTests(unittest.TestCase):
    def setUp(self):
        from roof2d_data import build_label_rasters

        self.t, shape = grid()
        self.rgb = np.full(shape + (3,), 120, np.uint8)
        self.rgb[:, :10] = 0  # NoData strip
        self.pos = world_box(self.t, 40, 40, 100, 100)
        self.neg = world_box(self.t, 90, 90, 130, 130)  # overlaps the positive corner
        self.ign = world_box(self.t, 140, 20, 180, 60)
        ground = np.zeros(shape, bool)
        ground[150:, 100:] = True
        self.roof, self.edge, self.corner, self.contact = build_label_rasters(
            self.rgb, self.t, [self.pos], [self.neg], [self.ign], ground)

    def test_positive_wins_over_negative(self):
        self.assertEqual(self.roof[95, 95], 1)  # inside both: owner positive is never erased
        self.assertEqual(self.roof[120, 120], 0)

    def test_ring_ignore_ground_and_nodata(self):
        self.assertEqual(self.roof[70, 104], 0)  # 0.6 m outside the positive: background ring
        self.assertEqual(self.roof[160, 40], 255)  # ignore polygon
        self.assertEqual(self.roof[180, 180], 0)  # LiDAR ground away from candidates
        self.assertEqual(self.roof[20, 160], 255)  # unreviewed area
        self.assertEqual(self.roof[50, 5], 255)  # NoData
        self.assertEqual(self.edge[50, 5], 0)

    def test_edge_and_corner_targets(self):
        self.assertEqual(self.edge[40, 70], 1)
        self.assertEqual(self.edge[70, 70], 0)
        self.assertEqual(self.corner[40, 40], 1)
        self.assertEqual(self.corner[40, 70], 0)

    def test_contact_marks_shared_wall_only(self):
        from roof2d_data import build_label_rasters

        a = world_box(self.t, 40, 40, 100, 100)
        b = world_box(self.t, 40, 101, 100, 150)  # 0.15 m gap: terraced neighbour
        _, edge, _, contact = build_label_rasters(self.rgb, self.t, [a, b], [], [])
        self.assertEqual(contact[70, 100], 1)
        self.assertEqual(edge[70, 100], 1)
        self.assertEqual(contact[40, 70], 0)
        self.assertEqual(self.contact.sum(), 0)  # a single roof has no contact

    def test_split_raster_bands(self):
        from roof2d_data import SPLIT_BUFFER, SPLIT_TRAIN, SPLIT_VAL, split_raster

        s = split_raster(self.t, (200, 200), val_min_y=2000.0 - 100 * 0.15, buffer_m=3.0)
        self.assertEqual(s[0, 0], SPLIT_VAL)
        self.assertEqual(s[100, 5], SPLIT_BUFFER)
        self.assertEqual(s[199, 199], SPLIT_TRAIN)


@unittest.skipUnless(HAS_GEO, "rasterio/shapely/cv2/scipy missing")
class CropAugmentTests(unittest.TestCase):
    def test_sample_crop_out_of_bounds_is_ignored_and_resized(self):
        from roof2d_data import IGNORE, sample_crop

        rgb = np.full((100, 100, 3), 200, np.uint8)
        labels = np.zeros((3, 100, 100), np.uint8)
        img, lab = sample_crop(rgb, labels, (0, 0), 64, 1.5)
        self.assertEqual(img.shape, (64, 64, 3))
        self.assertEqual(lab.shape, (3, 64, 64))
        self.assertEqual(lab[0, 0, 0], IGNORE)
        self.assertEqual(lab[0, 63, 63], 0)
        self.assertEqual(img[0, 0].sum(), 0.0)

    def test_photometric_keeps_nodata_black(self):
        from roof2d_data import augment_photometric

        x = np.full((32, 32, 3), 0.5, np.float32)
        x[:4] = 0.0
        rng = np.random.default_rng(1)
        for _ in range(10):
            y = augment_photometric(x, rng)
            self.assertTrue(np.all(y[:4] == 0.0))
            self.assertTrue(0.0 <= y.min() and y.max() <= 1.0)

    def test_pseudo_never_overrides_owner_labels(self):
        from train_roof2d import with_pseudo

        labels = np.zeros((3, 10, 10), np.uint8)
        labels[0, :, :5] = 255
        pseudo = np.ones((10, 10), np.uint8)
        out = with_pseudo(labels, pseudo)
        self.assertTrue(np.all(out[0, :, 5:] == 0))  # owner background stays background
        self.assertTrue(np.all(out[0, :, :5] == 1))  # unknown pixels filled
        self.assertTrue(np.all(labels[0, :, :5] == 255))  # input untouched


@unittest.skipUnless(importlib.util.find_spec("torch"), "torch not installed")
class LossTests(unittest.TestCase):
    def test_loss_ignores_255_and_prefers_correct(self):
        import torch

        from train_roof2d import multitask_loss

        y = torch.zeros((1, 3, 8, 8), dtype=torch.uint8)
        y[0, 0, :, :4] = 1
        y[0, 0, :, 6:] = 255
        good = torch.full((1, 3, 8, 8), -6.0)
        good[0, 0, :, :4] = 6.0
        bad = -good
        bad[0, 0, :, 6:] = 6.0
        lg, _ = multitask_loss(good, y)
        lb, _ = multitask_loss(bad, y)
        self.assertLess(float(lg), float(lb))
        noisy = good.clone()
        noisy[0, 0, :, 6:] = 100.0  # predictions on ignored pixels must not change the loss
        self.assertAlmostEqual(float(multitask_loss(noisy, y)[0]), float(lg), places=5)

    def test_contact_channel_weighs_outline_loss(self):
        import torch

        from train_roof2d import multitask_loss

        y = torch.zeros((1, 4, 8, 8), dtype=torch.uint8)
        y[0, 1, :, 3] = 1
        logits = torch.zeros((1, 3, 8, 8))
        base = multitask_loss(logits, y[:, :3])[1]["edge"]
        y[0, 3, :, 3] = 1
        self.assertGreater(multitask_loss(logits, y)[1]["edge"], base)

    def test_model_output_shape(self):
        import torch

        from train_roof2d import build_model

        for arch in ("resnet34", "convnext_tiny"):
            m = build_model(pretrained=False, arch=arch).eval()
            with torch.no_grad():
                self.assertEqual(tuple(m(torch.zeros(1, 3, 64, 64)).shape), (1, 3, 64, 64), arch)


@unittest.skipUnless(HAS_GEO, "rasterio/shapely/cv2/scipy missing")
class VectorizeTests(unittest.TestCase):
    def test_resolve_overlaps_clips_weaker_and_drops_duplicates(self):
        from shapely.geometry import box

        from scan_roof2d_aoi import resolve_overlaps

        strong, weak, dup = box(0, 0, 10, 10), box(8, 0, 18, 10), box(1, 1, 9, 9)
        kept, dropped = resolve_overlaps([(weak, 0.7), (strong, 0.9), (dup, 0.6)])
        self.assertEqual(dropped, 1)
        self.assertEqual(len(kept), 2)
        geoms = [g for g, _, _ in kept]
        self.assertLess(geoms[0].intersection(geoms[1]).area, 0.25)
        self.assertTrue(kept[1][2])  # the weaker one was clipped

    def test_snap_rectilinear_squares_a_noisy_l(self):
        from shapely.affinity import rotate
        from shapely.geometry import Polygon, box

        from scan_roof2d_aoi import angle_stats, snap_rectilinear

        l_shape = rotate(box(0, 0, 20, 10).union(box(0, 0, 8, 18)), 23, origin=(0, 0))
        rng = np.random.default_rng(0)
        c = np.asarray(l_shape.exterior.coords)[:-1]
        noisy = Polygon(c + rng.normal(0, 0.1, c.shape))
        rect = snap_rectilinear(noisy.buffer(0))
        self.assertIsNotNone(rect)
        self.assertEqual(len(rect.exterior.coords) - 1, 6)
        self.assertEqual(angle_stats([rect])["ortho_45_90_share"], 1.0)
        self.assertGreater(rect.intersection(l_shape).area / rect.union(l_shape).area, 0.95)

    def test_outline_head_splits_touching_roofs_and_regularizes(self):
        from scan_roof2d_aoi import angle_stats, regularize, vectorize

        t, shape = grid(200)
        roof = np.zeros(shape, np.float32)
        edge = np.zeros(shape, np.float32)
        roof[40:120, 30:170] = 0.95
        edge[40:120, 99:102] = 0.9  # shared wall between two roofs
        polys = vectorize(roof, edge, t, thr=0.5, min_area_m2=12.0)
        self.assertEqual(len(polys), 2)
        reg = [regularize(p) for p, _ in polys]
        self.assertTrue(all(len(p.exterior.coords) - 1 == 4 for p in reg))
        self.assertEqual(angle_stats(reg)["ortho_45_90_share"], 1.0)
        total = sum(p.area for p in reg)
        self.assertAlmostEqual(total, 80 * 140 * 0.15**2, delta=0.06 * total)


if __name__ == "__main__":
    unittest.main()


@unittest.skipUnless(HAS_GEO, "rasterio/shapely/cv2/scipy missing")
class EaveSnapTests(unittest.TestCase):
    def test_edge_moves_parallel_onto_the_eave_and_keeps_right_angles(self):
        from shapely.geometry import box

        from scan_roof2d_aoi import angle_stats
        from vlm_merge_finish import snap_edges

        truth = box(0, 0, 10.45, 8)  # real eave on the east side is 0.45 m further out

        def sample(xy):
            return 1.0 if truth.exterior.distance(__import__("shapely.geometry", fromlist=["Point"]).Point(xy)) < 0.08 else 0.0

        snapped, shift = snap_edges(box(0, 0, 10, 8), sample)
        self.assertAlmostEqual(snapped.bounds[2], 10.45, delta=0.08)
        self.assertGreater(shift, 0.3)
        self.assertEqual(angle_stats([snapped])["ortho_45_90_share"], 1.0)
