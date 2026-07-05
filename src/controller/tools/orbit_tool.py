"""Default tool: orbit/pan/zoom. Does NOT modify the document."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent, QCursor
from src.controller.tools.base_tool import BaseTool
from math import pi
import numpy as np


class OrbitTool(BaseTool):
    """Viewport navigation — orbit, pan, zoom.

    Middle-button drag: orbit
    Shift + middle-button drag: pan
    Scroll wheel: zoom
    """

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.OpenHandCursor)

    def activate(self):
        if hasattr(self.view, '_status_callback') and self.view._status_callback:
            self.view._status_callback("Orbit: MIDDLE=rotate Shift+MIDDLE=pan Scroll=zoom")

    def mouse_press(self, event: QMouseEvent, scene_pos):
        self.view._last_mouse = event.pos()
        if event.button() == Qt.MouseButton.MiddleButton:
            self.view.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouse_move(self, event: QMouseEvent, scene_pos):
        if self.view._last_mouse is None:
            self.view._last_mouse = event.pos()
            return
        dx = event.pos().x() - self.view._last_mouse.x()
        dy = event.pos().y() - self.view._last_mouse.y()

        if event.buttons() & Qt.MouseButton.MiddleButton:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.view._target += np.array([-dx * 0.02, dy * 0.02, 0.0])
            else:
                self.view._theta -= dx * 0.005
                self.view._phi += dy * 0.005
                self.view._phi = max(-pi / 2 + 0.01, min(pi / 2 - 0.01, self.view._phi))
            self.view.refresh_view()

        self.view._last_mouse = event.pos()

    def mouse_release(self, event: QMouseEvent, scene_pos):
        self.view.setCursor(Qt.CursorShape.OpenHandCursor)
