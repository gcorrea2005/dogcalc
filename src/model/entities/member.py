"""Member entity — structural element connecting two nodes."""

from dataclasses import dataclass
from enum import Enum


class MemberType(Enum):
    BEAM = "beam"        # resists bending + shear + axial
    COLUMN = "column"    # same as beam (naming convention)
    BRACE = "brace"      # axial only (future)
    TRUSS = "truss"      # axial only (future)


@dataclass
class Member:
    """A structural member (beam/column/brace) connecting two nodes.

    In the FEM model, members are 3D frame elements with 6 DOF per node.
    """

    id: str                     # UUID
    start_node_id: str
    end_node_id: str
    material_id: str = ""       # references Material.id
    section_id: str = ""        # references Section.id
    member_type: MemberType = MemberType.BEAM
    label: str = ""

    def __repr__(self):
        return f"Member({self.label}: {self.start_node_id[:8]}→{self.end_node_id[:8]} [{self.member_type.value}])"
