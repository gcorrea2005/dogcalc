"""Command Line — single-line text input with command history (like AutoCAD / STAAD)."""

from PySide6.QtWidgets import QPlainTextEdit
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent, QTextCursor


class CommandLine(QPlainTextEdit):
    """STAAD-style command input with history navigation (Up/Down arrows).

    Supported commands:
      NODE x,y,z          — create node
      MEMBER n1,n2        — create member between nodes n1 and n2 (1-indexed)
      SUPPORT n TYPE      — set support (FIXED, PINNED, ROLLER_X/Y/Z)
      LOAD lc n fx fy fz  — apply nodal load
      ANALYZE             — run analysis
      ZOOM E              — zoom extents
    """

    command_entered = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._history: list[str] = []
        self._history_index = -1
        self._current_input = ""

        self.setFixedHeight(28)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTabChangesFocus(False)
        self.setPlaceholderText("Command: _")

        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #000018;
                color: #FFFFFF;
                border: 1px solid #1a1a2e;
                font-family: 'Courier New', monospace;
                font-size: 14px;
                padding: 4px 8px;
            }
        """)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            cmd = self.toPlainText().strip()
            if cmd:
                self._history.append(cmd)
                self._history_index = len(self._history)
                self.command_entered.emit(cmd)
                self.clear()
            return

        elif event.key() == Qt.Key.Key_Up:
            if self._history and self._history_index > 0:
                if self._history_index == len(self._history):
                    self._current_input = self.toPlainText()
                self._history_index -= 1
                self.setPlainText(self._history[self._history_index])
                self.moveCursor(QTextCursor.MoveOperation.End)
            return

        elif event.key() == Qt.Key.Key_Down:
            end = len(self._history)
            if self._history_index < end - 1:
                self._history_index += 1
                self.setPlainText(self._history[self._history_index])
                self.moveCursor(QTextCursor.MoveOperation.End)
            elif self._history_index == end - 1:
                self._history_index = end
                self.setPlainText(self._current_input)
                self.moveCursor(QTextCursor.MoveOperation.End)
            return

        elif event.key() == Qt.Key.Key_Escape:
            self.clear()
            return

        super().keyPressEvent(event)
