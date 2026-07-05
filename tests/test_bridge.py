"""Tests for project file I/O — save/load roundtrip."""

import pytest
import tempfile
import os
from src.model.document import Document
from src.model.entities.node import SupportType
from src.model.entities.member import MemberType
from src.io.project_file import save_document, load_document


class TestProjectFile:
    def test_save_load_roundtrip(self):
        doc = Document()
        mat = doc.add_material("Steel", 200e9, 0.3, 7850, 275e6)
        sec = doc.add_section("IPE300", 5380e-6, 8360e-8, 8360e-8, 604e-8, 20e-8)
        n1 = doc.add_node(0, 0, 0, "N1", SupportType.FIXED)
        n2 = doc.add_node(5, 0, 0, "N2")
        n3 = doc.add_node(5, 3, 0, "N3")
        doc.add_member(n1.id, n2.id, "B1", mat.id, sec.id)
        doc.add_member(n2.id, n3.id, "C1", mat.id, sec.id, MemberType.COLUMN)

        with tempfile.NamedTemporaryFile(suffix=".dogcalc", delete=False) as f:
            tmp = f.name

        try:
            save_document(doc, tmp)
            loaded = load_document(tmp)

            assert loaded.node_count == 3
            assert loaded.member_count == 2
            assert loaded.nodes[n1.id].label == "N1"
            assert loaded.nodes[n1.id].support_type == SupportType.FIXED
            assert loaded.nodes[n1.id].x == 0.0
            assert loaded.materials[mat.id].name == "Steel"
            assert loaded.materials[mat.id].elastic_modulus == 200e9
            assert loaded.sections[sec.id].name == "IPE300"
            assert loaded.sections[sec.id].area == 5380e-6

            # Member type preserved
            m2 = loaded.members[list(loaded.members.keys())[1]]
            assert m2.member_type == MemberType.COLUMN
        finally:
            os.unlink(tmp)

    def test_load_nonexistent_file(self):
        with pytest.raises(FileNotFoundError):
            load_document("/nonexistent/path.dogcalc")

    def test_save_empty_document(self):
        doc = Document()
        with tempfile.NamedTemporaryFile(suffix=".dogcalc", delete=False) as f:
            tmp = f.name
        try:
            save_document(doc, tmp)
            loaded = load_document(tmp)
            assert loaded.node_count == 0
            assert loaded.member_count == 0
        finally:
            os.unlink(tmp)

    def test_save_preserves_coordinates(self):
        doc = Document()
        n = doc.add_node(1.234, 5.678, -9.012)
        with tempfile.NamedTemporaryFile(suffix=".dogcalc", delete=False) as f:
            tmp = f.name
        try:
            save_document(doc, tmp)
            loaded = load_document(tmp)
            loaded_n = loaded.nodes[n.id]
            assert loaded_n.x == pytest.approx(1.234)
            assert loaded_n.y == pytest.approx(5.678)
            assert loaded_n.z == pytest.approx(-9.012)
        finally:
            os.unlink(tmp)
