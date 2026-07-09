"""Bridge: converts DogCalC Document → PyNite FEModel3D.

This is the translation layer between our data model and the FEM engine.
If we ever swap PyNite for OpenSeesPy, only this file changes.
"""

from Pynite import FEModel3D
from src.model.entities.node import SupportType


def build_pynite_model(doc) -> FEModel3D:
    """Build a PyNite FEModel3D from a DogCalC Document.

    Args:
        doc: Document instance with nodes, members, materials, sections, load cases.

    Returns:
        FEModel3D ready for analysis.

    Raises:
        ValueError: if no members are defined or nodes are missing.
    """
    if doc.member_count == 0:
        raise ValueError("No members defined — cannot build FEM model")

    model = FEModel3D()

    # ── 1. Add nodes ──
    for node in doc.nodes.values():
        model.add_node(node.id, node.x, node.y, node.z)

    # ── 2. Add supports ──
    for node in doc.nodes.values():
        if node.support_type != SupportType.FREE:
            flags = _support_flags(node.support_type)
            model.def_support(node.id, *flags)

    # ── 3. Add materials ──
    _ensure_default_material(doc)
    for mat in doc.materials.values():
        model.add_material(
            mat.id,
            mat.elastic_modulus,
            G=mat.shear_modulus,
            nu=mat.poisson_ratio,
            rho=mat.density,
        )

    # ── 3.5. Add sections (PyNite v3 requires named sections) ──
    if not doc.sections:
        _ensure_default_section(doc)
    for sec in doc.sections.values():
        model.add_section(sec.id, sec.area, sec.ix, sec.iy, sec.j)

    # ── 4. Add members (frame elements) ──
    for member in doc.members.values():
        mat_id = member.material_id if member.material_id else "Default"
        sec_id = member.section_id if member.section_id else "Default"

        model.add_member(
            member.id,
            member.start_node_id,
            member.end_node_id,
            mat_id,
            sec_id,
        )

    # ── 5. Add loads ──
    for lc in doc.load_cases.values():
        combo_name = lc.id
        model.add_load_combo(combo_name, factors={combo_name: 1.0})

        # Nodal loads
        for nl in lc.nodal_loads.values():
            if nl.fx:
                model.add_node_load(nl.node_id, 'FX', nl.fx, case=combo_name)
            if nl.fy:
                model.add_node_load(nl.node_id, 'FY', nl.fy, case=combo_name)
            if nl.fz:
                model.add_node_load(nl.node_id, 'FZ', nl.fz, case=combo_name)
            if nl.mx:
                model.add_node_load(nl.node_id, 'MX', nl.mx, case=combo_name)
            if nl.my:
                model.add_node_load(nl.node_id, 'MY', nl.my, case=combo_name)
            if nl.mz:
                model.add_node_load(nl.node_id, 'MZ', nl.mz, case=combo_name)

        # Member distributed loads
        for ml in lc.member_loads.values():
            dir_map = {'local_y': 'Fy', 'local_z': 'Fz', 'axial': 'Fx'}
            direction = dir_map.get(ml.direction, 'Fy')
            model.add_member_dist_load(
                ml.member_id, direction, ml.w1, ml.w2,
                x1=0.0, x2=1.0, case=combo_name,
            )

        # Self-weight
        if lc.include_self_weight:
            for member in doc.members.values():
                sec = doc.sections.get(member.section_id)
                mat = doc.materials.get(member.material_id)
                if sec and mat:
                    w = -sec.area * mat.density * 9.81 / 1000  # kN/m in -Y
                    model.add_member_dist_load(
                        member.id, 'Fy', w, w,
                        x1=0.0, x2=1.0, case=combo_name,
                    )

    return model


def _support_flags(st: SupportType) -> tuple[bool, bool, bool, bool, bool, bool]:
    """Convert SupportType to PyNite restraint flags (DX, DY, DZ, RX, RY, RZ)."""
    mapping = {
        SupportType.FREE:      (False, False, False, False, False, False),
        SupportType.PINNED:    (True,  True,  True,  False, False, False),
        SupportType.FIXED:     (True,  True,  True,  True,  True,  True),
        SupportType.ROLLER_X:  (False, True,  True,  False, False, False),
        SupportType.ROLLER_Y:  (True,  False, True,  False, False, False),
        SupportType.ROLLER_Z:  (True,  True,  False, False, False, False),
    }
    return mapping.get(st, mapping[SupportType.FREE])


def _ensure_default_section(doc):
    """Create a default section if none exists."""
    if not doc.sections:
        from src.model.entities.section import Section
        sec = Section(
            id="Default", name="Default (0.01 m²)",
            area=0.01, ix=1e-4, iy=1e-4, iz=1e-6, j=1e-6,
        )
        doc.sections[sec.id] = sec


def _ensure_default_material(doc):
    """Create a default steel material if none exists."""
    if not doc.materials:
        from src.model.entities.material import Material
        mat = Material(
            id="Default", name="Steel (default)",
            elastic_modulus=200e9, poisson_ratio=0.3,
            density=7850.0, yield_strength=275e6,
        )
        doc.materials[mat.id] = mat
