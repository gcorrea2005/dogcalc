"""Project file I/O — save/load .dogcalc files (SQLite format)."""

import sqlite3
from pathlib import Path
from src.model.entities.node import Node, SupportType
from src.model.entities.member import Member, MemberType
from src.model.entities.material import Material
from src.model.entities.section import Section


def save_document(doc, filepath: str):
    """Save all document entities to a SQLite file."""
    conn = sqlite3.connect(filepath)
    c = conn.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS nodes (
        id TEXT PRIMARY KEY, label TEXT, x REAL, y REAL, z REAL, support_type TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS members (
        id TEXT PRIMARY KEY, label TEXT, start_node_id TEXT, end_node_id TEXT,
        material_id TEXT, section_id TEXT, member_type TEXT)""")
    c.execute("""CREATE TABLE IF NOT EXISTS materials (
        id TEXT PRIMARY KEY, name TEXT, elastic_modulus REAL, poisson_ratio REAL,
        density REAL, yield_strength REAL)""")
    c.execute("""CREATE TABLE IF NOT EXISTS sections (
        id TEXT PRIMARY KEY, name TEXT, area REAL, ix REAL, iy REAL, iz REAL,
        j REAL, depth REAL, width REAL)""")
    c.execute("CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)")

    for table in ("nodes", "members", "materials", "sections"):
        c.execute(f"DELETE FROM {table}")

    for node in doc.nodes.values():
        c.execute("INSERT INTO nodes VALUES (?,?,?,?,?,?)",
                  (node.id, node.label, node.x, node.y, node.z, node.support_type.value))
    for member in doc.members.values():
        c.execute("INSERT INTO members VALUES (?,?,?,?,?,?,?)",
                  (member.id, member.label, member.start_node_id, member.end_node_id,
                   member.material_id, member.section_id, member.member_type.value))
    for mat in doc.materials.values():
        c.execute("INSERT INTO materials VALUES (?,?,?,?,?,?)",
                  (mat.id, mat.name, mat.elastic_modulus, mat.poisson_ratio,
                   mat.density, mat.yield_strength))
    for sec in doc.sections.values():
        c.execute("INSERT INTO sections VALUES (?,?,?,?,?,?,?,?,?)",
                  (sec.id, sec.name, sec.area, sec.ix, sec.iy, sec.iz, sec.j,
                   sec.depth, sec.width))

    c.execute("INSERT OR REPLACE INTO meta VALUES ('version', '1.0')")
    c.execute("INSERT OR REPLACE INTO meta VALUES ('units', ?)",
              (getattr(doc, 'units', 'metric'),))

    conn.commit()
    conn.close()
    doc._dirty = False


def load_document(filepath: str):
    """Load document from SQLite file. Returns Document or raises."""
    if not Path(filepath).exists():
        raise FileNotFoundError(f"File not found: {filepath}")

    from src.model.document import Document
    doc = Document()
    conn = sqlite3.connect(filepath)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()

    for row in c.execute("SELECT * FROM nodes"):
        node = Node(id=row["id"], label=row["label"],
                    x=row["x"], y=row["y"], z=row["z"],
                    support_type=SupportType(row["support_type"]))
        doc.nodes[node.id] = node

    for row in c.execute("SELECT * FROM members"):
        member = Member(id=row["id"], label=row["label"],
                        start_node_id=row["start_node_id"],
                        end_node_id=row["end_node_id"],
                        material_id=row["material_id"] or "",
                        section_id=row["section_id"] or "",
                        member_type=MemberType(row["member_type"]))
        doc.members[member.id] = member

    for row in c.execute("SELECT * FROM materials"):
        mat = Material(id=row["id"], name=row["name"],
                       elastic_modulus=row["elastic_modulus"],
                       poisson_ratio=row["poisson_ratio"],
                       density=row["density"],
                       yield_strength=row["yield_strength"])
        doc.materials[mat.id] = mat

    for row in c.execute("SELECT * FROM sections"):
        sec = Section(id=row["id"], name=row["name"],
                      area=row["area"], ix=row["ix"], iy=row["iy"],
                      iz=row["iz"], j=row["j"], depth=row["depth"],
                      width=row["width"])
        doc.sections[sec.id] = sec

    conn.close()
    doc._dirty = False
    return doc
