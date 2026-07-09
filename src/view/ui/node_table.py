"""Node Editor — STAAD.Pro V8i-style spreadsheet for structural nodes."""

from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

EMPTY_ROWS = 5

HEADER_STYLE = """
    QHeaderView::section {
        background: #001133; color: #44AAFF; font-weight: bold;
        padding: 2px 4px; border: 1px solid #112244; font-size: 11px;
    }
"""
TABLE_STYLE = f"""
    QTableWidget {{
        background: #000018; color: #CCD;
        gridline-color: #1a1a3a; font: 12px 'Courier New';
        border: 1px solid #1a1a3a;
    }}
    QTableWidget::item:selected {{ background: #003366; color: #FFF; }}
    QTableWidget::item {{ padding: 2px 4px; }}
    {HEADER_STYLE}
"""
COLUMNS = ["#", "X (m)", "Y (m)", "Z (m)", ""]
COL_WIDTHS = [40, 85, 85, 85, 32]


class NodeTable(QDockWidget):
    """STAAD-style spreadsheet node editor — coordinates only, no supports.

    - Always shows 5 empty rows at the bottom for new nodes.
    - Single-click to edit any cell.
    - Typing in an empty row auto-creates a node.
    - Real-time 3D sync on every change.
    """

    node_changed = Signal()

    def __init__(self, document, parent=None):
        super().__init__("NODE EDITOR", parent)
        self._doc = document
        self._suppress = False

        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.setMinimumWidth(300)

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget(0, len(COLUMNS))
        self._table.setHorizontalHeaderLabels(COLUMNS)
        self._table.setStyleSheet(TABLE_STYLE)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(
            QAbstractItemView.EditTrigger.CurrentChanged |
            QAbstractItemView.EditTrigger.SelectedClicked
        )
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(False)
        for i, w in enumerate(COL_WIDTHS):
            self._table.setColumnWidth(i, w)
        self._table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        self._table.cellChanged.connect(self._on_cell_changed)
        layout.addWidget(self._table)
        self.setWidget(body)

    # ── Refresh ───────────────────────────────────

    def refresh(self):
        """Rebuild table: existing nodes + empty rows."""
        self._suppress = True
        nodes = self._doc.node_list()
        total = len(nodes) + EMPTY_ROWS
        self._table.setRowCount(total)

        for row in range(total):
            if row < len(nodes):
                self._fill_node_row(row, nodes[row])
            else:
                self._fill_empty_row(row)

        self._suppress = False

    def _fill_node_row(self, row, node):
        """Populate row with existing node data."""
        # Label (read-only)
        lbl = QTableWidgetItem(node.label)
        lbl.setFlags(lbl.flags() & ~Qt.ItemFlag.ItemIsEditable)
        lbl.setForeground(QColor("#88CCFF"))
        lbl.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setData(Qt.ItemDataRole.UserRole, node.id)  # store ID for delete
        self._table.setItem(row, 0, lbl)

        # Coordinates (editable)
        for col, val in enumerate([node.x, node.y, node.z], 1):
            item = QTableWidgetItem(f"{val:.3f}")
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, col, item)

        # Delete button
        btn = QPushButton("X")
        btn.setFixedSize(24, 20)
        btn.setStyleSheet(
            "QPushButton { background: #330000; color: #FF4444; font-weight: bold; "
            "border: none; font-size: 10px; } QPushButton:hover { background: #660000; }"
        )
        btn.clicked.connect(self._on_delete)
        self._table.setCellWidget(row, 4, btn)

    def _fill_empty_row(self, row):
        """Populate row with empty editable cells for new node creation."""
        # Empty label
        lbl = QTableWidgetItem("")
        lbl.setFlags(Qt.ItemFlag.NoItemFlags)
        lbl.setForeground(QColor("#223344"))
        self._table.setItem(row, 0, lbl)

        # Empty coordinate cells (editable)
        for col in range(1, 4):
            item = QTableWidgetItem("")
            item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            item.setForeground(QColor("#334455"))
            self._table.setItem(row, col, item)

        # No delete button
        empty = QTableWidgetItem("")
        empty.setFlags(Qt.ItemFlag.NoItemFlags)
        self._table.setItem(row, 4, empty)

    # ── Events ────────────────────────────────────

    def _on_cell_changed(self, row: int, col: int):
        if self._suppress:
            return
        if col not in (1, 2, 3):
            return

        nodes = self._doc.node_list()

        if row >= len(nodes):
            # Empty row — auto-create node
            self._create_node_from_row(row)
            return

        # Existing node — update coordinate
        node = nodes[row]
        item = self._table.item(row, col)
        if item is None:
            return
        text = item.text().strip()
        if not text or text == "-":
            return
        try:
            val = float(text)
            axis = {1: 'x', 2: 'y', 3: 'z'}[col]
            setattr(node, axis, val)
            self.node_changed.emit()
        except ValueError:
            self._suppress = True
            current = getattr(node, {1: 'x', 2: 'y', 3: 'z'}[col])
            item.setText(f"{current:.3f}")
            self._suppress = False

    def _create_node_from_row(self, row: int):
        """Create a new node from values in an empty row."""
        x = self._cell_value(row, 1)
        y = self._cell_value(row, 2)
        z = self._cell_value(row, 3)
        node = self._doc.add_node(x, y, z)
        self.node_changed.emit()
        self.refresh()
        new_row = min(self._doc.node_count, self._table.rowCount() - 1)
        self._table.setCurrentCell(new_row, self._table.currentColumn())
        item = self._table.item(new_row, self._table.currentColumn())
        if item is not None:
            self._table.editItem(item)

    def _cell_value(self, row: int, col: int) -> float:
        item = self._table.item(row, col)
        if item is None:
            return 0.0
        text = item.text().strip()
        if not text or text == "-":
            return 0.0
        try:
            return float(text)
        except ValueError:
            return 0.0

    def _on_delete(self):
        """Find sender button row, delete node, remove row."""
        btn = self.sender()
        if btn is None:
            return
        # Find row of this button
        for row in range(self._table.rowCount()):
            if self._table.cellWidget(row, 4) is btn:
                item = self._table.item(row, 0)
                if item is None:
                    continue
                node_id = item.data(Qt.ItemDataRole.UserRole)
                if node_id:
                    self._doc.delete_entity(node_id)
                    self.node_changed.emit()
                    self._suppress = True
                    self._table.removeRow(row)
                    self._suppress = False
                break
