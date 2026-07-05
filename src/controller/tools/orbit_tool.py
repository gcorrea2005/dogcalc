"""Orbit tool — Left drag=rotate, Right drag=pan, Scroll=zoom (Mac friendly)."""

from PySide6.QtCore import Qt
from PySide6.QtGui import QMouseEvent, QCursor
from src.controller.tools.base_tool import BaseTool
from math import pi


class OrbitTool(BaseTool):
    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.OpenHandCursor)

    def activate(self):
        if hasattr(self.view, '_status_callback') and self.view._status_callback:
            self.view._status_callback("LEFT=rotate RIGHT=pan Scroll=zoom")

    def mouse_press(self, event: QMouseEvent, scene_pos):
        self.view._last_mouse = event.pos()
        if event.button() == Qt.MouseButton.LeftButton:
            self.view.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouse_move(self, event: QMouseEvent, scene_pos):
        if self.view._last_mouse is None:
            self.view._last_mouse = event.pos()
            return
        dx = event.pos().x() - self.view._last_mouse.x()
        dy = event.pos().y() - self.view._last_mouse.y()
        if event.buttons() & Qt.MouseButton.LeftButton:
            self.view._angle += dx * 0.005
            self.view.refresh_view()
        elif event.buttons() & Qt.MouseButton.RightButton:
            self.view._offset_x += dx
            self.view._offset_y += dy
            self.view.refresh_view()
        self.view._last_mouse = event.pos()

    def mouse_release(self, event: QMouseEvent, scene_pos):
        self.view.setCursor(Qt.CursorShape.OpenHandCursor)

    def key_press(self, event):
        if event.key() == Qt.Key.Key_Left:   self.view._angle -= 0.1; self.view.refresh_view()
        elif event.key() == Qt.Key.Key_Right: self.view._angle += 0.1; self.view.refresh_view()
        elif event.key() == Qt.Key.Key_Up:    self.view._offset_y += 30; self.view.refresh_view()
        elif event.key() == Qt.Key.Key_Down:  self.view._offset_y -= 30; self.view.refresh_view()
