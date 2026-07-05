"""StructView — 2D projection with orbit camera.

CRITICAL: items added to scene BEFORE super().__init__().
This is the ONLY pattern that renders on macOS.
"""

import numpy as np
from math import sin, cos, pi
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPen, QBrush, QColor, QPainter, QMouseEvent, QWheelEvent, QKeyEvent


class StructView(QGraphicsView):

    def __init__(self, document=None, parent=None):
        self.document = document
        self.tool_manager = None
        self.analysis_result = None
        self.show_deformed = False
        self.deformed_scale = 50.0

        # Fixed 2D transform params (viewport-independent)
        self._offset_x = 0.0
        self._offset_y = 0.0
        self._zoom = 40.0  # pixels per meter

        # Pre-draw scene BEFORE super().__init__
        self._scene = QGraphicsScene()
        self._scene.setSceneRect(-10000, -10000, 20000, 20000)
        self._draw_scene()
        super().__init__(self._scene, parent)

        self.setRenderHints(QPainter.RenderHint.Antialiasing)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setBackgroundBrush(QColor(15, 15, 25))
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self._status_callback = None
        self._last_mouse = None

    def _to_screen(self, wx, wy):
        """Simple 2D transform: world XY -> screen XY."""
        x = self._offset_x + wx * self._zoom
        y = self._offset_y - wy * self._zoom  # flip Y
        return QPointF(x, y)

    def _draw_scene(self):
        self._scene.clear()
        # DEBUG markers — always visible
        self._scene.addLine(-20, 0, 20, 0, QPen(QColor(255, 50, 50), 2))
        self._scene.addLine(0, -20, 0, 20, QPen(QColor(255, 50, 50), 2))
        self._scene.addLine(-15, -15, 15, 15, QPen(QColor(50, 255, 50), 2))

        if not self.document: return

        from src.model.entities.node import SupportType
        wp = QPen(QColor(255, 255, 255), 2); wb = QBrush(QColor(255, 255, 255))
        gp = QPen(QColor(50, 255, 50), 3); gb = QBrush(QColor(50, 255, 50))
        yp = QPen(QColor(255, 255, 0), 3); yb = QBrush(QColor(255, 255, 0))
        mp = QPen(QColor(80, 180, 255), 2)
        r = 4

        for n in self.document.nodes.values():
            p = self._to_screen(n.x, n.y)
            issel = (n.id == self.document.selected_node_id)
            pen = yp if issel else (gp if n.is_supported else wp)
            brush = yb if issel else (gb if n.is_supported else wb)
            self._scene.addEllipse(p.x()-r, p.y()-r, r*2, r*2, pen, brush)

        for m in self.document.members.values():
            n1 = self.document.nodes[m.start_node_id]
            n2 = self.document.nodes[m.end_node_id]
            p1 = self._to_screen(n1.x, n1.y)
            p2 = self._to_screen(n2.x, n2.y)
            issel = (m.id == self.document.selected_member_id)
            self._scene.addLine(p1.x(), p1.y(), p2.x(), p2.y(), yp if issel else mp)

    def refresh_view(self):
        self._draw_scene()

    def fit_to_model(self):
        if not self.document or self.document.node_count == 0: return
        xs = [n.x for n in self.document.nodes.values()]
        ys = [n.y for n in self.document.nodes.values()]
        cx = (max(xs)+min(xs))/2
        cy = (max(ys)+min(ys))/2
        span = max(max(xs)-min(xs), max(ys)-min(ys), 1.0)
        self._offset_x = -cx * self._zoom
        self._offset_y = cy * self._zoom
        self._zoom = 500 / span
        self._offset_x = -cx * self._zoom
        self._offset_y = cy * self._zoom
        self.refresh_view()

    def _screen_to_world(self, scene_pos):
        wx = (scene_pos.x() - self._offset_x) / self._zoom
        wy = -(scene_pos.y() - self._offset_y) / self._zoom
        return QPointF(wx, wy)

    def mousePressEvent(self, event: QMouseEvent):
        self._last_mouse = event.pos()
        if self.tool_manager and self.tool_manager.active_tool:
            w = self._screen_to_world(self.mapToScene(event.pos()))
            self.tool_manager.active_tool.mouse_press(event, w)
            self.refresh_view(); return
        if event.button() == Qt.MouseButton.MiddleButton:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent):
        if self.tool_manager and self.tool_manager.active_tool:
            w = self._screen_to_world(self.mapToScene(event.pos()))
            self.tool_manager.active_tool.mouse_move(event, w)
            self._last_mouse = event.pos(); return
        if self._last_mouse is None: self._last_mouse = event.pos(); return
        dx = event.pos().x() - self._last_mouse.x()
        dy = event.pos().y() - self._last_mouse.y()
        if event.buttons() & Qt.MouseButton.MiddleButton:
            self._offset_x += dx
            self._offset_y += dy
            self.refresh_view()
        self._last_mouse = event.pos()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.tool_manager and self.tool_manager.active_tool:
            w = self._screen_to_world(self.mapToScene(event.pos()))
            self.tool_manager.active_tool.mouse_release(event, w)
            self.refresh_view(); return
        self.setCursor(Qt.CursorShape.CrossCursor)

    def wheelEvent(self, event: QWheelEvent):
        # Zoom at mouse position
        old_pos = self.mapToScene(event.pos())
        f = 1.0 - event.angleDelta().y() * 0.001
        self._zoom = max(1.0, min(500.0, self._zoom * f))
        self.refresh_view()

    def keyPressEvent(self, event: QKeyEvent):
        if self.tool_manager and self.tool_manager.active_tool:
            self.tool_manager.active_tool.key_press(event); return
