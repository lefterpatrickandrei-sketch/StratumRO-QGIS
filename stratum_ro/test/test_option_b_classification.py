# -*- coding: utf-8 -*-
"""Tests for tools/classify_option_b.py.

Synthetic tests always run. The real-data test skips with an explicit reason
when the required files or packages are absent; it never passes silently.
"""
import sys
import unittest
from pathlib import Path

from shapely.geometry import Polygon, box

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import classify_option_b as cob  # noqa: E402


def good_evidence(**over):
    ev = dict(touches_nodata=False, rgb_valid_fraction=1.0, height_valid_fraction=1.0,
              height_median_m=6.0, h90_m=7.0, route="OPTICAL_UNKNOWN_REVIEW")
    ev.update(over)
    return {"new": ev}


def case(cid, geom, proposal=True):
    return dict(candidate_id=cid, geometry=geom, is_proposal=proposal)


def by_id(results):
    return {r["candidate_id"]: r for r in results}


class ClassifierTests(unittest.TestCase):
    def setUp(self):
        self.a = box(0, 0, 10, 10)
        self.b = box(100, 0, 110, 10)
        self.c = box(200, 0, 210, 10)

    def run_cls(self, cases, evidence, **kw):
        return cob.classify(cases, evidence, **kw)

    def test_clean_case_passes_with_non_acceptance_status(self):
        res, summ = self.run_cls([case("X1", self.a)], {"X1": good_evidence()})
        self.assertEqual(res[0]["status"], cob.PASS_STATUS)
        self.assertNotIn("ADMIS", res[0]["status"].upper())
        self.assertIsNone(res[0]["primary_reason"])

    def test_partition_sums_to_total(self):
        cases = [case("P", self.a), case("N", self.b), case("M", self.c)]
        ev = {"P": good_evidence(), "N": good_evidence(touches_nodata=True)}  # M has no evidence
        res, summ = self.run_cls(cases, ev)
        self.assertEqual(summ["total"], 3)
        self.assertTrue(summ["partition_ok"])
        self.assertEqual(sum(summ["by_primary_reason"].values()) + summ["passed_pending_owner_review"], 3)

    def test_nodata_contact_is_read_from_evidence(self):
        res, _ = self.run_cls([case("N", self.a)], {"N": good_evidence(touches_nodata=True)})
        self.assertEqual(res[0]["primary_reason"], cob.NODATA_CONTACT)

    def test_missing_evidence_never_passes(self):
        res, _ = self.run_cls([case("M", self.a)], {})
        self.assertEqual(res[0]["status"], cob.FLAGGED_STATUS)
        self.assertEqual(res[0]["primary_reason"], cob.NO_SENSOR_EVIDENCE)

    def test_missing_field_never_passes(self):
        ev = good_evidence()
        del ev["new"]["touches_nodata"]
        res, _ = self.run_cls([case("F", self.a)], {"F": ev})
        self.assertEqual(res[0]["status"], cob.FLAGGED_STATUS)

    def test_low_height_is_measured_not_id_based(self):
        cases = [case("OPT_B_999:C1", self.a), case("OPT_B_210:C1", self.b)]
        ev = {"OPT_B_999:C1": good_evidence(height_median_m=0.9, h90_m=1.4),
              "OPT_B_210:C1": good_evidence(height_median_m=8.0)}
        res, _ = self.run_cls(cases, ev)
        r = by_id(res)
        self.assertEqual(r["OPT_B_999:C1"]["primary_reason"], cob.SUSPECT_SOL_SUB_1_8M)
        self.assertEqual(r["OPT_B_210:C1"]["status"], cob.PASS_STATUS)

    def test_partial_height_is_review_not_ground_veto(self):
        res, _ = self.run_cls([case("H", self.a)], {"H": good_evidence(height_valid_fraction=0.5)})
        self.assertEqual(res[0]["primary_reason"], cob.HEIGHT_MISSING_OR_PARTIAL)

    def test_vegetation_route_flagged(self):
        res, _ = self.run_cls([case("V", self.a)], {"V": good_evidence(route="LIKELY_VEGETATION_REVIEW")})
        self.assertEqual(res[0]["primary_reason"], cob.SUSPECT_VEGETATION)

    def test_upstream_diagnostic_not_proposal(self):
        res, _ = self.run_cls([case("U", self.a, proposal=False)], {"U": good_evidence()})
        self.assertEqual(res[0]["primary_reason"], cob.UPSTREAM_DIAGNOSTIC)

    def test_stale_evidence_blocks_unless_explicitly_accepted(self):
        res, summ = self.run_cls([case("S", self.a)], {"S": good_evidence()}, stale_reason="SOURCE_HASH_MISMATCH")
        self.assertEqual(res[0]["primary_reason"], cob.EVIDENCE_STALE)
        res2, summ2 = self.run_cls([case("S", self.a)], {"S": good_evidence()},
                                   stale_reason="SOURCE_HASH_MISMATCH", accept_stale=True)
        self.assertEqual(res2[0]["status"], cob.PASS_STATUS)
        self.assertTrue(summ2["evidence_stale_accepted"])

    def test_contained_overlap_blocks_smaller_only(self):
        big = box(0, 0, 20, 20)
        small = box(2, 2, 8, 8)
        res, summ = self.run_cls([case("BIG", big), case("SMALL", small)],
                                 {"BIG": good_evidence(), "SMALL": good_evidence()})
        r = by_id(res)
        self.assertEqual(r["SMALL"]["primary_reason"], cob.OVERLAP_CONTAINED)
        self.assertEqual(r["BIG"]["status"], cob.PASS_STATUS)
        self.assertIn(cob.OVERLAP_CONTAINS_OTHER, [f["code"] for f in r["BIG"]["flags"]])
        self.assertEqual(summ["overlap_pairs"], 1)

    def test_seam_overlap_blocks_both(self):
        a = box(0, 0, 10, 10)
        b = box(9, 0, 19, 10)   # 10 m2 overlap, 10% containment
        res, _ = self.run_cls([case("A", a), case("B", b)], {"A": good_evidence(), "B": good_evidence()})
        self.assertTrue(all(r["primary_reason"] == cob.OVERLAP_SEAM for r in res))

    def test_overlap_with_flagged_partner_is_informational(self):
        a = box(0, 0, 10, 10)
        b = box(5, 0, 15, 10)
        res, _ = self.run_cls([case("A", a), case("B", b)],
                              {"A": good_evidence(), "B": good_evidence(touches_nodata=True)})
        r = by_id(res)
        self.assertEqual(r["A"]["status"], cob.PASS_STATUS)
        self.assertEqual(r["B"]["primary_reason"], cob.NODATA_CONTACT)

    def test_geometry_artifacts_blocking_depends_on_stage(self):
        spike = Polygon([(0, 0), (10, 0), (10, 10), (5.2, 10), (5, 30), (4.8, 10), (0, 10)])
        ev = {"SP": good_evidence()}
        cleaned, _ = self.run_cls([case("SP", spike)], ev, geometry_artifacts_blocking=True)
        raw, _ = self.run_cls([case("SP", spike)], ev, geometry_artifacts_blocking=False)
        self.assertEqual(cleaned[0]["primary_reason"], cob.ACUTE_ANGLE)
        self.assertEqual(raw[0]["status"], cob.PASS_STATUS)
        self.assertIn(cob.ACUTE_ANGLE, [f["code"] for f in raw[0]["flags"]])

    def test_spurious_hole_and_duplicate_nodes(self):
        holed = Polygon([(0, 0), (10, 0), (10, 10), (0, 10)], [[(4, 4), (5, 4), (5, 5), (4, 5)]])
        dup = Polygon([(0, 0), (10, 0), (10, 0), (10, 10), (0, 10)])
        res, _ = self.run_cls([case("H", holed), case("D", dup)],
                              {"H": good_evidence(), "D": good_evidence()})
        r = by_id(res)
        self.assertEqual(r["H"]["primary_reason"], cob.SPURIOUS_HOLE)
        self.assertEqual(r["D"]["primary_reason"], cob.DUPLICATE_NODES)

    def test_geometry_is_not_modified(self):
        a = box(0, 0, 10, 10)
        b = box(9, 0, 19, 10)
        wkb_before = (a.wkb, b.wkb)
        self.run_cls([case("A", a), case("B", b)], {"A": good_evidence(), "B": good_evidence()})
        self.assertEqual((a.wkb, b.wkb), wkb_before)

    def test_duplicate_ids_rejected(self):
        with self.assertRaises(ValueError):
            self.run_cls([case("A", self.a), case("A", self.b)], {})

    def test_invalid_geometry_flagged(self):
        bow = Polygon([(0, 0), (10, 10), (10, 0), (0, 10)])  # self-intersecting
        res, _ = self.run_cls([case("I", bow)], {"I": good_evidence()})
        self.assertEqual(res[0]["primary_reason"], cob.INVALID_GEOMETRY)


class RealDataTests(unittest.TestCase):
    """Partition check on the real 216 cases; skips with a reason if inputs are absent."""

    def test_all_216_cases_partitioned_with_reason(self):
        try:
            import geopandas  # noqa: F401
            import pyogrio  # noqa: F401
        except ImportError as exc:
            self.skipTest(f"geopandas/pyogrio not installed: {exc}")
        for p in (cob.DEFAULT_SOURCE_GPKG, cob.DEFAULT_EVIDENCE):
            if not p.exists():
                self.skipTest(f"required input missing: {p}")
        results, summary = cob.run(cob.DEFAULT_SOURCE_GPKG, "B_SIMPLE", "B_ROOF_PROPOSALS",
                                   cob.DEFAULT_EVIDENCE, accept_stale=True,
                                   geometry_artifacts_blocking=False)
        self.assertEqual(summary["total"], 216)
        self.assertTrue(summary["partition_ok"])
        for r in results:
            if r["status"] == cob.FLAGGED_STATUS:
                self.assertIsNotNone(r["primary_reason"], r["candidate_id"])
        self.assertNotIn("ADMIS", " ".join(r["status"] for r in results).upper())


if __name__ == "__main__":
    unittest.main()
