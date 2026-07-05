"""Node entity — 3D point in space with optional support condition."""

from dataclasses import dataclass
from enum import Enum


class SupportType(Enum):
    FREE = "free"
    PINNED = "pinned"        # DX, DY, DZ restrained
    FIXED = "fixed"          # DX, DY, DZ, RX, RY, RZ restrained
    ROLLER_X = "roller_x"    # free in X direction
    ROLLER_Y = "roller_y"    # free in Y direction
    ROLLER_Z = "roller_z"    # free in Z direction


@dataclass
class Node:
    """A structural node (joint) at a point in 3D space.

    Nodes are the fundamental building blocks. Members connect nodes.
    Supports are applied at nodes.
    """

    id: str                    # UUID
    label: str = ""
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0
    support_type: SupportType = SupportType.FREE

    @property
    def is_supported(self) -> bool:
        return self.support_type != SupportType.FREE

    @property
    def position(self) -> tuple[float, float, float]:
        return (self.x, self.y, self.z)

    def __repr__(self):
        sup = f" [{self.support_type.value}]" if self.is_supported else ""
        return f"Node({self.label} @ {self.x:.2f}, {self.y:.2f}, {self.z:.2f}{sup})"
