"""Section entity — cross-sectional properties for structural members."""

from dataclasses import dataclass


@dataclass
class Section:
    """Cross-section properties for beam/column members.

    All values in consistent units (m, m², m⁴ for metric).
    """

    id: str
    name: str = ""
    area: float = 0.01                # A (m²) — cross-sectional area
    ix: float = 1e-4                  # Iy (m⁴) — moment of inertia about local Y
    iy: float = 1e-4                  # Iz (m⁴) — moment of inertia about local Z
    iz: float = 1e-6                  # J  (m⁴) — torsional constant
    j: float = 1e-6                   # J  (m⁴) — torsional constant (alias)
    depth: float = 0.3                # section depth (m)
    width: float = 0.15               # section width (m)

    @property
    def iy_strong(self) -> float:
        """Strong-axis moment of inertia (convention: max of ix, iy)."""
        return max(self.ix, self.iy)

    @property
    def iz_weak(self) -> float:
        """Weak-axis moment of inertia."""
        return min(self.ix, self.iy)

    def __repr__(self):
        return f"Section({self.name}: A={self.area:.4f} m², Iy={self.ix:.2e} m⁴)"
