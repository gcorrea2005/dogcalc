"""Base class for all interaction tools.

Pattern: identical to cad2d-lite's BaseTool.
Tools receive mouse/key events forwarded from StructView.
Each tool manipulates the Document through a clean interface.
"""

from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QCursor, QMouseEvent, QKeyEvent


class BaseTool:
    """Base class for structural modeling tools.

    Lifecycle:
      1. activate()   — tool becomes active, set up state
      2. mouse_*()    — user interacts via StructView
      3. deactivate() — tool is being switched away, clean up
    """

    def __init__(self, view, document):
        self.view = view       # StructView instance
        self.document = document  # model.Document instance

    def activate(self):
        """Called when this tool becomes the active tool."""
        pass

    def deactivate(self):
        """Called when switching away from this tool."""
        pass

    def cursor(self) -> QCursor:
        """Default cursor shape for this tool."""
        return QCursor(Qt.CursorShape.CrossCursor)

    # ── Mouse events ──────────────────────────────

    def mouse_press(self, event: QMouseEvent, scene_pos: QPointF):
        """Handle mouse press at world position (XZ plane)."""
        pass

    def mouse_move(self, event: QMouseEvent, scene_pos: QPointF):
        """Handle mouse move — useful for preview/feedback."""
        pass

    def mouse_release(self, event: QMouseEvent, scene_pos: QPointF):
        """Handle mouse release."""
        pass

    def mouse_double_click(self, event: QMouseEvent, scene_pos: QPointF):
        """Handle double-click."""
        pass

    # ── Keyboard ────────────────────────────────

    def key_press(self, event: QKeyEvent):
        """Handle key press while this tool is active."""
        pass
