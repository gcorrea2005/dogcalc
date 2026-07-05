"""MemberTool — connect two existing nodes by clicking them."""

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QMouseEvent, QCursor
from src.controller.tools.base_tool import BaseTool


class MemberTool(BaseTool):
    """Click first node → click second node → creates a member (beam).

    Visual feedback: highlights the selected start node.
    """

    def __init__(self, view, document):
        super().__init__(view, document)
        self._first_node_id: str | None = None

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.PointingHandCursor)

    def activate(self):
        self._first_node_id = None
        if hasattr(self.view, '_status_callback') and self.view._status_callback:
            self.view._status_callback("Member: Click start node → click end node")

    def mouse_press(self, event: QMouseEvent, scene_pos: QPointF):
        nearest = self._find_nearest_node(scene_pos.x(), scene_pos.y(), tolerance=0.8)
        if nearest is None:
            return

        nid, node = nearest

        if self._first_node_id is None:
            # First click: select start node
            self._first_node_id = nid
            self.document.selected_node_id = nid  # highlight in viewport
            self.view.refresh_view()
            if hasattr(self.view, '_status_callback') and self.view._status_callback:
                self.view._status_callback(f"Start: {node.label} → click end node")
        elif nid == self._first_node_id:
            # Click same node = deselect
            self._first_node_id = None
            self.document.selected_node_id = None
            self.view.refresh_view()
        else:
            # Second click: create member
            label = f"M{self.document.member_count + 1}"
            member = self.document.add_member(self._first_node_id, nid, label=label)
            n1_label = self.document.nodes[self._first_node_id].label
            self.document.selected_node_id = None
            self._first_node_id = None
            self.view.refresh_view()
            if hasattr(self.view, '_status_callback') and self.view._status_callback:
                self.view._status_callback(
                    f"Member {label}: {n1_label} → {node.label}"
                )

    def _find_nearest_node(self, wx: float, wz: float, tolerance: float = 0.8):
        """Find the node closest to world position (XZ plane)."""
        best = None
        best_dist = tolerance
        for nid, node in self.document.nodes.items():
            dist = ((node.x - wx) ** 2 + (node.z - wz) ** 2) ** 0.5
            if dist < best_dist:
                best_dist = dist
                best = (nid, node)
        return best
