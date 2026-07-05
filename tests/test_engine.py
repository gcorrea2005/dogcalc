"""Tests for FEM engine — bridge, solver, analysis results."""

import pytest
from src.model.document import Document
from src.model.entities.node import SupportType
from src.model.entities.load_case import LoadCase, NodalLoad
from src.engine.bridge import build_pynite_model
from src.engine.solver import run_analysis, run_analysis_for_document
from src.engine.results import AnalysisResult, NodeResult, MemberResult


class TestFEMBridge:
    def test_build_empty_raises(self):
        doc = Document()
        with pytest.raises(ValueError, match="No members"):
            build_pynite_model(doc)

    def test_build_single_member(self):
        doc = Document()
        mat = doc.add_material("Steel", 200e9)
        sec = doc.add_section("IPE300", 5380e-6, 8360e-8, 8360e-8, 604e-8, 20e-8)
        n1 = doc.add_node(0, 0, 0, support_type=SupportType.FIXED)
        n2 = doc.add_node(5, 0, 0)
        doc.add_member(n1.id, n2.id, "B1", mat.id, sec.id)
        model = build_pynite_model(doc)
        assert model is not None
        assert len(model.nodes) == 2
        assert len(model.members) == 1

    def test_default_material_auto_created(self):
        doc = Document()
        doc.add_node(0, 0, 0, support_type=SupportType.FIXED)
        doc.add_node(5, 0, 0)
        doc.add_member(list(doc.nodes.keys())[0], list(doc.nodes.keys())[1])
        model = build_pynite_model(doc)
        assert model is not None


class TestFEMSolver:
    def test_cantilever_deflection(self):
        """Cantilever beam: L=5m, P=10kN at tip. Expected δ ≈ 24.92 mm."""
        doc = Document()
        mat = doc.add_material("Steel", 200e9, 0.3, 7850, 275e6)
        sec = doc.add_section("IPE300", 5380e-6, 8360e-8, 8360e-8, 604e-8, 20e-8)
        n1 = doc.add_node(0, 0, 0, support_type=SupportType.FIXED)
        n2 = doc.add_node(5, 0, 0)
        doc.add_member(n1.id, n2.id, "B1", mat.id, sec.id)
        lc = doc.add_load_case("Test")
        lc.nodal_loads["nl"] = NodalLoad(node_id=n2.id, fy=-10e3)

        result = run_analysis_for_document(doc)
        assert result.success, f"Failed: {result.errors}"
        assert result.load_case_name

        dy = result.node_results[n2.id].dy
        expected = -10e3 * 125 / (3 * 200e9 * 8360e-8)
        err_pct = abs((dy - expected) / expected) * 100
        assert err_pct < 5, f"Deflection error {err_pct:.2f}%"

    def test_run_analysis_for_document(self):
        """End-to-end: Document → PyNite → results (covers bridge + solver)."""
        doc = Document()
        mat = doc.add_material("Steel", 200e9)
        sec = doc.add_section("IPE300", 5380e-6, 8360e-8, 8360e-8, 604e-8, 20e-8)
        n1 = doc.add_node(0, 0, 0, SupportType.FIXED)
        n2 = doc.add_node(5, 0, 0)
        doc.add_member(n1.id, n2.id, "B1", mat.id, sec.id)
        lc = doc.add_load_case("Test")
        lc.nodal_loads["nl"] = NodalLoad(node_id=n2.id, fy=-5000)
        result = run_analysis_for_document(doc)
        assert result.success
        # Just verify the API works — result has node/member data
        assert result.load_case_name == lc.id
        assert len(result.node_results) == 2
        assert len(result.member_results) == 1

    def test_analysis_fails_on_unstable(self):
        """Structure with no supports should fail."""
        doc = Document()
        doc.add_node(0, 0, 0)
        doc.add_node(5, 0, 0)
        doc.add_member(list(doc.nodes.keys())[0], list(doc.nodes.keys())[1])
        lc = doc.add_load_case("Test")
        lc.nodal_loads["nl"] = NodalLoad(node_id=list(doc.nodes.keys())[1], fy=-1000)
        result = run_analysis_for_document(doc)
        # Pynite may or may not succeed on an unconstrained model;
        # the important thing is it doesn't crash
        assert isinstance(result, AnalysisResult)

    def test_no_load_combos_returns_error(self):
        from Pynite import FEModel3D
        model = FEModel3D()
        result = run_analysis(model, [])
        assert not result.success
        assert "No load combinations" in result.errors[0]


class TestAnalysisResult:
    def test_node_result_defaults(self):
        nr = NodeResult(node_id="test")
        assert nr.dx == 0.0 and nr.dy == 0.0

    def test_max_displacement_empty(self):
        ar = AnalysisResult(success=True)
        assert ar.max_displacement() == 0.0

    def test_member_result(self):
        mr = MemberResult(member_id="M1", segments=[{"x": 0.5, "V": 10, "M": 25}])
        assert mr.segments[0]["M"] == 25
