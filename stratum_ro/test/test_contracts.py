# -*- coding: utf-8 -*-
"""
StratumRO — Phase 2 Architecture & Contract Test Suite
Validates type definitions, protocol conformance, data models, and boundary decoupling.
"""

import os
import sys

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import unittest
import numpy as np
from shapely.geometry import Polygon

from stratum_ro.contracts import (
    Coordinate2D,
    Coordinate3D,
    BoundingBox,
    CommonGeoObject,
    AxisOrder,
    CRSMetadata,
    ICRSManager,
    ITransformer,
    IGeometryEngine,
    DomainMaturity,
    DomainCapability,
    BaseDomainPack,
    TopoLTLayer,
    CadastralPoint,
    PADTableSpec,
    CPInterchangeSpec,
    VisionPromptType,
    VisionPrompt,
    VisionMaskResult,
    IVisionEngine,
    WorkflowStatus,
    ApprovalState,
    ApprovalRequest,
    ApprovalDecision,
    ValidationSeverity,
    ValidationIssue,
    ValidationReport,
    ProvenanceRecordContract,
    IQgisAdapter
)


class TestArchitectureContracts(unittest.TestCase):
    """
    Unit tests ensuring that all Phase 2 contracts and data models function correctly
    and provide strict boundary separation without affecting existing production code.
    """

    def test_01_common_geo_object_contracts(self):
        poly = Polygon([(0, 0), (10, 0), (10, 5), (0, 5)])
        geo_obj = CommonGeoObject(
            id="BLD_001",
            geometry=poly,
            crs="EPSG:3844",
            attributes={"destinatie": "Locuinta", "regim_inaltime": "P+1E"},
            metadata={"source": "SAM2_Ortho_Fusion"}
        )
        self.assertEqual(geo_obj.id, "BLD_001")
        self.assertEqual(geo_obj.crs, "EPSG:3844")
        self.assertFalse(geo_obj.is_3d)
        self.assertEqual(geo_obj.attributes["regim_inaltime"], "P+1E")

    def test_02_geodesy_and_crs_metadata_contracts(self):
        stereo70 = CRSMetadata(
            crs_id="EPSG:3844",
            epsg_code=3844,
            name="Pulkovo 1942(58) / Stereo 70",
            datum="Dealul Piscului 1970",
            ellipsoid="Krasovsky 1940",
            projection="Stereographic 1970",
            units="metre",
            axis_order=AxisOrder.NORTHING_EASTING
        )
        self.assertEqual(stereo70.epsg_code, 3844)
        self.assertEqual(stereo70.axis_order, AxisOrder.NORTHING_EASTING)
        self.assertEqual(stereo70.ellipsoid, "Krasovsky 1940")

    def test_03_domain_pack_abstraction(self):
        class MockCadastrePack(BaseDomainPack):
            @property
            def domain_id(self) -> str:
                return "cadastre_ro"

            @property
            def domain_name(self) -> str:
                return "Romanian Cadastre Domain Pack"

            @property
            def maturity(self) -> DomainMaturity:
                return DomainMaturity.MATURE

            def list_capabilities(self):
                return [
                    DomainCapability(
                        capability_name="pad_table_export",
                        description="Generates official PAD coordinate table",
                        input_types=["CommonGeoObject"],
                        output_types=["PADTableSpec"],
                        is_deterministic=True,
                        requires_ai_assistance=False
                    )
                ]

            def execute_capability(self, capability_name: str, inputs, **params):
                return "SUCCESS"

            def validate_deliverable(self, deliverable):
                return {"valid": True}

        pack = MockCadastrePack()
        self.assertEqual(pack.domain_id, "cadastre_ro")
        self.assertEqual(pack.maturity, DomainMaturity.MATURE)
        caps = pack.list_capabilities()
        self.assertEqual(len(caps), 1)
        self.assertTrue(caps[0].is_deterministic)

    def test_04_cadastral_point_and_pad_table_contracts(self):
        pt1 = CadastralPoint(point_id="1", x_nord=587123.456, y_est=391456.789)
        pt2 = CadastralPoint(point_id="2", x_nord=587130.123, y_est=391460.456)
        
        self.assertEqual(pt1.as_pad_row(), ("1", "587123.46", "391456.79"))
        
        pad = PADTableSpec(
            imobil_id="CAD_12345",
            points=[pt1, pt2],
            computed_area_m2=150.25,
            measured_area_m2=150.00
        )
        self.assertEqual(pad.point_count, 2)
        self.assertEqual(pad.destination, "Intravilan")

    def test_05_vision_engine_contracts_decoupling(self):
        prompt = VisionPrompt(
            prompt_type=VisionPromptType.BOUNDING_BOX,
            box=(10.0, 20.0, 110.0, 120.0)
        )
        mask = np.ones((256, 256), dtype=bool)
        result = VisionMaskResult(
            binary_mask=mask,
            iou_prediction=0.92,
            inference_time_ms=45.2
        )
        self.assertEqual(result.iou_prediction, 0.92)
        self.assertEqual(result.binary_mask.shape, (256, 256))
        self.assertEqual(prompt.prompt_type, VisionPromptType.BOUNDING_BOX)

    def test_06_approval_request_and_decision_lifecycle(self):
        req = ApprovalRequest(
            request_id="REQ_99",
            task_id="TASK_04",
            task_name="cadastral_boundary_modification",
            risk_level="HIGH",
            reason="Exceeds 0.10m tolerance threshold",
            proposed_payload={"delta_m": 0.14}
        )
        self.assertEqual(req.state, ApprovalState.PENDING)
        
        dec = ApprovalDecision(
            request_id="REQ_99",
            decision=ApprovalState.APPROVED,
            approver_id="SURVEYOR_RO_007",
            comments="Approved after physical field boundary inspection"
        )
        self.assertEqual(dec.decision, ApprovalState.APPROVED)
        self.assertEqual(dec.approver_id, "SURVEYOR_RO_007")

    def test_07_validation_contracts_reporting(self):
        issue1 = ValidationIssue(
            code="ANCPI_EAVE_OFFSET",
            message="Roof eave overhang not retracted",
            severity=ValidationSeverity.WARNING,
            feature_id="BLD_01"
        )
        issue2 = ValidationIssue(
            code="GEOS_SELF_INTERSECTION",
            message="Polygon self-intersects at vertex 4",
            severity=ValidationSeverity.CRITICAL,
            feature_id="BLD_02"
        )
        report = ValidationReport(
            is_valid=False,
            ruleset_name="ANCPI_600_2023_VALIDATION",
            total_features_checked=2,
            issues=[issue1, issue2]
        )
        self.assertFalse(report.is_valid)
        self.assertTrue(report.has_critical_errors)
        self.assertEqual(len(report.issues), 2)

    def test_08_provenance_contract_serialization(self):
        prov = ProvenanceRecordContract(
            activity_id="ACT_001",
            activity_name="90_deg_cadastral_regularization",
            input_hashes={"input.geojson": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"},
            parameters={"tolerance": 0.5, "algorithm": "orthogonalize_cad"},
            output_hashes={"output.geojson": "a1b2c3d4e5f60718293a4b5c6d7e8f90123456789abcdef0123456789abcdef0"},
            operator_id="antigravity"
        )
        self.assertEqual(prov.activity_id, "ACT_001")
        self.assertEqual(prov.parameters["tolerance"], 0.5)


if __name__ == "__main__":
    unittest.main()
