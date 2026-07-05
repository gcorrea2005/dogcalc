"""SelectTool — click to select a node or member, showing info in status bar."""

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QMouseEvent, QCursor
from src.controller.tools.base_tool import BaseTool


class SelectTool(BaseTool):
    """Click on a node or member to select it. Deselect on empty click.

    Selected entity is highlighted yellow in the viewport.
    Property panel can read selected_entity_id to show properties.
    """

    def __init__(self, view, document):
        super().__init__(view, document)
        self.selected_type: str | None = None  # 'node' | 'member' | None

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.ArrowCursor)

    def activate(self):
        self._clear_selection()
        if hasattr(self.view, '_status_callback') and self.view._status_callback:
            self.view._status_callback("Select: Click node or member")

    def mouse_press(self, event: QMouseEvent, scene_pos: QPointF):
        wx, wz = scene_pos.x(), scene_pos.y()

        # Check nodes first (more precise)
        best_node = self._nearest_node(wx, wz, 0.6)
        if best_node:
            nid, node = best_node
            self.document.selected_node_id = nid
            self.document.selected_member_id = None
            self.selected_type = 'node'
            self.view.update()
            if hasattr(self.view, '_status_callback') and self.view._status_callback:
                s = node.support_type.value
                self.view._status_callback(
                    f"Node {node.label} | ({node.x:.3f}, {node.y:.3f}, {node.z:.3f}) | {s}"
                )
            return

        # Then members
        best_member = self._nearest_member(wx, wz, 0.4)
        if best_member:
            mid, member = best_member
            self.document.selected_member_id = mid
            self.document.selected_node_id = None
            self.selected_type = 'member'
            self.view.update()
            if hasattr(self.view, '_status_callback') and self.view._status_callback:
                n1 = self.document.nodes[member.start_node_id].label
                n2 = self.document.nodes[member.end_node_id].label
                self.view._status_callback(
                    f"Member {member.label} | {n1} → {n2} | {member.member_type.value}"
                )
            return

        # Empty click → deselect
        self._clear_selection()
        self.view.update()

    def _clear_selection(self):
        self.selected_type = None
        self.document.selected_node_id = None
        self.document.selected_member_id = None

    # ── Hit testing ──────────────────────────────

    def _nearest_node(self, wx, wz, tol):
        best, best_d = None, tol
        for nid, node in self.document.nodes.items():
            d = ((node.x - wx) ** 2 + (node.z - wz) ** 2) ** 0.5
            if d < best_d:
                best_d, best = d, (nid, node)
        return best

    def _nearest_member(self, wx, wz, tol):
        best, best_d = None, tol
        for mid, m in self.document.members.items():
            n1 = self.document.nodes[m.start_node_id]
            n2 = self.document.nodes[m.end_node_id]
            d = self._seg_dist(wx, wz, n1.x, n1.z, n2.x, n2.z)
            if d < best_d:
                best_d, best = d, (mid, m)
        return best

    @staticmethod
    def _seg_dist(px, py, x1, y1, x2, y2):
        dx, dy = x2 - x1, y2 - y1
        if dx == 0 and dy == 0:
            return ((px - x1) ** 2 + (py - y1) ** 2) ** 0.5
        t = max(0, min(1, ((px - x1) * dx + (py - y1) * dy) / (dx * dx + dy * dy)))
        return ((px - (x1 + t * dx)) ** 2 + (py - (y1 + t * dy)) ** 2) ** 0.5
