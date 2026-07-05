"""OpenGL renderer for structural entities.

Uses fixed-function OpenGL (GLU primitives) — simple, reliable, no shaders needed.
"""

import numpy as np
from math import sqrt
from OpenGL.GL import *
from OpenGL.GLU import gluPerspective, gluNewQuadric, gluSphere, gluCylinder, gluDeleteQuadric


class Renderer:
    """Renders the 3D structural scene."""

    def __init__(self):
        self.bg_color = (0.15, 0.15, 0.18, 1.0)  # lighter gray
        self.grid_color = (0.25, 0.25, 0.30)       # brighter grid
        self.grid_spacing = 1.0
        self.grid_size = 20
        self.draw_grid_enabled = True
        self._node_scale = 1.0

    def initialize(self):
        """Configure OpenGL state."""
        glClearColor(*self.bg_color)
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LINE_SMOOTH)
        glHint(GL_LINE_SMOOTH_HINT, GL_NICEST)

    def resize(self, w: int, h: int):
        """Adjust viewport and projection matrix."""
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45.0, w / max(h, 1), 0.1, 500.0)
        glMatrixMode(GL_MODELVIEW)

    def begin_frame(self, camera):
        """Clear buffers and load view matrix from camera."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        view = camera.view_matrix()
        glMultMatrixf(view.flatten())

    # ── Grid ─────────────────────────────────────────

    def draw_grid(self):
        """Draw reference grid on XZ plane (Y=0, structural floor)."""
        if not self.draw_grid_enabled:
            return
        glColor3f(*self.grid_color)
        glLineWidth(0.5)
        n = self.grid_size
        s = self.grid_spacing
        glBegin(GL_LINES)
        for i in range(-n, n + 1):
            glVertex3f(i * s, 0, -n * s)
            glVertex3f(i * s, 0,  n * s)
            glVertex3f(-n * s, 0, i * s)
            glVertex3f( n * s, 0, i * s)
        glEnd()

    # ── Axes ─────────────────────────────────────────

    def draw_axes(self):
        """Draw XYZ axes at origin. X=Red, Y=Green, Z=Blue."""
        length = 5.0
        glLineWidth(3.0)

        glColor3f(1.0, 0.2, 0.2)
        glBegin(GL_LINES)
        glVertex3f(0, 0, 0); glVertex3f(length, 0, 0)
        glEnd()

        glColor3f(0.2, 1.0, 0.2)
        glBegin(GL_LINES)
        glVertex3f(0, 0, 0); glVertex3f(0, length, 0)
        glEnd()

        glColor3f(0.2, 0.4, 1.0)
        glBegin(GL_LINES)
        glVertex3f(0, 0, 0); glVertex3f(0, 0, length)
        glEnd()

    # ── Structural primitives ────────────────────────

    def draw_node(self, x, y, z, color=(1.0, 1.0, 1.0), radius=None):
        """Draw a sphere at the node position."""
        if radius is None:
            radius = 0.08 * self._node_scale
        glPushMatrix()
        glTranslatef(x, y, z)
        glColor3f(*color)
        quad = gluNewQuadric()
        gluSphere(quad, radius, 16, 12)
        gluDeleteQuadric(quad)
        glPopMatrix()

    def draw_member(self, x1, y1, z1, x2, y2, z2, color=(0.3, 0.7, 1.0), radius=None):
        """Draw a cylinder between two 3D points."""
        if radius is None:
            radius = 0.03 * self._node_scale
        dx, dy, dz = x2 - x1, y2 - y1, z2 - z1
        length = sqrt(dx * dx + dy * dy + dz * dz)
        if length < 0.001:
            return

        glPushMatrix()
        glTranslatef(x1, y1, z1)

        # Align default cylinder axis (Y-up) with member direction
        dir_vec = np.array([dx, dy, dz]) / length
        y_axis = np.array([0.0, 1.0, 0.0])
        dot = np.dot(y_axis, dir_vec)
        if dot > 0.9999:
            pass  # already aligned
        elif dot < -0.9999:
            glRotatef(180, 1, 0, 0)
        else:
            angle = np.arccos(dot) * 180.0 / np.pi
            axis = np.cross(y_axis, dir_vec)
            axis = axis / np.linalg.norm(axis)
            glRotatef(angle, axis[0], axis[1], axis[2])

        glColor3f(*color)
        quad = gluNewQuadric()
        gluCylinder(quad, radius, radius, length, 8, 1)
        gluDeleteQuadric(quad)
        glPopMatrix()

    # ── Model rendering ──────────────────────────────

    def draw_model(self, document):
        """Render all nodes, members, supports, and loads from the Document."""
        from src.model.entities.node import SupportType

        # Nodes
        for node in document.nodes.values():
            is_sel = (node.id == document.selected_node_id)
            if node.support_type == SupportType.FREE:
                color = (0.2, 1.0, 0.2) if is_sel else (1.0, 1.0, 1.0)
            else:
                color = (1.0, 0.8, 0.0) if is_sel else (0.2, 1.0, 0.2)
            self.draw_node(node.x, node.y, node.z, color=color)
            if node.is_supported:
                self._draw_support(node.x, node.y, node.z, node.support_type.value)

        # Members
        for member in document.members.values():
            n1 = document.nodes[member.start_node_id]
            n2 = document.nodes[member.end_node_id]
            is_sel = (member.id == document.selected_member_id)
            color = (1.0, 0.8, 0.0) if is_sel else (0.3, 0.7, 1.0)
            self.draw_member(n1.x, n1.y, n1.z, n2.x, n2.y, n2.z, color=color)

    def draw_deformed_shape(self, document, analysis_result, scale=50.0):
        """Overlay deformed geometry in red, scaled for visibility."""
        if not analysis_result or not analysis_result.success:
            return
        glColor3f(1.0, 0.2, 0.2)
        glLineWidth(2.5)
        glBegin(GL_LINES)
        for member in document.members.values():
            r1 = analysis_result.node_results.get(member.start_node_id)
            r2 = analysis_result.node_results.get(member.end_node_id)
            if r1 and r2:
                n1 = document.nodes[member.start_node_id]
                n2 = document.nodes[member.end_node_id]
                glVertex3f(n1.x + r1.dx * scale, n1.y + r1.dy * scale, n1.z + r1.dz * scale)
                glVertex3f(n2.x + r2.dx * scale, n2.y + r2.dy * scale, n2.z + r2.dz * scale)
        glEnd()
        glLineWidth(1.0)

    # ── Support symbols ──────────────────────────────

    def _draw_support(self, x, y, z, stype: str):
        """Draw a support symbol at node position."""
        glPushMatrix()
        glTranslatef(x, y, z)
        glColor3f(0.2, 1.0, 0.2)
        s = 0.3

        if stype == "pinned":
            glBegin(GL_TRIANGLES)
            glVertex3f(-s, -s * 0.3, 0); glVertex3f(s, -s * 0.3, 0)
            glVertex3f(0, -s, 0)
            glEnd()
        elif stype == "fixed":
            glBegin(GL_TRIANGLES)
            glVertex3f(-s, 0, 0); glVertex3f(s, 0, 0); glVertex3f(0, -s, 0)
            glEnd()
            glLineWidth(1.5)
            glBegin(GL_LINES)
            for dy in (0.05, 0.15, 0.25):
                glVertex3f(-s * 0.8, -dy, 0); glVertex3f(s * 0.8, -dy, 0)
            glEnd()
            glLineWidth(1.0)
        elif stype.startswith("roller"):
            quad = gluNewQuadric()
            gluSphere(quad, s * 0.35, 8, 6)
            gluDeleteQuadric(quad)

        glPopMatrix()
