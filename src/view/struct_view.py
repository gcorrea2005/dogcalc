"""3D viewport for structural model — QOpenGLWidget with orbit camera."""

from PySide6.QtOpenGLWidgets import QOpenGLWidget
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QMouseEvent, QWheelEvent, QKeyEvent
from src.view.camera import OrbitCamera
from src.view.renderer import Renderer


class StructView(QOpenGLWidget):
    """Main 3D viewport. Renders grid, axes, nodes, members, loads, deformed shape.

    Mouse controls:
      - Middle-button drag: orbit
      - Shift + middle-button drag: pan
      - Scroll wheel: zoom
    """

    def __init__(self, document=None, parent=None):
        super().__init__(parent)
        self.camera = OrbitCamera()
        self.renderer = Renderer()
        self.document = document           # model.Document reference
        self.tool_manager = None           # set by MainWindow
        self.analysis_result = None        # last analysis result
        self.show_deformed = False         # toggle deformed overlay
        self.deformed_scale = 50.0         # deformation magnification
        self._last_mouse = QPoint()
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.CrossCursor)

        # Callbacks set by MainWindow
        self._status_callback = None
        self._on_mouse_move = None

    # ── OpenGL lifecycle ─────────────────────────────

    def initializeGL(self):
        self.renderer.initialize()

    def resizeGL(self, w: int, h: int):
        self.renderer.resize(w, h)

    def paintGL(self):
        self.renderer.begin_frame(self.camera)
        self.renderer.draw_grid()
        self.renderer.draw_axes()

        if self.document:
            try:
                self.renderer.draw_model(self.document)
            except Exception as e:
                import traceback
                print(f"draw_model error: {e}")
                traceback.print_exc()
            if self.show_deformed and self.analysis_result:
                try:
                    self.renderer.draw_deformed_shape(
                        self.document, self.analysis_result, self.deformed_scale
                    )
                except Exception:
                    pass

    # ── Mouse events — default orbit/pan/zoom ────────

    def mousePressEvent(self, event: QMouseEvent):
        self._last_mouse = event.pos()

        # Delegate to active tool if available
        if self.tool_manager and self.tool_manager.active_tool:
            scene_pos = self._screen_to_world(event.pos())
            if event.type() == QMouseEvent.Type.MouseButtonDblClick:
                self.tool_manager.active_tool.mouse_double_click(event, scene_pos)
            else:
                self.tool_manager.active_tool.mouse_press(event, scene_pos)
            self.update()
            return

        # Default orbit behavior
        if event.button() == Qt.MouseButton.MiddleButton:
            self.setCursor(Qt.CursorShape.ClosedHandCursor)

    def mouseMoveEvent(self, event: QMouseEvent):
        # Delegate to active tool
        if self.tool_manager and self.tool_manager.active_tool:
            scene_pos = self._screen_to_world(event.pos())
            self.tool_manager.active_tool.mouse_move(event, scene_pos)
            if self._on_mouse_move:
                self._on_mouse_move(scene_pos)
            self._last_mouse = event.pos()
            return

        # Default orbit behavior
        dx = event.pos().x() - self._last_mouse.x()
        dy = event.pos().y() - self._last_mouse.y()
        if event.buttons() & Qt.MouseButton.MiddleButton:
            if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
                self.camera.pan(dx, dy)
            else:
                self.camera.orbit(dx, dy)
            self.update()

        if self._on_mouse_move:
            scene_pos = self._screen_to_world(event.pos())
            self._on_mouse_move(scene_pos)
        self._last_mouse = event.pos()

    def mouseReleaseEvent(self, event: QMouseEvent):
        if self.tool_manager and self.tool_manager.active_tool:
            scene_pos = self._screen_to_world(event.pos())
            self.tool_manager.active_tool.mouse_release(event, scene_pos)
            self.update()
            return
        self.setCursor(Qt.CursorShape.CrossCursor)

    def wheelEvent(self, event: QWheelEvent):
        self.camera.zoom(event.angleDelta().y())
        self.update()

    # ── Keyboard ─────────────────────────────────────

    def keyPressEvent(self, event: QKeyEvent):
        # Delegate to tool
        if self.tool_manager and self.tool_manager.active_tool:
            self.tool_manager.active_tool.key_press(event)
            return

        # Global hotkeys
        if event.key() == Qt.Key.Key_F:
            self.zoom_extents()
        elif event.key() == Qt.Key.Key_R:
            self.camera = OrbitCamera()
            self.update()
        elif event.key() == Qt.Key.Key_G:
            self.renderer.draw_grid_enabled = not self.renderer.draw_grid_enabled
            self.update()
        else:
            super().keyPressEvent(event)

    # ── Zoom utilities ───────────────────────────────

    def zoom_extents(self):
        """Fit all model content in view."""
        # Simple implementation: reset camera to default position
        self.camera = OrbitCamera()
        self.update()

    def zoom_previous(self):
        """Placeholder for zoom previous."""
        pass

    def zoom_in(self):
        self.camera.zoom(500)
        self.update()

    def zoom_out(self):
        self.camera.zoom(-500)
        self.update()

    # ── Screen ↔ World conversion ────────────────────

    def _screen_to_world(self, screen_pos) -> QPointF:
        """Convert screen position to world coordinates (XZ plane at Y=0).

        This is a simplified approximation. For precise 3D picking,
        use gluUnProject with depth buffer in future iterations.
        """
        vp_w = self.width()
        vp_h = self.height()
        if vp_w == 0 or vp_h == 0:
            return QPointF(0, 0)

        scale = self.camera.radius / 10.0
        wx = (screen_pos.x() - vp_w / 2) * scale + self.camera.target[0]
        # Qt Y is inverted relative to world Z
        wz = -(screen_pos.y() - vp_h / 2) * scale + self.camera.target[2]
        return QPointF(wx, wz)
