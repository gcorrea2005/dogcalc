"""Orbit camera for 3D structural viewport.

Spherical coordinate system:
  - theta: horizontal angle (rotation around Y axis)
  - phi: vertical angle (0 = horizon, +pi/2 = top-down)
  - radius: distance from target
"""

import numpy as np
from math import cos, sin, pi


class OrbitCamera:
    """Camera with orbit/pan/zoom controls — identical UX to cad2d-lite.

    Convention: Y axis is UP (structural engineering convention).
    Grid is on the XZ plane (floor).
    """

    def __init__(self):
        self.theta = -pi / 6       # look from front-right
        self.phi = 0.3             # slight elevation
        self.radius = 20.0        # distance from target
        self.target = np.array([0.0, 0.0, 0.0], dtype=np.float32)
        self.up = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    @property
    def position(self) -> np.ndarray:
        """Camera position in cartesian coordinates."""
        x = self.target[0] + self.radius * cos(self.phi) * cos(self.theta)
        y = self.target[1] + self.radius * sin(self.phi)
        z = self.target[2] + self.radius * cos(self.phi) * sin(self.theta)
        return np.array([x, y, z], dtype=np.float32)

    def view_matrix(self) -> np.ndarray:
        """Returns 4x4 view (lookAt) matrix as float32 numpy array."""
        eye = self.position
        return _look_at(eye, self.target, self.up)

    def orbit(self, dx: float, dy: float):
        """Rotate around target. dx, dy are pixel deltas."""
        self.theta -= dx * 0.005
        self.phi += dy * 0.005
        self.phi = max(-pi / 2 + 0.01, min(pi / 2 - 0.01, self.phi))

    def pan(self, dx: float, dy: float):
        """Pan: move target in camera-plane. dx, dy are pixel deltas."""
        forward = self.position - self.target
        forward_n = forward / np.linalg.norm(forward)
        right = np.cross(forward_n, self.up)
        right_n = right / np.linalg.norm(right)
        cam_up = np.cross(right_n, forward_n)
        s = self.radius * 0.001
        self.target += right_n * dx * s + cam_up * (-dy * s)

    def zoom(self, delta: float):
        """Zoom in/out. delta is scroll delta (positive = zoom in)."""
        self.radius *= (1.0 - delta * 0.001)
        self.radius = max(0.5, min(200.0, self.radius))


def _look_at(eye: np.ndarray, target: np.ndarray, up: np.ndarray) -> np.ndarray:
    """Compute a 4x4 lookAt matrix (like gluLookAt) without pyrr dependency."""
    eye = np.asarray(eye, dtype=np.float32)
    target = np.asarray(target, dtype=np.float32)
    up = np.asarray(up, dtype=np.float32)

    forward = eye - target
    forward = forward / np.linalg.norm(forward)
    right = np.cross(up, forward)
    right = right / np.linalg.norm(right)
    cam_up = np.cross(forward, right)

    # View matrix: [R | -R*eye; 0 0 0 1]
    m = np.eye(4, dtype=np.float32)
    m[0, :3] = right
    m[1, :3] = cam_up
    m[2, :3] = forward
    m[:3, 3] = [-np.dot(right, eye), -np.dot(cam_up, eye), -np.dot(forward, eye)]
    return m
