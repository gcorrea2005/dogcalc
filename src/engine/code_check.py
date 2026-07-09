"""NSR-10 / AISC 360-10 steel code check for axial members."""

import math
from dataclasses import dataclass


@dataclass
class CodeCheckResult:
    """Result for one member."""
    member_id: str
    label: str = ""
    section: str = ""
    axial_demand: float = 0.0    # kN
    axial_capacity: float = 0.0  # kN
    ratio: float = 0.0           # demand/capacity
    status: str = "OK"           # OK | OVERSTRESS
    length_m: float = 0.0        # member length


def check_member_axial(member_id: str, label: str, section: dict, material: dict,
                       length: float, axial_force: float, k_factor: float = 1.0) -> CodeCheckResult:
    """Check a single member for axial tension/compression per AISC 360-10.

    Args:
        member_id: member UUID
        label: member label (M1, M2, ...)
        section: dict with A, Ix, Iy, depth, width (m², m⁴, m)
        material: dict with Fy (kPa), E (kPa)
        length: member length in meters
        axial_force: max axial force in kN (positive = tension, negative = compression)
        k_factor: effective length factor (1.0 for pin-pin)

    Returns:
        CodeCheckResult with demand, capacity, ratio
    """
    A = section.get('A', 0.001)       # m²
    Iy = section.get('Iy', section.get('Ix', 1e-6))  # weak axis I
    Fy = material.get('Fy', 250e3)     # kPa (250 MPa default)
    E = material.get('E', 200e6)       # kPa
    Fu = material.get('Fu', 400e3)     # kPa

    # Radius of gyration (weak axis)
    r = math.sqrt(Iy / A) if A > 0 and Iy > 0 else 0.01

    abs_axial = abs(axial_force)  # kN

    if axial_force >= 0:
        # TENSION — AISC D2
        phi_yield = 0.90
        Pn_yield = Fy * A / 1000  # kN
        capacity = phi_yield * Pn_yield
    else:
        # COMPRESSION — AISC E3
        phi_c = 0.90
        KL_r = k_factor * length / r if r > 0 else 200
        Fe = math.pi**2 * E / (KL_r**2) / 1000  # kN/m² → kN (Euler stress in kPa)
        lambda_c = math.sqrt(Fy / (Fe * 1000)) if Fe > 0 else 3.0  # Fe in kPa

        if lambda_c <= 1.5:
            Fcr = (0.658 ** (lambda_c ** 2)) * Fy
        else:
            Fcr = (0.877 / (lambda_c ** 2)) * Fy

        Pn = Fcr * A / 1000  # kN
        capacity = phi_c * Pn

    ratio = abs_axial / capacity if capacity > 0 else 999.0
    status = "OK" if ratio <= 1.0 else "OVERSTRESS"

    return CodeCheckResult(
        member_id=member_id,
        label=label,
        section=section.get('name', '?'),
        axial_demand=axial_force,
        axial_capacity=capacity,
        ratio=ratio,
        status=status,
        length_m=length,
    )


def check_all_members(doc, envelope) -> list[CodeCheckResult]:
    """Check all members against envelope max axial forces.

    Args:
        doc: Document with members, sections, materials
        envelope: Envelope with max_axial dict

    Returns:
        List of CodeCheckResult sorted by ratio (worst first)
    """
    results = []
    sections = {s.id: {'name': s.name, 'A': s.area, 'Ix': s.ix, 'Iy': s.iy, 'Iz': s.iz, 'J': s.j}
                for s in doc.sections.values()}
    materials = {m.id: {'Fy': m.yield_strength, 'Fu': m.ultimate_strength, 'E': m.elastic_modulus}
                 for m in doc.materials.values()}
    # Apply code params if available (FYLD/FU from STAAD PARAMETER)
    fy_override = doc.code_params.get('fy', 0)
    fu_override = doc.code_params.get('fu', 0)
    if fy_override:
        for m in materials.values():
            m['Fy'] = fy_override
    if fu_override:
        for m in materials.values():
            m['Fu'] = fu_override

    for member in doc.members.values():
        axial = envelope.max_axial.get(member.id, 0.0)  # kN
        sec = sections.get(member.section_id, {})
        mat = materials.get(member.material_id, {})

        # Compute member length
        sn = doc.nodes.get(member.start_node_id)
        en = doc.nodes.get(member.end_node_id)
        if sn and en:
            length = math.sqrt((en.x - sn.x)**2 + (en.y - sn.y)**2 + (en.z - sn.z)**2)
        else:
            length = 1.0

        r = check_member_axial(
            member.id, member.label, sec, mat, length, axial, k_factor=1.0
        )
        results.append(r)

    results.sort(key=lambda x: x.ratio, reverse=True)
    return results
