"""STAAD .std file parser and writer.

Bidirectional: reads .std → Document, writes Document → .std.

STAAD input file structure (simplified):
  STAAD SPACE
  START JOB INFORMATION
  ...
  END JOB INFORMATION
  INPUT WIDTH 79
  UNIT METER KN
  JOINT COORDINATES
  <id> <x> <y> <z>
  MEMBER INCIDENCES
  <id> <start> <end>
  MEMBER PROPERTY
  <id> TABLE ST <section_name>
  DEFINE MATERIAL START
  ISOTROPIC <name>
  E <value>
  POISSON <value>
  DENSITY <value>
  END DEFINE MATERIAL
  CONSTANTS
  MATERIAL <name> ALL
  SUPPORTS
  <id> FIXED
  LOAD <n> LOADTYPE <type>
  JOINT LOAD
  <id> FY <value>
  PERFORM ANALYSIS
  FINISH
"""

import re
from pathlib import Path
from collections import OrderedDict
from src.model.document import Document
from src.model.entities.node import Node, SupportType
from src.model.entities.member import Member, MemberType
from src.model.entities.material import Material
from src.model.entities.section import Section
from src.model.entities.load_case import LoadCase, NodalLoad


# ── Section name → properties lookup (common steel sections) ──
STEEL_SECTIONS = {
    "W12X26":  dict(A=4935e-6, Ix=8490e-8, Iy=8490e-8, Iz=240e-8, J=20e-8, depth=0.310, width=0.165),
    "W12X40":  dict(A=7610e-6, Ix=12900e-8, Iy=12900e-8, Iz=430e-8, J=30e-8, depth=0.310, width=0.205),
    "W14X22":  dict(A=4180e-6, Ix=8280e-8, Iy=8280e-8, Iz=155e-8, J=12e-8, depth=0.349, width=0.127),
    "W14X30":  dict(A=5710e-6, Ix=12100e-8, Iy=12100e-8, Iz=230e-8, J=18e-8, depth=0.352, width=0.170),
    "IPE300":  dict(A=5380e-6, Ix=8360e-8, Iy=8360e-8, Iz=604e-8, J=20e-8, depth=0.300, width=0.150),
    "IPE400":  dict(A=8450e-6, Ix=23130e-8, Iy=23130e-8, Iz=1320e-8, J=51e-8, depth=0.400, width=0.180),
    "HEA200":  dict(A=5380e-6, Ix=3690e-8, Iy=3690e-8, Iz=1340e-8, J=21e-8, depth=0.190, width=0.200),
    "HEA300":  dict(A=11300e-6, Ix=18260e-8, Iy=18260e-8, Iz=6310e-8, J=85e-8, depth=0.290, width=0.300),
    "TUBO70x4": dict(A=1056e-6, Ix=76.95e-8, Iy=76.95e-8, Iz=76.95e-8, J=153.9e-8, depth=0.070, width=0.070),
    "TUBO70X4": dict(A=1056e-6, Ix=76.95e-8, Iy=76.95e-8, Iz=76.95e-8, J=153.9e-8, depth=0.070, width=0.070),
}


# ── Parse .std → Document ──────────────────────────

def parse_std(filepath: str) -> Document:
    """Parse a STAAD .std file into a DogCalC Document.

    Supports: SPACE structures, joints, members, materials, sections,
              supports, joint loads, member loads, load cases.
    """
    if not Path(filepath).exists():
        raise FileNotFoundError(filepath)

    text = Path(filepath).read_text()
    lines = text.split("\n")

    doc = Document()
    ctx = _ParseContext(doc, filepath)

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Skip comments and empty
        if not line or line.startswith("*") or line.startswith("#"):
            i += 1
            continue

        upper = line.upper()

        # Envelope — must be checked BEFORE _is_section_header which also matches it
        if upper.startswith("DEFINE ENVELOPE"):
            i = _parse_envelope(lines, i + 1, ctx)
            continue

        # Skip parameters / code check (future)
        if upper.startswith("PARAMETER") or upper.startswith("CHECK CODE") or upper.startswith("STEEL"):
            i += 1
            continue

        if upper.startswith("CODE "):
            ctx.code = line
            i += 1
            continue

        if upper.startswith("FYLD "):
            try:
                ctx.fy = float(line.split()[1])
            except (ValueError, IndexError):
                pass
            i += 1
            continue

        if upper.startswith("FU "):
            try:
                ctx.fu = float(line.split()[1])
            except (ValueError, IndexError):
                pass
            i += 1
            continue

        if upper.startswith("TRACK "):
            i += 1
            continue

        if _is_section_header(line):
            if upper.startswith("STAAD"):
                ctx.structure_type = _parse_staad_header(line)
            elif upper == "START JOB INFORMATION":
                i = _skip_until(lines, i, "END JOB INFORMATION")
            elif upper.startswith("INPUT WIDTH"):
                pass  # ignore
            elif upper.startswith("UNIT"):
                ctx.units = line

            # Joints
            elif upper == "JOINT COORDINATES":
                i = _parse_joints(lines, i, ctx)

            # Members
            elif upper == "MEMBER INCIDENCES":
                i = _parse_members(lines, i, ctx)

            # Member properties → sections
            elif upper.startswith("MEMBER PROPERTY"):
                i = _parse_member_property(lines, i, ctx)

            # Materials
            elif upper == "DEFINE MATERIAL START":
                i = _parse_materials(lines, i, ctx)

            # Material assignments
            elif upper == "CONSTANTS":
                i = _parse_constants(lines, i, ctx)

            # Supports
            elif upper == "SUPPORTS":
                i = _parse_supports(lines, i, ctx)

            # Member releases
            elif upper.startswith("MEMBER RELEASE"):
                i = _parse_member_releases(lines, i + 1, ctx)

            # Loads (but not LOAD COMBINATION)
            elif upper.startswith("LOAD ") and not upper.startswith("LOAD COMB"):
                i = _parse_load_case(lines, i, ctx)

            # Load combinations
            elif upper.startswith("LOAD COMBINATION") or upper.startswith("LOAD COMB"):
                i = _parse_load_combination(lines, i, ctx)

            # Analysis trigger
            elif upper == "PERFORM ANALYSIS":
                pass  # just a marker

            # End
            elif upper == "FINISH":
                break

        i += 1

    doc.code_params = {'fy': ctx.fy, 'fu': ctx.fu, 'code': ctx.code}
    return doc


class _ParseContext:
    def __init__(self, doc, filepath):
        self.doc = doc
        self.filepath = filepath
        self.structure_type = "SPACE"
        self.units = "UNIT METER KN"
        self._default_mat_id = None
        self._default_sec_id = None
        self.code = ""
        self.fy = 250000  # kPa default
        self.fu = 400000  # kPa default


def _parse_staad_header(line: str) -> str:
    parts = line.upper().split()
    if len(parts) > 1 and parts[1] in ("SPACE", "PLANE", "TRUSS", "FLOOR"):
        return parts[1]
    return "SPACE"


def _skip_until(lines, i, end_marker: str) -> int:
    """Skip lines until end_marker is found. Returns index of end_marker line."""
    i += 1
    while i < len(lines):
        if lines[i].strip().upper() == end_marker:
            return i
        i += 1
    return i


def _parse_joints(lines, i, ctx) -> int:
    """Parse JOINT COORDINATES section."""
    i += 1
    while i < len(lines):
        line = lines[i].strip()
        if not line or _is_section_header(line):
            return i - 1

        # Handle semicolons (multiple joints per line)
        for part in line.replace(";", "\n").split("\n"):
            part = part.strip()
            if not part:
                continue
            nums = part.split()
            if len(nums) >= 4:
                try:
                    jid = nums[0]
                    x, y, z = float(nums[1]), float(nums[2]), float(nums[3])
                    ctx.doc.add_node(x, y, z, f"N{jid}")
                except ValueError:
                    pass
        i += 1
    return i


def _is_section_header(line: str) -> bool:
    """Check if line starts a new STAAD section."""
    u = line.upper()
    return any(u.startswith(k) for k in (
        "MEMBER ", "JOINT ", "DEFINE ", "CONSTANTS", "SUPPORTS",
        "LOAD ", "PERFORM ", "FINISH", "UNIT ", "END ", "START ",
    ))


def _parse_members(lines, i, ctx) -> int:
    """Parse MEMBER INCIDENCES section."""
    i += 1
    while i < len(lines):
        line = lines[i].strip()
        if not line or _is_section_header(line):
            return i - 1

        for part in line.replace(";", "\n").split("\n"):
            part = part.strip()
            if not part:
                continue
            nums = part.split()
            if len(nums) >= 3:
                try:
                    mid, start, end = nums[0], nums[1], nums[2]
                    nids = list(ctx.doc.nodes.keys())
                    # Find node matching label N<start> and N<end>
                    sn = _find_node_by_label(ctx.doc, f"N{start}")
                    en = _find_node_by_label(ctx.doc, f"N{end}")
                    if sn and en:
                        ctx.doc.add_member(sn, en, f"M{mid}")
                except ValueError:
                    pass
        i += 1
    return i


def _find_node_by_label(doc, label: str) -> str | None:
    for nid, node in doc.nodes.items():
        if node.label == label:
            return nid
    return None


def _parse_member_property(lines, i, ctx) -> int:
    """Parse MEMBER PROPERTY section — maps members to sections."""
    i += 1
    while i < len(lines):
        line = lines[i].strip()
        if not line or _is_section_header(line):
            return i - 1

        upper = line.upper()
        # Format: <member_list> TABLE ST <section_name>
        if "TABLE" in upper:
            parts = line.split()
            member_ids = []
            sec_name = None
            table_idx = None
            for j, p in enumerate(parts):
                if p.upper() == "TABLE":
                    table_idx = j
                    break
            if table_idx:
                member_ids = parts[:table_idx]
                if table_idx + 2 < len(parts):
                    sec_name = parts[table_idx + 2]

            if sec_name:
                sec_props = STEEL_SECTIONS.get(sec_name.upper())
                if sec_props:
                    sec = ctx.doc.add_section(sec_name,
                        area=sec_props.get("A", 0.01),
                        ix=sec_props.get("Ix", 1e-4),
                        iy=sec_props.get("Iy", 1e-4),
                        iz=sec_props.get("Iz", 1e-6),
                        j=sec_props.get("J", 1e-6),
                        depth=sec_props.get("depth", 0.3),
                        width=sec_props.get("width", 0.15))
                    ctx._default_sec_id = sec.id

                    # Expand member range (e.g., "1 TO 6" → 1,2,3,4,5,6)
                    expanded = _expand_member_range(member_ids)
                    for mid_str in expanded:
                        if mid_str.isdigit():
                            nid = _find_member_by_index(ctx.doc, int(mid_str))
                            if nid:
                                ctx.doc.members[nid].section_id = sec.id
                        elif mid_str.upper() == "ALL":
                            for member in ctx.doc.members.values():
                                member.section_id = sec.id
        i += 1
    return i


def _parse_materials(lines, i, ctx) -> int:
    """Parse DEFINE MATERIAL START ... END DEFINE MATERIAL."""
    i += 1
    current_mat = None
    while i < len(lines):
        line = lines[i].strip()
        upper = line.upper()
        if upper == "END DEFINE MATERIAL":
            if current_mat:
                mat = ctx.doc.add_material(
                    current_mat["name"], current_mat["E"],
                    current_mat["poisson"], current_mat["density"]
                )
                ctx._default_mat_id = mat.id
            return i

        if upper.startswith("ISOTROPIC"):
            name = line.split("ISOTROPIC", 1)[-1].strip() or "Steel"
            current_mat = {"name": name, "E": 200e9, "poisson": 0.3, "density": 7850}
        elif current_mat:
            parts = line.split()
            if upper.startswith("E ") or upper == "E":
                current_mat["E"] = float(parts[1]) * 1e6 if float(parts[1]) < 1e6 else float(parts[1])
            elif upper.startswith("POISSON"):
                current_mat["poisson"] = float(parts[1])
            elif upper.startswith("DENSITY"):
                v = float(parts[1])
                current_mat["density"] = v * 100 if v < 1000 else v  # kN/m³ → kg/m³ (~/9.81×1000)

        i += 1

    if current_mat:
        mat = ctx.doc.add_material(
            current_mat["name"], current_mat["E"],
            current_mat["poisson"], current_mat["density"]
        )
        ctx._default_mat_id = mat.id
    return i


def _parse_constants(lines, i, ctx) -> int:
    """Parse CONSTANTS section — material assignments to members."""
    i += 1
    while i < len(lines):
        line = lines[i].strip()
        if not line or _is_section_header(line):
            return i - 1

        upper = line.upper()
        if upper.startswith("MATERIAL"):
            parts = line.split()
            mat_name = parts[1] if len(parts) > 1 else None
            apply_to = parts[2].upper() if len(parts) > 2 else "ALL"
            if mat_name:
                mat_id = None
                for mat in ctx.doc.materials.values():
                    if mat.name.upper() == mat_name.upper():
                        mat_id = mat.id
                        break

                if mat_id and apply_to == "ALL":
                    for member in ctx.doc.members.values():
                        member.material_id = mat_id
                elif mat_id:
                    for part in parts[2:]:
                        mid = part.strip()
                        if mid.isdigit():
                            # Find member by index
                            nid = _find_member_by_index(ctx.doc, int(mid))
                            if nid:
                                ctx.doc.members[nid].material_id = mat_id
        i += 1
    return i


def _find_member_by_index(doc, idx: int) -> str | None:
    for i, (mid, _) in enumerate(doc.members.items(), 1):
        if i == idx:
            return mid
    return None


def _parse_envelope(lines, i, ctx) -> int:
    """Parse DEFINE ENVELOPE ... END DEFINE ENVELOPE."""
    from src.model.entities.envelope import Envelope
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        upper = line.upper()
        if upper.startswith("END DEFINE ENVELOPE"):
            return i + 1
        parts = line.split()
        try:
            env_idx = [j for j, p in enumerate(parts) if p.upper() == 'ENVELOPE'][0]
        except IndexError:
            i += 1
            continue
        combo_nums = parts[:env_idx]
        env_id = parts[env_idx + 1] if env_idx + 1 < len(parts) else "1"
        env_type = "strength"
        if "TYPE" in upper:
            type_idx = [j for j, p in enumerate(parts) if p.upper() == 'TYPE'][0]
            if type_idx + 1 < len(parts):
                env_type = parts[type_idx + 1].lower()
        expanded = _expand_member_range(combo_nums)
        combo_ids = [c for c in expanded if c in ctx.doc.load_combinations]
        if combo_ids:
            ctx.doc.envelopes[env_id] = Envelope(
                id=env_id, name=f"ENVELOPE {env_id}",
                combo_ids=combo_ids, envelope_type=env_type
            )
        i += 1
    return i


def _expand_member_range(ids: list[str]) -> list[str]:
    """Expand STAAD range syntax: ['1', 'TO', '6'] → ['1','2','3','4','5','6'].

    Also handles: ['1', 'TO', '6', '8', 'TO', '10'] → ['1'..'6', '8','9','10']
    """
    result = []
    i = 0
    while i < len(ids):
        tok = ids[i].upper()
        # Check for range: N TO M
        if tok == "TO" and i > 0 and i + 1 < len(ids):
            try:
                start = int(ids[i - 1])
                end = int(ids[i + 1])
                # Remove the start we added previously
                if result and result[-1] == ids[i - 1]:
                    result.pop()
                for v in range(start, end + 1):
                    result.append(str(v))
                i += 2  # skip TO and end (will be incremented again below)
            except ValueError:
                result.append(ids[i])
        elif tok != "TO":
            result.append(ids[i])
        i += 1
    return result


def _parse_supports(lines, i, ctx) -> int:
    """Parse SUPPORTS section."""
    i += 1
    while i < len(lines):
        line = lines[i].strip()
        if not line or _is_section_header(line):
            return i - 1

        upper = line.upper()
        parts = line.split()
        if len(parts) >= 2:
            node_label = f"N{parts[0]}"
            stype_str = parts[1].upper()
            nid = _find_node_by_label(ctx.doc, node_label)
            if nid:
                st = _map_support(stype_str)
                ctx.doc.nodes[nid].support_type = st
        i += 1
    return i


def _map_support(stype: str) -> SupportType:
    mapping = {
        "FIXED": SupportType.FIXED,
        "PINNED": SupportType.PINNED,
        "ROLLER": SupportType.ROLLER_X,
    }
    return mapping.get(stype, SupportType.PINNED)


def _parse_member_releases(lines, i, ctx) -> int:
    """Parse MEMBER RELEASE lines.
    Format: <member_range> START|END <DOF> [<DOF> ...]
    Example: 30 TO 33 35 TO 38 START MX MY MZ
    """
    dof_map = {'FX': 0, 'FY': 1, 'FZ': 2, 'MX': 3, 'MY': 4, 'MZ': 5}
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        upper = line.upper()
        if _is_section_header(line):
            return i - 1
        # Parse member numbers and release spec
        parts = line.split()
        if 'START' in upper:
            node_pos = 0
            kw_idx = [j for j, p in enumerate(parts) if p.upper() == 'START'][0]
        elif 'END' in upper:
            node_pos = 6
            kw_idx = [j for j, p in enumerate(parts) if p.upper() == 'END'][0]
        else:
            i += 1
            continue
        member_nums = parts[:kw_idx]
        dofs = parts[kw_idx + 1:]
        expanded = _expand_member_range(member_nums)
        for m_num in expanded:
            mid = _find_member_by_index(ctx.doc, int(m_num))
            if mid and mid in ctx.doc.members:
                mem = ctx.doc.members[mid]
                for dof_name in dofs:
                    dof_idx = dof_map.get(dof_name.upper())
                    if dof_idx is not None:
                        mem.releases[node_pos + dof_idx] = True
        i += 1
    return i


def _parse_load_case(lines, i, ctx) -> int:
    """Parse LOAD n ... section."""
    line = lines[i].strip()
    parts = line.split()

    lc_name = " ".join(parts[1:]) if len(parts) > 1 else "Load"
    lc = ctx.doc.add_load_case(lc_name)

    # Determine load type
    for j, p in enumerate(parts):
        if p.upper() == "LOADTYPE" and j + 1 < len(parts):
            lc.load_type = parts[j + 1].lower()
            lc.name = lc_name

    i += 1
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        upper = line.upper()
        if _is_section_header(line) and not upper.startswith("JOINT") and not upper.startswith("MEMBER"):
            return i - 1

        if upper.startswith("JOINT LOAD") or upper == "JOINT LOAD":
            i = _parse_joint_loads(lines, i, ctx, lc)
        elif upper.startswith("MEMBER LOAD") or upper == "MEMBER LOAD":
            i = _parse_member_loads(lines, i, ctx, lc)
        elif upper.startswith("SELFWEIGHT"):
            lc.include_self_weight = True
            i += 1
        else:
            i += 1

    return i


def _parse_joint_loads(lines, i, ctx, lc):
    """Parse JOINT LOAD sub-section within a load case."""
    i += 1
    count = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if _is_section_header(line) and not line.upper().startswith("JOINT"):
            return i - 1

        parts = line.split()
        # Format: <joint_id> <direction> <value> [<direction> <value>...]
        if len(parts) >= 3:
            try:
                nid = _find_node_by_label(ctx.doc, f"N{parts[0]}")
                if nid:
                    fx = fy = fz = mx = my = mz = 0.0
                    j = 1
                    while j + 1 < len(parts):
                        d = parts[j].upper()
                        v = float(parts[j + 1])
                        if d == "FX": fx = v
                        elif d == "FY": fy = v
                        elif d == "FZ": fz = v
                        elif d == "MX": mx = v
                        elif d == "MY": my = v
                        elif d == "MZ": mz = v
                        j += 2
                    count += 1
                    lc.nodal_loads[f"nl_{count}"] = NodalLoad(
                        node_id=nid, fx=fx, fy=fy, fz=fz, mx=mx, my=my, mz=mz
                    )
            except (ValueError, IndexError):
                pass
        i += 1
    return i


def _parse_member_loads(lines, i, ctx, lc):
    """Parse MEMBER LOAD sub-section within a load case."""
    i += 1
    count = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if _is_section_header(line) and not line.upper().startswith("MEMBER"):
            return i - 1
        i += 1
    return i


def _parse_load_combination(lines, i, ctx) -> int:
    """Parse LOAD COMBINATION n ... lines."""
    from src.model.entities.load_case import LoadCombination
    line = lines[i].strip()
    parts = line.split()
    combo_id = parts[2] if len(parts) > 2 else str(len(ctx.doc.load_cases) + 100)
    combo_name = " ".join(parts[3:]) if len(parts) > 3 else f"COMBO{combo_id}"
    factors = {}
    i += 1
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            i += 1
            continue
        if line.upper().startswith("LOAD COMB"):
            break
        if _is_section_header(line):
            break
        nums = line.split()
        for j in range(0, len(nums) - 1, 2):
            try:
                lc_num = int(nums[j])
                factor = float(nums[j + 1])
                lc_idx = 0
                for lc_id, _ in ctx.doc.load_cases.items():
                    lc_idx += 1
                    if lc_idx == lc_num:
                        factors[lc_id] = factor
                        break
            except (ValueError, IndexError):
                pass
        i += 1
    if factors:
        ctx.doc.load_combinations[combo_id] = LoadCombination(
            id=combo_id, name=combo_name, factors=factors
        )
    return i - 1


# ── Write Document → .std ──────────────────────────

def write_std(doc: Document, filepath: str):
    """Export a DogCalC Document to STAAD .std text format."""
    Path(filepath).write_text(build_std_text(doc))


def build_std_text(doc: Document) -> str:
    """Generate STAAD .std text from a Document. Returns the full text."""
    lines = []
    w = lines.append

    w("STAAD SPACE")
    w("START JOB INFORMATION")
    w("ENGINEER DATE " + _today())
    w("END JOB INFORMATION")
    w("INPUT WIDTH 79")
    w("UNIT METER KN")
    w("")

    # Joints
    w("JOINT COORDINATES")
    for node in doc.nodes.values():
        # Use label number if numeric, else index
        jid = _node_index(doc, node)
        w(f"{jid} {node.x:.3f} {node.y:.3f} {node.z:.3f}")
    w("")

    # Members
    w("MEMBER INCIDENCES")
    for member in doc.members.values():
        mid = _member_index(doc, member)
        si = _node_index(doc, doc.nodes[member.start_node_id])
        ei = _node_index(doc, doc.nodes[member.end_node_id])
        w(f"{mid} {si} {ei}")
    w("")

    # Member properties
    if doc.sections:
        # Group members by section
        sec_members: dict[str, list] = {}
        for m in doc.members.values():
            sid = m.section_id or _default_section_id(doc)
            sec_members.setdefault(sid, []).append(m)

        w("MEMBER PROPERTY")
        for sid, members in sec_members.items():
            sec = doc.sections.get(sid)
            if sec:
                member_list = " ".join(str(_member_index(doc, m)) for m in members)
                w(f"{member_list} TABLE ST {sec.name}")
    w("")

    # Materials
    if doc.materials:
        w("DEFINE MATERIAL START")
        for mat in doc.materials.values():
            w(f"ISOTROPIC {mat.name}")
            w(f"E {mat.elastic_modulus / 1e6:.3f}")
            w(f"POISSON {mat.poisson_ratio}")
            w(f"DENSITY {mat.density / 1000:.2f}")
        w("END DEFINE MATERIAL")
        w("")

    # Material assignments
    if doc.materials:
        w("CONSTANTS")
        mat_name = list(doc.materials.values())[0].name if doc.materials else "STEEL"
        w(f"MATERIAL {mat_name} ALL")
        w("")

    # Supports
    supported = [n for n in doc.nodes.values() if n.is_supported]
    if supported:
        w("SUPPORTS")
        for node in supported:
            jid = _node_index(doc, node)
            stype = _support_to_staad(node.support_type)
            w(f"{jid} {stype}")
        w("")

    # Loads
    for lc in doc.load_cases.values():
        w(f"LOAD {_lc_index(doc, lc)} LOADTYPE {lc.load_type.capitalize()} {lc.name}")
        if lc.nodal_loads:
            w("JOINT LOAD")
            for nl in lc.nodal_loads.values():
                node = doc.nodes.get(nl.node_id)
                if node:
                    jid = _node_index(doc, node)
                    parts = []
                    if nl.fx: parts.append(f"FX {nl.fx:.2f}")
                    if nl.fy: parts.append(f"FY {nl.fy:.2f}")
                    if nl.fz: parts.append(f"FZ {nl.fz:.2f}")
                    if nl.mx: parts.append(f"MX {nl.mx:.2f}")
                    if nl.my: parts.append(f"MY {nl.my:.2f}")
                    if nl.mz: parts.append(f"MZ {nl.mz:.2f}")
                    if parts:
                        w(f"{jid} {' '.join(parts)}")
        if lc.include_self_weight:
            w("SELFWEIGHT Y -1")
        w("")

    # Load combinations
    for combo in doc.load_combinations.values():
        w(f"LOAD COMBINATION {combo.id} {combo.name}")
        for lc_id, factor in combo.factors.items():
            # Find load case index
            lc_idx = _lc_index_by_id(doc, lc_id)
            w(f"{lc_idx} {factor}")
        w("")

    w("PERFORM ANALYSIS")
    w("FINISH")

    return "\n".join(lines)


# ── Helpers ────────────────────────────────────────

def _node_index(doc, node) -> int:
    """Get 1-based index from node label (N1→1, N3→3). Preserves original numbering."""
    import re
    m = re.search(r'\d+', node.label)
    return int(m.group()) if m else 0


def _member_index(doc, member) -> int:
    """Get 1-based index from member label (M1→1, M3→3). Preserves original numbering."""
    import re
    m = re.search(r'\d+', member.label)
    return int(m.group()) if m else 0


def _lc_index(doc, lc) -> int:
    for i, (lid, _) in enumerate(doc.load_cases.items(), 1):
        if lid == lc.id:
            return i
    return 1


def _lc_index_by_id(doc, lc_id: str) -> int:
    for i, (lid, _) in enumerate(doc.load_cases.items(), 1):
        if lid == lc_id:
            return i
    return 1


def _default_section_id(doc) -> str:
    if doc.sections:
        return list(doc.sections.keys())[0]
    return ""


def _support_to_staad(st: SupportType) -> str:
    mapping = {
        SupportType.FIXED: "FIXED",
        SupportType.PINNED: "PINNED",
        SupportType.ROLLER_X: "ROLLER",
        SupportType.ROLLER_Y: "ROLLER",
        SupportType.ROLLER_Z: "ROLLER",
    }
    return mapping.get(st, "FREE")


def _today() -> str:
    from datetime import date
    return date.today().strftime("%d-%b-%y")
