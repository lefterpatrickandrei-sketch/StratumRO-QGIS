# -*- coding: utf-8 -*-
"""
Unit tests for Cadastral Vectorizer and 90-degree Orthogonalization.
"""

import os
import unittest
import numpy as np
import rasterio
from shapely.geometry import Polygon
from stratum_ro.vectorizer import CadastralVectorizer


class TestCadastralVectorizer(unittest.TestCase):

    def setUp(self):
        self.vectorizer = CadastralVectorizer(crs="EPSG:3844")

    def test_orthogonalize_slanted_rectangle(self):
        # Slightly slanted rectangle
        slanted_coords = [
            (10.0, 10.0),
            (20.2, 10.1),
            (20.1, 25.0),
            (9.9, 24.9),
            (10.0, 10.0)
        ]
        poly = Polygon(slanted_coords)
        ortho_poly = self.vectorizer.orthogonalize_polygon(poly, tolerance=0.5)

        self.assertTrue(ortho_poly.is_valid)
        self.assertGreater(ortho_poly.area, 50.0)

    def test_vectorize_synthetic_ndsm(self):
        # 50x50 synthetic nDSM with a 10x10 building in center
        ndsm = np.zeros((50, 50), dtype=np.float32)
        ndsm[15:25, 15:25] = 6.5  # 6.5m high building
        transform = rasterio.transform.from_origin(390000.0, 585000.0, 1.0, 1.0)

        buildings = self.vectorizer.vectorize_ndsm_buildings(
            ndsm_array=ndsm,
            transform=transform,
            min_height=2.5,
            min_area_m2=20.0,
            orthogonalize=True
        )

        self.assertEqual(len(buildings), 1)
        self.assertAlmostEqual(buildings[0]["area_m2"], 100.0, delta=10.0)
        self.assertEqual(buildings[0]["crs"], "EPSG:3844")

    def test_resolve_multipart_touching_blocks(self):
        """Verifică unificarea blocurilor alipite (evită spargerea în corpuri incomplete)."""
        from shapely.geometry import box, MultiPolygon
        from stratum_ro.geometry_utils import resolve_multipart_geometry
        b1 = box(0, 0, 10, 20)   # 200 mp
        b2 = box(10, 0, 20, 10)  # 100 mp
        mp = MultiPolygon([b1, b2])
        res = resolve_multipart_geometry(mp)
        self.assertEqual(res.geom_type, "Polygon")
        self.assertAlmostEqual(res.area, 300.0, places=1)

    def test_resolve_multipart_bridged_wings(self):
        """Verifică construirea punții structurale între aripi de clădire separate de rost/coridor."""
        from shapely.geometry import box, MultiPolygon
        from stratum_ro.geometry_utils import resolve_multipart_geometry
        b1 = box(0, 0, 10, 20)   # 200 mp
        b2 = box(11, 0, 21, 20)  # 200 mp, spațiu de 1.0m
        mp = MultiPolygon([b1, b2])
        res = resolve_multipart_geometry(mp, bridge_max_distance_m=1.5)
        self.assertEqual(res.geom_type, "Polygon")
        self.assertGreaterEqual(res.area, 400.0)

    def test_resolve_multipart_micro_noise_filtered(self):
        """Verifică eliminarea zgomotului parazit (< 8 mp) fără afectarea corpului principal."""
        from shapely.geometry import box, MultiPolygon
        from stratum_ro.geometry_utils import resolve_multipart_geometry
        b_main = box(0, 0, 20, 20)     # 400 mp
        b_noise = box(25, 25, 26, 27)  # 2 mp
        mp = MultiPolygon([b_main, b_noise])
        res = resolve_multipart_geometry(mp)
        self.assertEqual(res.geom_type, "Polygon")
        self.assertAlmostEqual(res.area, 400.0, places=1)

    def test_classify_temporary_container(self):
        """Verifică detectarea automată a containerelor modulare (20ft) și solariilor, protejând clădirile mari."""
        from shapely.geometry import box
        # Standard 20ft container: 2.44m x 6.06m ≈ 14.78 mp
        poly_container = box(0.0, 0.0, 2.44, 6.06)
        res = self.vectorizer.classify_temporary_structure(poly_container)
        self.assertTrue(res["is_temporary"])
        self.assertEqual(res["type"], "CONTAINER_MODULAR")

        # Clădire rezidențială normală: 10m x 12m = 120 mp
        poly_house = box(0.0, 0.0, 10.0, 12.0)
        res_house = self.vectorizer.classify_temporary_structure(poly_house)
        self.assertFalse(res_house["is_temporary"])
        self.assertEqual(res_house["type"], "CONSTRUCTIE_PERMANENTA")

        # Seră / solar alungit îngust: 6m x 36m (raport 6.0, arie 216 mp, H 4m)
        poly_greenhouse = box(0.0, 0.0, 6.0, 36.0)
        res_gh = self.vectorizer.classify_temporary_structure(poly_greenhouse, mean_height=3.8)
        self.assertTrue(res_gh["is_temporary"])
        self.assertEqual(res_gh["type"], "SERA_SOLAR_ALUNGIT")

        # Corp masiv de facultate / bloc alungit: 20m x 80m (raport 4.0, arie 1600 mp, H 15m) -> NU e provizoriu!
        poly_univ = box(0.0, 0.0, 20.0, 80.0)
        res_univ = self.vectorizer.classify_temporary_structure(poly_univ, mean_height=14.5)
        self.assertFalse(res_univ["is_temporary"])
        self.assertEqual(res_univ["type"], "CONSTRUCTIE_PERMANENTA")

    def test_split_at_calcan(self):
        """
        Verifică separarea automată la calcan (zid comun) a două corpuri de clădire
        adiacente cu treaptă de înălțime nDSM (P0.1 DoD).
        """
        from stratum_ro.geometry_utils import split_at_calcan
        from shapely.geometry import box
        from shapely.ops import unary_union

        # 1. Două dreptunghiuri adiacente de 300 mp fiecare (comun la X = 15.0)
        # Clădirea A: [0, 0, 15, 20], H = 4.0 m
        # Clădirea B: [15, 0, 30, 20], H = 8.5 m
        r1 = box(0.0, 0.0, 15.0, 20.0)
        r2 = box(15.0, 0.0, 30.0, 20.0)
        merged = unary_union([r1, r2])
        self.assertEqual(merged.area, 600.0)

        # Mock funcție nDSM altimetrică
        def mock_ndsm(x, y):
            return 4.0 if x < 15.0 else 8.5

        bodies = split_at_calcan(
            merged,
            ndsm_callable=mock_ndsm,
            min_split_area_m2=350.0,
            min_height_step_m=1.5
        )

        self.assertEqual(len(bodies), 2, "Clădirea contopită la calcan trebuie separată în 2 corpuri")
        for b in bodies:
            self.assertTrue(b.is_valid)
            self.assertAlmostEqual(b.area, 300.0, delta=25.0)

        # 2. Clădire compactă sub pragul minim (nu trebuie fragmentată eronat)
        small_bldg = box(0.0, 0.0, 10.0, 10.0)
        unaffected = split_at_calcan(small_bldg, min_split_area_m2=350.0)
        self.assertEqual(len(unaffected), 1)
        self.assertEqual(unaffected[0].area, 100.0)

    def test_format_hybrid_buildings_filter_temporary(self):
        """Verifică excluderea structurilor temporare când filter_temporary=True."""
        from shapely.geometry import box
        bldg_permanent = box(100.0, 100.0, 115.0, 120.0)  # 15m x 20m = 300 mp
        bldg_container = box(200.0, 200.0, 202.44, 206.06)  # 2.44m x 6.06m = 14.8 mp container
        bldg_polytunnel = box(300.0, 300.0, 305.0, 340.0)  # 5m x 40m = 200 mp solar alungit

        raw_inputs = [
            {"geometry": bldg_permanent, "sam2_score": 0.95, "mean_h": 6.5, "max_h": 8.0},
            {"geometry": bldg_container, "sam2_score": 0.88, "mean_h": 2.6, "max_h": 2.7},
            {"geometry": bldg_polytunnel, "sam2_score": 0.85, "mean_h": 3.5, "max_h": 4.0},
        ]

        # Fără filtru: toate cele 3 sunt păstrate și adnotate
        res_unfiltered = self.vectorizer.format_hybrid_buildings(raw_inputs, filter_temporary=False)
        self.assertEqual(len(res_unfiltered), 3)
        self.assertTrue(any(r["is_temporary"] and r["structure_type"] == "CONTAINER_MODULAR" for r in res_unfiltered))
        self.assertTrue(any(r["is_temporary"] and r["structure_type"] == "SERA_SOLAR_ALUNGIT" for r in res_unfiltered))

        # Cu filtru activat: doar clădirea permanentă este păstrată
        res_filtered = self.vectorizer.format_hybrid_buildings(raw_inputs, filter_temporary=True)
        self.assertEqual(len(res_filtered), 1)
        self.assertEqual(res_filtered[0]["structure_type"], "CONSTRUCTIE_PERMANENTA")
        self.assertFalse(res_filtered[0]["is_temporary"])


if __name__ == "__main__":
    unittest.main()


