"""Material entity — mechanical properties for structural elements."""

from dataclasses import dataclass


@dataclass
class Material:
    """Material definition (isotropic linear elastic).

    Units convention (metric):
      - elastic_modulus: MPa (or Pa depending on user preference)
      - density: kg/m³
      - yield_strength: MPa
    """

    id: str
    name: str = ""
    elastic_modulus: float = 200e9     # E (Pa) — default: structural steel
    poisson_ratio: float = 0.3          # ν
    density: float = 7850.0             # ρ (kg/m³) — steel
    yield_strength: float = 275e6       # Fy (Pa) — S275

    @property
    def shear_modulus(self) -> float:
        """G = E / (2 * (1 + ν))"""
        return self.elastic_modulus / (2 * (1 + self.poisson_ratio))

    def __repr__(self):
        return f"Material({self.name}: E={self.elastic_modulus:.1e} Pa)"
