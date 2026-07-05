"""DeleteTool — select entity and press Delete/Backspace, or double-click to delete."""

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QMouseEvent, QKeyEvent, QCursor
from src.controller.tools.select_tool import SelectTool


class DeleteTool(SelectTool):
    """Click entity to select, then:
       - Press Delete/Backspace to remove it
       - Click same entity again to remove it
    """

    def cursor(self) -> QCursor:
        return QCursor(Qt.CursorShape.ForbiddenCursor)

    def activate(self):
        super().activate()
        if hasattr(self.view, '_status_callback') and self.view._status_callback:
            self.view._status_callback("Delete: Click entity, then DEL key or click again")

    def mouse_press(self, event: QMouseEvent, scene_pos: QPointF):
        prev_id = self.document.selected_node_id or self.document.selected_member_id
        prev_type = self.selected_type

        super().mouse_press(event, scene_pos)

        current_id = self.document.selected_node_id or self.document.selected_member_id

        # If same entity clicked again → delete
        if current_id and current_id == prev_id and self.selected_type == prev_type:
            entity = None
            if self.selected_type == 'node':
                entity = self.document.nodes.get(current_id)
            elif self.selected_type == 'member':
                entity = self.document.members.get(current_id)

            if entity:
                label = entity.label
                self.document.delete_entity(current_id)
                self._clear_selection()
                self.view.update()
                if hasattr(self.view, '_status_callback') and self.view._status_callback:
                    self.view._status_callback(f"Deleted: {label}")

    def key_press(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            eid = self.document.selected_node_id or self.document.selected_member_id
            if eid:
                entity = None
                if self.document.selected_node_id:
                    entity = self.document.nodes.get(eid)
                elif self.document.selected_member_id:
                    entity = self.document.members.get(eid)

                if entity:
                    label = entity.label
                    self.document.delete_entity(eid)
                    self._clear_selection()
                    self.view.update()
                    if hasattr(self.view, '_status_callback') and self.view._status_callback:
                        self.view._status_callback(f"Deleted: {label}")
