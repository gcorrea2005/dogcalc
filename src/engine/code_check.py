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
    moment_demand: float = 0.0   # kN-m (strong axis Mz)
    moment_capacity: float = 0.0 # kN-m
    shear_demand: float = 0.0    # kN (Vy)
    shear_capacity: float = 0.0  # kN
    ratio: float = 0.0           # demand/capacity (governing)
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
        Pn_yield = Fy * A  # kN (Fy in kPa × A in m² = kN)
        capacity = phi_yield * Pn_yield
    else:
        # COMPRESSION — AISC E3
        phi_c = 0.90
        KL_r = k_factor * length / r if r > 0 else 200
        Fe = math.pi**2 * E / (KL_r**2)  # kPa (Euler stress)
        lambda_c = math.sqrt(Fy / Fe) if Fe > 0 else 3.0

        if lambda_c <= 1.5:
            Fcr = (0.658 ** (lambda_c ** 2)) * Fy
        else:
            Fcr = (0.877 / (lambda_c ** 2)) * Fy

        Pn = Fcr * A  # kN
        capacity = phi_c * Pn

    ratio = abs_axial / capacity if capacity > 0 else 999.0
    status = "OK" if ratio <= 1.0 else "OVERSTRESS"

    return CodeCheckResult(
        member_id=member_id,
        label=label,
        section=section.get('name', '?'),
        axial_demand=axial_force,
        axial_capacity=capacity,
        moment_demand=0.0,
        moment_capacity=0.0,
        shear_demand=0.0,
        shear_capacity=0.0,
        ratio=ratio,
        status=status,
        length_m=length,
    )


def _section_modulus_sx(sec: dict) -> float:
    """Compute elastic section modulus Sx (m³) from sec properties."""
    Ix = sec.get('Ix', sec.get('ix', 1e-4))
    depth = sec.get('depth', 0.3)
    return Ix / (depth / 2) if depth > 0 else 1e-4


def _shear_area_vy(sec: dict) -> float:
    """Approximate shear area for Vy (web area)."""
    depth = sec.get('depth', 0.3)
    # Estimate web thickness from area/depth ratio for C-channels
    A = sec.get('A', 0.001)
    web_t = A / (depth + 2 * 0.065)  # rough estimate for C-channel
    return depth * web_t


def check_member_bending(result: CodeCheckResult, sec: dict, mat: dict,
                         moment: float, shear: float) -> CodeCheckResult:
    """Check bending (AISC F) and shear (AISC G) for a member.

    Args:
        result: existing CodeCheckResult (with axial data)
        sec: section dict with A, Ix, Iy, depth, width
        mat: material dict with Fy, E
        moment: max absolute moment Mz (kN-m)
        shear: max absolute shear Vy (kN)

    Returns:
        Updated CodeCheckResult with moment/shear data and governing ratio.
    """
    phi_b = 0.90  # AISC F1
    phi_v = 0.90  # AISC G1

    Fy = mat.get('Fy', 250e3)  # kPa
    E = mat.get('E', 200e6)    # kPa

    # ── Moment capacity (AISC F5 for channels, conservative elastic) ──
    Sx = _section_modulus_sx(sec)
    # Conservative: use elastic Sx (valid for non-compact/slender sections)
    # Inelastic reserve or plastic: Zx ≈ 1.2*Sx typical for C-channels
    Zx = Sx * 1.2
    Mn = Fy * Zx  # kN-m (Fy in kPa × m³ = kN·m)
    moment_cap = phi_b * Mn

    # ── Shear capacity (AISC G2) ──
    Aw = _shear_area_vy(sec)
    Cv = 1.0  # conservative compact web assumption
    Vn = 0.6 * Fy * Aw * Cv  # kN
    shear_cap = phi_v * Vn

    # ── Combined ratio per AISC H1-1a ──
    result.moment_demand = moment
    result.moment_capacity = round(moment_cap, 3)
    result.shear_demand = shear
    result.shear_capacity = round(shear_cap, 3)

    ratios = []
    if result.axial_capacity > 0:
        ratios.append(abs(result.axial_demand) / result.axial_capacity)
    if moment_cap > 0:
        ratios.append(abs(moment) / moment_cap)
    if shear_cap > 0:
        ratios.append(abs(shear) / shear_cap)

    max_r = max(ratios) if ratios else 0
    result.ratio = round(max_r, 3)
    result.status = "OK" if max_r <= 1.0 else "OVERSTRESS"
    return result


def check_all_members(doc, envelope) -> list[CodeCheckResult]:
    """Check all members against envelope max axial forces.

    Args:
        doc: Document with members, sections, materials
        envelope: Envelope with max_axial dict

    Returns:
        List of CodeCheckResult sorted by ratio (worst first)
    """
    results = []
    sections = {s.id: {'name': s.name, 'A': s.area, 'Ix': s.ix, 'Iy': s.iy, 'Iz': s.iz, 'J': s.j,
                       'depth': s.depth, 'width': s.width}
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
        moment = envelope.max_moment_z.get(member.id, 0.0)  # kN-m
        shear = envelope.max_shear_y.get(member.id, 0.0)  # kN
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
        r = check_member_bending(r, sec, mat, moment, shear)
        results.append(r)

    results.sort(key=lambda x: x.ratio, reverse=True)
    return results
