# -*- coding: utf-8 -*-
"""
Test Suite for StratumRO Phase 2 — Hybrid Sensor Fusion & Calcan Retraction
Covers:
  - 2D Hann window apodization and sliding-window seamless inference
  - Multi-tile intersecting detection and VRT virtual mosaicing
  - 3D structural feature tensors (planarity, sphericity, linearity)
  - Vertical datum normalization (TransDatRO geoid offset)
  - Calcan-aware adaptive eave retraction (ANCPI party wall protection)
"""

import os
import unittest
import numpy as np
from shapely.geometry import Polygon, LineString, Point, box

from stratum_ro.ortho_extractor import (
    generate_hann_window_2d,
    sliding_window_inference_mosaic,
    OrthoExtractor
)
from stratum_ro.lidar_processor import (
    compute_3d_structural_features,
    LidarProcessor
)
from stratum_ro.geometry_utils import (
    apply_calcan_aware_eave_retraction,
    apply_eave_retraction_with_calcan
)


class TestPhase2SensorFusion(unittest.TestCase):

    def test_hann_window_2d_properties(self):
        """Verifică proprietățile matematice ale ferestrei Hann 2D."""
        tile_size = 256
        hann = generate_hann_window_2d(tile_size)
        
        self.assertEqual(hann.shape, (256, 256))
        self.assertTrue(np.allclose(hann, hann.T), "Fereastra Hann 2D trebuie sa fie perfect simetrica.")
        
        # Centrul ferestrei trebuie să fie maxim (apropiat de 1.0)
        center_val = hann[128, 128]
        self.assertAlmostEqual(float(center_val), 1.0, places=2)
        
        # Perimetrul trebuie să aibă valori atenuate spre 0
        self.assertLess(float(hann[0, 128]), 0.05)
        self.assertLess(float(hann[128, 0]), 0.05)
        self.assertLess(float(hann[255, 128]), 0.05)

    def test_sliding_window_inference_mosaic(self):
        """Verifică inferența glisantă pe blocuri mari cu blending Hann și reflective padding."""
        # Creăm o imagine sintetică de 800 x 600 pixeli
        img = np.random.randint(0, 255, (600, 800, 3), dtype=np.uint8)

        # Mock predictor care returnează o probabilitate uniformă de 0.85
        def mock_predict(tile):
            return np.full((tile.shape[0], tile.shape[1]), 0.85, dtype=np.float32)

        result_mask = sliding_window_inference_mosaic(
            img,
            tile_size=256,
            overlap_margin=64,
            predict_fn=mock_predict
        )

        self.assertEqual(result_mask.shape, (600, 800), "Dimensiunea măștii finale trebuie să coincidă exact cu imaginea de intrare.")
        self.assertFalse(np.isnan(result_mask).any(), "Nu trebuie să existe valori NaN în masca de inferență.")
        # Valorile normalizate trebuie să fie fidele predictorului
        self.assertTrue(np.allclose(result_mask, 0.85, atol=0.05))

    def test_ortho_extractor_multi_tile_intersection(self):
        """Verifică detectarea multi-tile pe granița dintre plăci orthophoto."""
        extractor = OrthoExtractor(tiles_dir=None)
        # Mock index cu 2 tile-uri alăturate (West și East)
        extractor.tiles_index = [
            {
                "name": "Tile_West.sid",
                "path": "C:/fake/Tile_West.sid",
                "xmin": 390000.0,
                "xmax": 391000.0,
                "ymin": 585000.0,
                "ymax": 586000.0,
                "resolution": 0.10
            },
            {
                "name": "Tile_East.sid",
                "path": "C:/fake/Tile_East.sid",
                "xmin": 391000.0,
                "xmax": 392000.0,
                "ymin": 585000.0,
                "ymax": 586000.0,
                "resolution": 0.10
            }
        ]

        # AOI care se întinde peste ambele plăci (390800 -> 391200)
        crossing_tiles = extractor.find_intersecting_tiles(
            xmin=390800.0, ymin=585200.0, xmax=391200.0, ymax=585800.0
        )
        self.assertEqual(len(crossing_tiles), 2, "Trebuie identificate ambele tile-uri la trecerea frontierei.")
        self.assertIn("C:/fake/Tile_West.sid", crossing_tiles)
        self.assertIn("C:/fake/Tile_East.sid", crossing_tiles)

        # AOI situat strict în placa de vest
        west_only = extractor.find_intersecting_tiles(
            xmin=390100.0, ymin=585200.0, xmax=390500.0, ymax=585800.0
        )
        self.assertEqual(len(west_only), 1)
        self.assertEqual(west_only[0], "C:/fake/Tile_West.sid")

    def test_compute_3d_structural_features(self):
        """Verifică tensorii structurali 3D (planaritate acoperiș, sfericitate arbore, liniaritate cablu)."""
        # 1. Puncte coplanare (acoperiș plat Z = 10.0 cu zgomot minim)
        xx, yy = np.meshgrid(np.linspace(0, 10, 15), np.linspace(0, 10, 15))
        zz = np.full_like(xx, 10.0) + np.random.normal(0, 0.02, xx.shape)
        plane_pts = np.vstack([xx.ravel(), yy.ravel(), zz.ravel()]).T

        res_plane = compute_3d_structural_features(plane_pts, radius_m=2.0)
        mean_planarity = float(np.mean(res_plane["planarity"]))
        mean_sphericity = float(np.mean(res_plane["sphericity"]))
        self.assertGreater(mean_planarity, 0.70, "Planaritatea pentru un acoperiș trebuie să fie > 0.70.")
        self.assertLess(mean_sphericity, 0.10, "Sfericitatea pentru un acoperiș trebuie să fie < 0.10.")

        # 2. Puncte sferice (coronament arbore - cluster Gaussian 3D izotrop)
        np.random.seed(42)
        tree_pts = np.random.normal(loc=[5.0, 5.0, 8.0], scale=1.5, size=(250, 3))
        res_tree = compute_3d_structural_features(tree_pts, radius_m=2.0)
        mean_tree_sphericity = float(np.mean(res_tree["sphericity"]))
        self.assertGreater(mean_tree_sphericity, 0.25, "Sfericitatea pentru vegetație densă trebuie să fie > 0.25.")

        # 3. Puncte liniare (stâlp / cablu LEA de-a lungul axei Z)
        line_z = np.linspace(0, 15, 60)
        line_pts = np.vstack([np.full_like(line_z, 5.0), np.full_like(line_z, 5.0), line_z]).T
        line_pts += np.random.normal(0, 0.01, line_pts.shape)
        res_line = compute_3d_structural_features(line_pts, radius_m=2.0)
        mean_linearity = float(np.mean(res_line["linearity"]))
        self.assertGreater(mean_linearity, 0.80, "Liniaritatea pentru un stâlp/cablu trebuie să fie > 0.80.")

    def test_calcan_aware_eave_retraction_standalone(self):
        """Verifică retragerea uniformă a streșinii pentru o clădire izolată fără calcan."""
        # Clădire 10x10 m (suprafață 100 mp)
        b = box(0, 0, 10, 10)
        retracted = apply_calcan_aware_eave_retraction(b, property_boundary=None, offset_eave_m=0.40)
        
        self.assertTrue(retracted.is_valid)
        # Amprenta la sol retrasă: 9.2 x 9.2 = 84.64 mp
        self.assertAlmostEqual(retracted.area, 84.64, places=1)
        self.assertAlmostEqual(retracted.bounds[0], 0.40, places=2)
        self.assertAlmostEqual(retracted.bounds[1], 0.40, places=2)
        self.assertAlmostEqual(retracted.bounds[2], 9.60, places=2)
        self.assertAlmostEqual(retracted.bounds[3], 9.60, places=2)

    def test_calcan_aware_eave_retraction_party_wall(self):
        """Verifică protecția strictă a peretelui de calcan (deplasare 0.00m) pe limita de proprietate."""
        # Clădire 10x10 m între (0, 0) și (10, 10)
        b = box(0, 0, 10, 10)
        # Limita parcelei trece pe linia x = 0 (peretele de vest este pe calcan)
        prop_line = LineString([(0, -10), (0, 20)])
        
        retracted = apply_calcan_aware_eave_retraction(
            b,
            property_boundary=prop_line,
            offset_eave_m=0.40,
            calcan_tol_m=0.15
        )
        
        self.assertTrue(retracted.is_valid)
        bounds = retracted.bounds
        
        # Muchia de vest (x = 0) trebuie conservată exact la 0.00 m (fără decalaj eronat spre interior)
        self.assertAlmostEqual(bounds[0], 0.00, places=2, msg="Zidul comun pe calcan trebuie să rămână la x=0.00m.")
        
        # Fațada estică (liberă) trebuie retrasă la 9.60 m
        self.assertAlmostEqual(bounds[2], 9.60, places=2, msg="Fațada liberă trebuie retrasă la x=9.60m.")
        
        # Fațada nordică și sudică libere trebuie retrase
        self.assertAlmostEqual(bounds[1], 0.40, places=2, msg="Fațada sudică trebuie retrasă la y=0.40m.")
        self.assertAlmostEqual(bounds[3], 9.60, places=2, msg="Fațada nordică trebuie retrasă la y=9.60m.")

    def test_calcan_aware_eave_retraction_adjacent_buildings(self):
        """Verifică protecția calcanului la două clădiri învecinate alipite."""
        b1 = box(0, 0, 10, 10)
        b2 = box(10, 0, 20, 10)  # Clădire alipită pe latura x = 10
        
        # Retragere b1 cu conștientizarea vecinului b2
        retracted_b1 = apply_eave_retraction_with_calcan(
            b1,
            adjacent_buildings=[b2],
            offset_eave_m=0.40,
            calcan_tol_m=0.10
        )
        
        self.assertTrue(retracted_b1.is_valid)
        # Latura estică a lui b1 (x = 10) este lipită de b2 -> trebuie să rămână la x = 10.00
        self.assertAlmostEqual(retracted_b1.bounds[2], 10.00, places=2, msg="Peretele comun dintre b1 și b2 trebuie să rămână la x=10.00m.")
        # Latura vestică liberă a lui b1 trebuie retrasă la x = 0.40
        self.assertAlmostEqual(retracted_b1.bounds[0], 0.40, places=2)


if __name__ == "__main__":
    unittest.main()
