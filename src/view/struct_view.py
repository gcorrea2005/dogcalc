"""3D viewport using QGraphicsView — same approach as cad2d-lite.

Projects 3D world coords to 2D screen using the camera matrix.
No OpenGL needed — uses Qt's QGraphicsView (proven to work on macOS 15).
"""

import numpy as np
from math import sin, cos, pi
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsEllipseItem, QGraphicsLineItem
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QMouseEvent, QWheelEvent, QKeyEvent, QTransform


class StructView(QGraphicsView):
    """3D structural viewport using 2D graphics projection.

    Mouse: Middle drag=orbit, Shift+Middle=pan, Scroll=zoom
    """

    def __init__(self, document=None, parent=None):
        super().__init__(parent)
        self.document = document
        self.tool_manager = None
        self.analysis_result = None
        self.show_deformed = False
        self.deformed_scale = 50.0

        # Camera (spherical coords)
        self._theta = -pi / 6
        self._phi = 0.3
        self._radius = 20.0
        self._target = np.array([0.0, 0.0, 0.0])
        self._up = np.array([0.0, 1.0, 0.0])

        # Scene
        self._scene = QGraphicsScene()
        self._scene.setSceneRect(-1000, -1000, 2000, 2000)  # big visible area
        self.setScene(self._scene)
        self.setRenderHints(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QColor(15, 15, 25))
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.CrossCursor)

        # Callbacks
        self._status_callback = None
        self._on_mouse_move = None

        self._last_mouse = None
        self._grid_items = []
        self._model_items = []

        self._draw_grid()
        self._draw_model()

    # ── Camera ─────────────────────────────────────

    @property
    def camera_pos(self):
        x = self._target[0] + self._radius * cos(self._phi) * cos(self._theta)
        y = self._target[1] + self._radius * sin(self._phi)
        z = self._target[2] + self._radius * cos(self._phi) * sin(self._theta)
        return np.array([x, y, z])

    def _world_to_screen(self, wx, wy, wz):
        """Project 3D world point to 2D viewport coordinates."""
        eye = self.camera_pos
        forward = self._target - eye
        forward = forward / np.linalg.norm(forward)
        right = np.cross(forward, self._up)
        right = right / np.linalg.norm(right)
        cam_up = np.cross(right, forward)

        p = np.array([wx, wy, wz]) - eye
        sx = np.dot(p, right)
        sy = np.dot(p, cam_up)
        sz = np.dot(p, forward)

        if sz < 0.01:
            return None  # behind camera

        vp_w = self.viewport().width()
        vp_h = self.viewport().height()
        scale = vp_w / (2.0 * self._radius * 0.05)
        return QPointF(vp_w / 2 + sx * scale, vp_h / 2 - sy * scale)

    # ── Drawing ────────────────────────────────────

    def _draw_grid(self):
        """Draw reference grid on XZ plane (Y=0)."""
        pen = QPen(QColor(30, 35, 45), 0.5)
        n, s = 20, 1.0
        for i in range(-n, n + 1):
            p1 = self._world_to_screen(i * s, 0, -n * s)
            p2 = self._world_to_screen(i * s, 0, n * s)
            if p1 and p2:
                self._scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), pen)
            p1 = self._world_to_screen(-n * s, 0, i * s)
            p2 = self._world_to_screen(n * s, 0, i * s)
            if p1 and p2:
                self._scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), pen)

    def _clear_model(self):
        for item in self._model_items:
            self._scene.removeItem(item)
        self._model_items.clear()

    def _draw_model(self):
        """Draw nodes and members from document."""
        self._clear_model()
        if not self.document:
            return

        from src.model.entities.node import SupportType

        node_pen = QPen(QColor(255, 255, 255), 2)
        node_brush = QBrush(QColor(255, 255, 255))
        supp_pen = QPen(QColor(50, 255, 50), 2.5)
        supp_brush = QBrush(QColor(50, 255, 50))
        sel_pen = QPen(QColor(255, 255, 0), 3)
        sel_brush = QBrush(QColor(255, 255, 0))

        # Nodes
        for node in self.document.nodes.values():
            p = self._world_to_screen(node.x, node.y, node.z)
            if not p:
                continue
            r = 4
            is_sel = (node.id == self.document.selected_node_id)
            pen = sel_pen if is_sel else (supp_pen if node.is_supported else node_pen)
            brush = sel_brush if is_sel else (supp_brush if node.is_supported else node_brush)
            item = self._scene.addEllipse(p.x() - r, p.y() - r, r * 2, r * 2, pen, brush)
            self._model_items.append(item)

        # Members
        member_pen = QPen(QColor(80, 180, 255), 2)
        member_sel_pen = QPen(QColor(255, 255, 0), 3)
        for member in self.document.members.values():
            n1 = self.document.nodes[member.start_node_id]
            n2 = self.document.nodes[member.end_node_id]
            p1 = self._world_to_screen(n1.x, n1.y, n1.z)
            p2 = self._world_to_screen(n2.x, n2.y, n2.z)
            if not p1 or not p2:
                continue
            is_sel = (member.id == self.document.selected_member_id)
            pen = member_sel_pen if is_sel else member_pen
            item = self._scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), pen)
            self._model_items.append(item)

        # Deformed shape
        if self.show_deformed and self.analysis_result and self.analysis_result.success:
            def_pen = QPen(QColor(255, 50, 50), 2.5)
            for member in self.document.members.values():
                r1 = self.analysis_result.node_results.get(member.start_node_id)
                r2 = self.analysis_result.node_results.get(member.end_node_id)
                if r1 and r2:
                    n1 = self.document.nodes[member.start_node_id]
                    n2 = self.document.nodes[member.end_node_id]
                    s = self.deformed_scale
                    p1 = self._world_to_screen(n1.x + r1.dx * s, n1.y + r1.dy * s, n1.z + r1.dz * s)
                    p2 = self._world_to_screen(n2.x + r2.dx * s, n2.y + r2.dy * s, n2.z + r2.dz * s)
                    if p1 and p2:
                        item = self._scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), def_pen)
                        self._model_items.append(item)

    def refresh_view(self):
        """Redraw grid and model."""
        self._scene.clear()
        self._model_items.clear()
        self._draw_grid()
        self._draw_model()

    # ── Mouse ──────────────────────────────────────

    def mousePressEvent(self, event: QMouseEvent):
        self._last_mouse = event.pos()

        if self.tool_manager and self.tool_manager.active_tool:
            scene_pos = self.mapToScene(event.pos())
            world = self._screen_to_world(scene_pos)
            self.tool_manager.active_tool.mouse_press(event, world)
            self.refresh_view()
            return

        if event.button() == Qt.MouseButton.MiddleButton:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.tool_manager and self.tool_manager.active_tool:
            scene_pos = self.mapToScene(event.pos())
            world = self._screen_to_world(scene_pos)
            self.tool_manager.active_tool.mouse_move(event, world)
            self._last_mouse = event.pos()
            return

        if self._last_mouse is None:
            self._last_mouse = event.pos()
            return

        dx = event.pos().x() - self._last_mouse.x()
        dy = event.pos().y() - self._last_mouse.y()

        if event.buttons() & Qt.MouseButton.MiddleButton:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self._target += np.array([-dx * 0.02, dy * 0.02, 0.0])
            else:
                self._theta -= dx * 0.005
                self._phi += dy * 0.005
                self._phi = max(-pi / 2 + 0.01, min(pi / 2 - 0.01, self._phi))
            self.refresh_view()

        self._last_mouse = event.pos()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.tool_manager and self.tool_manager.active_tool:
            scene_pos = self.mapToScene(event.pos())
            world = self._screen_to_world(scene_pos)
            self.tool_manager.active_tool.mouse_release(event, world)
            self.refresh_view()
            return
        self.setCursor(Qt.CursorShape.CrossCursor)

    def wheelEvent(self, event: QWheelEvent):
        self._radius *= (1.0 - event.angleDelta().y() * 0.001)
        self._radius = max(1.0, min(200.0, self._radius))
        self.refresh_view()

    def keyPressEvent(self, event: QKeyEvent):
        if self.tool_manager and self.tool_manager.active_tool:
            self.tool_manager.active_tool.key_press(event)
            return
        if event.key() == Qt.Key.Key_R:
            self._theta, self._phi, self._radius = -pi / 6, 0.3, 20.0
            self._target = np.array([0.0, 0.0, 0.0])
            self.refresh_view()

    # ── Screen ↔ World ─────────────────────────────

    def _screen_to_world(self, scene_pos):
        """Approximate inverse projection — screen coords to world XZ plane at Y=0."""
        from PySide6.QtCore import QPointF
        vp_w = self.viewport().width()
        vp_h = self.viewport().height()
        scale = self._radius * 0.05 * 2 / vp_w if vp_w else 0.01
        wx = self._target[0] + (scene_pos.x() - vp_w / 2) * scale
        wz = self._target[2] - (scene_pos.y() - vp_h / 2) * scale
        return QPointF(wx, wz)

    def fit_to_model(self):
        """Adjust camera to frame model."""
        doc = self.document
        if not doc or doc.node_count == 0:
            return
        xs = [n.x for n in doc.nodes.values()]
        ys = [n.y for n in doc.nodes.values()]
        zs = [n.z for n in doc.nodes.values()]
        self._target = np.array([(max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2, (max(zs) + min(zs)) / 2])
        span = max(max(xs) - min(xs), max(ys) - min(ys), max(zs) - min(zs), 1.0)
        self._radius = span * 1.8
        self.refresh_view()
