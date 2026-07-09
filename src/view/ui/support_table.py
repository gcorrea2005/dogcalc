"""Support Editor — STAAD-style spreadsheet for nodal supports."""

from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QComboBox, QPushButton, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from src.model.entities.node import SupportType

EMPTY_ROWS = 3

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
COLUMNS = ["Node", "Support", ""]
COL_WIDTHS = [60, 100, 32]


class SupportTable(QDockWidget):
    """STAAD-style spreadsheet for nodal supports.

    - Shows only nodes that have supports (not FREE).
    - Dropdown to change support type per node.
    - Empty rows to add support to currently unsupported nodes.
    """

    supports_changed = Signal()

    def __init__(self, document, parent=None):
        super().__init__("SUPPORT EDITOR", parent)
        self._doc = document
        self._suppress = False

        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.setMinimumWidth(220)

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget(0, len(COLUMNS))
        self._table.setHorizontalHeaderLabels(COLUMNS)
        self._table.setStyleSheet(TABLE_STYLE)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(False)
        for i, w in enumerate(COL_WIDTHS):
            self._table.setColumnWidth(i, w)
        self._table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        layout.addWidget(self._table)
        self.setWidget(body)

    # ── Refresh ───────────────────────────────────

    def refresh(self):
        """Rebuild table: supported nodes + empty rows for unsupported nodes."""
        self._suppress = True

        supported = [n for n in self._doc.node_list() if n.support_type != SupportType.FREE]
        unsupported = [n for n in self._doc.node_list() if n.support_type == SupportType.FREE]
        total = len(supported) + min(EMPTY_ROWS, len(unsupported))
        self._table.setRowCount(total)

        for row, node in enumerate(supported):
            self._fill_support_row(row, node)

        for i, node in enumerate(unsupported[:EMPTY_ROWS]):
            self._fill_empty_row(len(supported) + i, node)

        self._suppress = False

    def _fill_support_row(self, row, node):
        """Row for a supported node."""
        lbl = QTableWidgetItem(node.label)
        lbl.setFlags(lbl.flags() & ~Qt.ItemFlag.ItemIsEditable)
        lbl.setForeground(QColor("#88CCFF"))
        lbl.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setData(Qt.ItemDataRole.UserRole, node.id)
        self._table.setItem(row, 0, lbl)

        combo = QComboBox()
        for st in SupportType:
            if st != SupportType.FREE:
                combo.addItem(st.value, st)
        combo.setCurrentText(node.support_type.value)
        combo.setStyleSheet(
            "QComboBox { background: #000033; color: #DDD; border: 1px solid #225; "
            "font: 11px 'Courier New'; padding: 1px 2px; }"
            "QComboBox::drop-down { border: none; }"
        )
        combo.currentIndexChanged.connect(
            lambda idx, nid=node.id, cb=combo: self._on_support_changed(nid, cb.itemData(idx))
        )
        self._table.setCellWidget(row, 1, combo)

        # Remove support button
        btn = QPushButton("X")
        btn.setFixedSize(24, 20)
        btn.setStyleSheet(
            "QPushButton { background: #330000; color: #FF4444; font-weight: bold; "
            "border: none; font-size: 10px; } QPushButton:hover { background: #660000; }"
        )
        btn.clicked.connect(self._on_remove)
        self._table.setCellWidget(row, 2, btn)

    def _fill_empty_row(self, row, node):
        """Row to add support to an unsupported node."""
        lbl = QTableWidgetItem(node.label)
        lbl.setFlags(Qt.ItemFlag.NoItemFlags)
        lbl.setForeground(QColor("#334455"))
        lbl.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setData(Qt.ItemDataRole.UserRole, node.id)
        self._table.setItem(row, 0, lbl)

        combo = QComboBox()
        combo.addItem("(add)", None)
        for st in SupportType:
            if st != SupportType.FREE:
                combo.addItem(st.value, st)
        combo.setStyleSheet(
            "QComboBox { background: #001122; color: #556677; border: 1px solid #1a1a3a; "
            "font: 11px 'Courier New'; padding: 1px 2px; }"
            "QComboBox::drop-down { border: none; }"
        )
        combo.currentIndexChanged.connect(
            lambda idx, nid=node.id, cb=combo: self._on_add_support(nid, cb.itemData(idx))
        )
        self._table.setCellWidget(row, 1, combo)

        empty = QTableWidgetItem("")
        empty.setFlags(Qt.ItemFlag.NoItemFlags)
        self._table.setItem(row, 2, empty)

    # ── Events ────────────────────────────────────

    def _on_support_changed(self, node_id: str, st):
        if node_id in self._doc.nodes and st is not None:
            self._doc.nodes[node_id].support_type = st
            self.supports_changed.emit()

    def _on_add_support(self, node_id: str, st):
        if st is None:
            return  # "(add)" selected, ignore
        if node_id in self._doc.nodes:
            self._doc.nodes[node_id].support_type = st
            self.supports_changed.emit()
            self.refresh()

    def _on_remove(self):
        """Set node support back to FREE."""
        btn = self.sender()
        if btn is None:
            return
        for row in range(self._table.rowCount()):
            if self._table.cellWidget(row, 2) is btn:
                item = self._table.item(row, 0)
                if item is None:
                    continue
                node_id = item.data(Qt.ItemDataRole.UserRole)
                if node_id and node_id in self._doc.nodes:
                    self._doc.nodes[node_id].support_type = SupportType.FREE
                    self.supports_changed.emit()
                    self.refresh()
                break
