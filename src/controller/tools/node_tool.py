"""NodeTool — create structural nodes with double-click on the viewport grid."""

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QMouseEvent, QCursor
from src.controller.tools.base_tool import BaseTool


class NodeTool(BaseTool):
    """Double-click on grid plane (XZ, Y=0) to create a node.

    Grid snap: position snaps to nearest 1.0m grid intersection.
    """

    def __init__(self, view, document):
        super().__init__(view, document)
        self._grid_snap = 1.0

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.CrossCursor)

    def activate(self):
        if hasattr(self.view, '_status_callback') and self.view._status_callback:
            self.view._status_callback("Node: Double-click on grid to place node | ESC to cancel")

    def mouse_double_click(self, event: QMouseEvent, scene_pos: QPointF):
        x, y, z = self._snap(scene_pos)
        label = f"N{self.document.node_count + 1}"
        node = self.document.add_node(x, y, z, label=label)
        self.view.refresh_view()
        if hasattr(self.view, '_status_callback') and self.view._status_callback:
            self.view._status_callback(
                f"Node {label} created at ({x:.2f}, {y:.2f}, {z:.2f})"
            )

    def _snap(self, pos: QPointF) -> tuple[float, float, float]:
        """Snap to grid on XZ plane (Y=0)."""
        g = self._grid_snap
        x = round(pos.x() / g) * g
        z = round(pos.y() / g) * g  # screen Y maps to world Z
        return (x, 0.0, z)
