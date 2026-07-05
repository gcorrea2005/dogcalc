"""LoadCase entity — collections of loads applied to the structure."""

from dataclasses import dataclass, field
from collections import OrderedDict


@dataclass
class NodalLoad:
    """Concentrated force/moment applied at a node.

    Forces in global axes: Fx, Fy, Fz (N or kN)
    Moments in global axes: Mx, My, Mz (N·m or kN·m)
    """

    node_id: str = ""
    fx: float = 0.0
    fy: float = 0.0
    fz: float = 0.0
    mx: float = 0.0
    my: float = 0.0
    mz: float = 0.0

    @property
    def has_force(self) -> bool:
        return any(abs(v) > 1e-10 for v in (self.fx, self.fy, self.fz))

    @property
    def has_moment(self) -> bool:
        return any(abs(v) > 1e-10 for v in (self.mx, self.my, self.mz))

    def __repr__(self):
        parts = []
        if self.has_force:
            parts.append(f"F=({self.fx:.1f},{self.fy:.1f},{self.fz:.1f})")
        if self.has_moment:
            parts.append(f"M=({self.mx:.1f},{self.my:.1f},{self.mz:.1f})")
        return f"NodalLoad(@{self.node_id[:8]} {' '.join(parts)})"


@dataclass
class MemberLoad:
    """Linearly varying distributed load on a member.

    Direction: local_y, local_z, or axial
    w1, w2: load intensity at start (x=0) and end (x=1)
    """

    member_id: str = ""
    direction: str = "local_y"   # local_y | local_z | axial
    w1: float = 0.0              # start magnitude
    w2: float = 0.0              # end magnitude (trapezoidal)

    def __repr__(self):
        return f"MemberLoad(@{self.member_id[:8]} {self.direction} w1={self.w1:.1f} w2={self.w2:.1f})"


@dataclass
class LoadCase:
    """A named load case containing nodal and member loads."""

    id: str
    name: str = ""
    load_type: str = "dead"      # dead | live | wind | seismic | snow | other
    include_self_weight: bool = False

    def __post_init__(self):
        self.nodal_loads: OrderedDict[str, NodalLoad] = OrderedDict()
        self.member_loads: OrderedDict[str, MemberLoad] = OrderedDict()

    def add_nodal_load(self, nl_id: str, load: NodalLoad):
        self.nodal_loads[nl_id] = load

    def add_member_load(self, ml_id: str, load: MemberLoad):
        self.member_loads[ml_id] = load

    def __repr__(self):
        return (f"LoadCase({self.name}, {len(self.nodal_loads)} nodal, "
                f"{len(self.member_loads)} member loads)")


@dataclass
class LoadCombination:
    """Combination of load cases with factors (e.g., 1.2*Dead + 1.6*Live)."""

    id: str
    name: str = ""
    factors: dict[str, float] = field(default_factory=dict)   # load_case_id → factor

    def __repr__(self):
        parts = [f"{lc_id[:8]}*{f:.2f}" for lc_id, f in self.factors.items()]
        return f"LoadComb({self.name}: {' + '.join(parts)})"
