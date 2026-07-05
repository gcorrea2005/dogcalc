"""Tests for Document model — CRUD, cascade delete, support types."""

import pytest
from src.model.document import Document
from src.model.entities.node import SupportType


class TestDocument:
    def test_add_node(self):
        doc = Document()
        n = doc.add_node(1, 2, 3, "N1")
        assert doc.node_count == 1
        assert n.label == "N1"
        assert n.x == 1 and n.y == 2 and n.z == 3

    def test_add_member(self):
        doc = Document()
        n1 = doc.add_node(0, 0, 0)
        n2 = doc.add_node(5, 0, 0)
        m = doc.add_member(n1.id, n2.id, "M1")
        assert doc.member_count == 1
        assert m.start_node_id == n1.id
        assert m.end_node_id == n2.id

    def test_member_requires_existing_nodes(self):
        doc = Document()
        n1 = doc.add_node(0, 0, 0)
        with pytest.raises(ValueError):
            doc.add_member(n1.id, "nonexistent")

    def test_member_cannot_connect_same_node(self):
        doc = Document()
        n1 = doc.add_node(0, 0, 0)
        with pytest.raises(ValueError):
            doc.add_member(n1.id, n1.id)

    def test_delete_node_cascades_members(self):
        doc = Document()
        n1 = doc.add_node(0, 0, 0)
        n2 = doc.add_node(5, 0, 0)
        doc.add_member(n1.id, n2.id)
        doc.delete_entity(n1.id)
        assert doc.node_count == 1   # only n2 remains
        assert doc.member_count == 0  # member cascaded

    def test_delete_member_only(self):
        doc = Document()
        n1 = doc.add_node(0, 0, 0)
        n2 = doc.add_node(5, 0, 0)
        m = doc.add_member(n1.id, n2.id)
        doc.delete_entity(m.id)
        assert doc.node_count == 2
        assert doc.member_count == 0

    def test_support_types(self):
        doc = Document()
        for st in (SupportType.FIXED, SupportType.PINNED,
                    SupportType.ROLLER_X, SupportType.FREE):
            n = doc.add_node(0, 0, 0, support_type=st)
            assert n.support_type == st
            assert n.is_supported == (st != SupportType.FREE)

    def test_material_operations(self):
        doc = Document()
        mat = doc.add_material("Steel", 200e9, 0.3, 7850, 275e6)
        assert len(doc.materials) == 1
        assert mat.shear_modulus == pytest.approx(200e9 / (2 * 1.3), rel=0.01)

    def test_section_operations(self):
        doc = Document()
        sec = doc.add_section("IPE300", 5380e-6, 8360e-8, 8360e-8, 604e-8, 20e-8)
        assert len(doc.sections) == 1
        assert sec.iy_strong == 8360e-8

    def test_load_case_operations(self):
        doc = Document()
        lc = doc.add_load_case("Dead", "dead")
        assert len(doc.load_cases) == 1
        assert lc.load_type == "dead"

    def test_dirty_flag(self):
        doc = Document()
        assert not doc.is_dirty
        doc.add_node(0, 0, 0)
        assert doc.is_dirty

    def test_node_list_order(self):
        doc = Document()
        n1 = doc.add_node(0, 0, 0, "A")
        n2 = doc.add_node(1, 0, 0, "B")
        n3 = doc.add_node(2, 0, 0, "C")
        nodes = doc.node_list()
        assert nodes[0].label == "A"
        assert nodes[2].label == "C"
