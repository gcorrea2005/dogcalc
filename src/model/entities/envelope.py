"""Envelope entity — groups load combinations for max/min results."""

from dataclasses import dataclass, field


@dataclass
class Envelope:
    """Envelope of load combinations.

    Computes max/min member forces and node displacements across a set of combos.
    Used for code checking (e.g., AISC, NSR-10).
    """

    id: str
    name: str = ""
    combo_ids: list[str] = field(default_factory=list)
    envelope_type: str = "strength"  # strength | service

    # Computed results
    max_displacement: float = 0.0
    max_axial: dict[str, float] = field(default_factory=dict)   # member_id → max axial
    max_moment_z: dict[str, float] = field(default_factory=dict) # member_id → max Mz
    max_shear_y: dict[str, float] = field(default_factory=dict)  # member_id → max Vy

    def __repr__(self):
        return f"Envelope({self.name}: {len(self.combo_ids)} combos)"
