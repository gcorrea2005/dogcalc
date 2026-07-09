"""Document — central data model holding all structural entities.

Pattern: identical to cad2d-lite's Document class.
Holds nodes, members, materials, sections, and load cases.
Provides add/delete/undo/redo operations.
"""

import uuid
from collections import OrderedDict
from src.model.entities.node import Node, SupportType
from src.model.entities.member import Member, MemberType
from src.model.entities.material import Material
from src.model.entities.section import Section
from src.model.entities.load_case import LoadCase


class Document:
    """The single source of truth for the structural model.

    All entities are stored in OrderedDicts keyed by UUID.
    The viewport renders from this document.
    The engine builds PyNite models from this document.
    """

    def __init__(self):
        self.nodes: OrderedDict[str, Node] = OrderedDict()
        self.members: OrderedDict[str, Member] = OrderedDict()
        self.materials: OrderedDict[str, Material] = OrderedDict()
        self.sections: OrderedDict[str, Section] = OrderedDict()
        self.load_cases: OrderedDict[str, LoadCase] = OrderedDict()
        self.load_combinations: OrderedDict[str, "LoadCombination"] = OrderedDict()
        self.envelopes: OrderedDict[str, "Envelope"] = OrderedDict()
        self.code_params: dict = {}  # {fy: kPa, fu: kPa, code: str}
        self._undo_stack: list = []
        self._redo_stack: list = []
        self._dirty: bool = False

        # UI state (not persisted)
        self.selected_node_id: str | None = None
        self.selected_member_id: str | None = None
        self.current_load_case: str | None = None
        self.units: str = "metric"   # metric | imperial

    # ── Properties ───────────────────────────────────

    @property
    def is_dirty(self) -> bool:
        return self._dirty

    @property
    def node_count(self) -> int:
        return len(self.nodes)

    @property
    def member_count(self) -> int:
        return len(self.members)

    def node_list(self) -> list[Node]:
        """Return nodes in insertion order."""
        return list(self.nodes.values())

    def member_list(self) -> list[Member]:
        """Return members in insertion order."""
        return list(self.members.values())

    # ── Node operations ──────────────────────────────

    def add_node(self, x: float, y: float, z: float,
                 label: str = "", support_type: SupportType = SupportType.FREE) -> Node:
        """Create and add a new node to the document."""
        if not label:
            label = f"N{self.node_count + 1}"
        node = Node(
            id=str(uuid.uuid4()), label=label,
            x=x, y=y, z=z, support_type=support_type
        )
        self.nodes[node.id] = node
        self._dirty = True
        return node

    # ── Member operations ────────────────────────────

    def add_member(self, start_node_id: str, end_node_id: str,
                   label: str = "", material_id: str = "",
                   section_id: str = "",
                   member_type: MemberType = MemberType.BEAM) -> Member:
        """Create and add a new member connecting two nodes."""
        if start_node_id not in self.nodes:
            raise ValueError(f"Start node {start_node_id} not found")
        if end_node_id not in self.nodes:
            raise ValueError(f"End node {end_node_id} not found")
        if start_node_id == end_node_id:
            raise ValueError("Member cannot connect a node to itself")
        if not label:
            label = f"M{self.member_count + 1}"
        member = Member(
            id=str(uuid.uuid4()), label=label,
            start_node_id=start_node_id, end_node_id=end_node_id,
            material_id=material_id, section_id=section_id,
            member_type=member_type
        )
        self.members[member.id] = member
        self._dirty = True
        return member

    # ── Delete operations ────────────────────────────

    def delete_entity(self, entity_id: str):
        """Delete a node or member by ID.

        Deleting a node also deletes all members connected to it.
        """
        if entity_id in self.nodes:
            # Cascade: remove members connected to this node
            to_remove = [
                m.id for m in self.members.values()
                if m.start_node_id == entity_id or m.end_node_id == entity_id
            ]
            for mid in to_remove:
                del self.members[mid]
            del self.nodes[entity_id]
        elif entity_id in self.members:
            del self.members[entity_id]
        self._dirty = True

    # ── Material operations ──────────────────────────

    def add_material(self, name: str = "", elastic_modulus: float = 200e9,
                     poisson_ratio: float = 0.3, density: float = 7850.0,
                     yield_strength: float = 275e6) -> Material:
        """Add a new material definition."""
        mat = Material(
            id=str(uuid.uuid4()), name=name,
            elastic_modulus=elastic_modulus, poisson_ratio=poisson_ratio,
            density=density, yield_strength=yield_strength
        )
        self.materials[mat.id] = mat
        self._dirty = True
        return mat

    # ── Section operations ───────────────────────────

    def add_section(self, name: str = "", area: float = 0.01,
                    ix: float = 1e-4, iy: float = 1e-4,
                    iz: float = 1e-6, j: float = 1e-6,
                    depth: float = 0.3, width: float = 0.15) -> Section:
        """Add a new section definition."""
        sec = Section(
            id=str(uuid.uuid4()), name=name,
            area=area, ix=ix, iy=iy, iz=iz, j=j,
            depth=depth, width=width
        )
        self.sections[sec.id] = sec
        self._dirty = True
        return sec

    # ── Load case operations ─────────────────────────

    def add_load_case(self, name: str = "", load_type: str = "dead") -> LoadCase:
        """Add a new load case."""
        lc = LoadCase(
            id=str(uuid.uuid4()), name=name, load_type=load_type
        )
        self.load_cases[lc.id] = lc
        self._dirty = True
        return lc

    # ── Undo/Redo (placeholder, full impl in Task 13) ─

    def undo(self):
        """Undo last operation."""
        if self._undo_stack:
            cmd = self._undo_stack.pop()
            cmd.undo(self)
            self._redo_stack.append(cmd)
            self._dirty = True

    def redo(self):
        """Redo last undone operation."""
        if self._redo_stack:
            cmd = self._redo_stack.pop()
            cmd.execute(self)
            self._undo_stack.append(cmd)
            self._dirty = True

    # ── Info ─────────────────────────────────────────

    def __repr__(self):
        return (f"Document({self.node_count} nodes, {self.member_count} members, "
                f"{len(self.materials)} materials, {len(self.sections)} sections, "
                f"{len(self.load_cases)} load cases)")
