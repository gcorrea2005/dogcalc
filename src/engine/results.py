"""Analysis results dataclasses."""

from dataclasses import dataclass, field


@dataclass
class NodeResult:
    """Analysis result for a single node."""

    node_id: str = ""
    dx: float = 0.0     # displacement X (m)
    dy: float = 0.0     # displacement Y (m)
    dz: float = 0.0     # displacement Z (m)
    rx: float = 0.0     # rotation X (rad)
    ry: float = 0.0     # rotation Y (rad)
    rz: float = 0.0     # rotation Z (rad)
    rxn_fx: float = 0.0  # reaction force X (N)
    rxn_fy: float = 0.0  # reaction force Y (N)
    rxn_fz: float = 0.0  # reaction force Z (N)
    rxn_mx: float = 0.0  # reaction moment X (N·m)
    rxn_my: float = 0.0  # reaction moment Y (N·m)
    rxn_mz: float = 0.0  # reaction moment Z (N·m)


@dataclass
class MemberResult:
    """Analysis result for a single member — internal forces along length."""

    member_id: str = ""
    segments: list[dict] = field(default_factory=list)
    # Each segment: {'x': float (0-1), 'axial': float, 'shear_y': float,
    #                 'shear_z': float, 'torsion': float,
    #                 'moment_y': float, 'moment_z': float}


@dataclass
class AnalysisResult:
    """Complete analysis results for a load combination."""

    success: bool = False
    load_case_name: str = ""
    node_results: dict[str, NodeResult] = field(default_factory=dict)
    member_results: dict[str, MemberResult] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def max_displacement(self) -> float:
        """Maximum resultant displacement among all nodes."""
        if not self.node_results:
            return 0.0
        return max(
            (r.dx**2 + r.dy**2 + r.dz**2)**0.5
            for r in self.node_results.values()
        )
