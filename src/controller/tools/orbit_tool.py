"""Default tool: orbit/pan/zoom. Does NOT modify the document."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent, QCursor
from src.controller.tools.base_tool import BaseTool


class OrbitTool(BaseTool):
    """Viewport navigation only — orbit, pan, zoom.

    Middle-button drag: orbit
    Shift + middle-button drag: pan
    Scroll wheel: zoom
    """

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.OpenHandCursor)

    def activate(self):
        if hasattr(self.view, '_status_callback') and self.view._status_callback:
            self.view._status_callback("Orbit: MIDDLE drag=rotate, Shift+MIDDLE=pan, Scroll=zoom")

    def mouse_press(self, event: QMouseEvent, scene_pos):
        self.view._last_mouse = event.pos()
        if event.button() == Qt.MouseButton.MiddleButton:
            self.view.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouse_move(self, event: QMouseEvent, scene_pos):
        dx = event.pos().x() - self.view._last_mouse.x()
        dy = event.pos().y() - self.view._last_mouse.y()

        if event.buttons() & Qt.MouseButton.MiddleButton:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.view.camera.pan(dx, dy)
            else:
                self.view.camera.orbit(dx, dy)
            self.view.update()

        # Update coordinate display
        if hasattr(self.view, '_on_mouse_move') and self.view._on_mouse_move:
            self.view._on_mouse_move(scene_pos)

        self.view._last_mouse = event.pos()

    def mouse_release(self, event: QMouseEvent, scene_pos):
        self.view.setCursor(Qt.CursorShape.OpenHandCursor)
