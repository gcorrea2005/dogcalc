"""Member Editor — STAAD.Pro V8i-style spreadsheet for structural members."""

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
COLUMNS = ["#", "Start", "End", ""]
COL_WIDTHS = [40, 75, 75, 32]


class MemberTable(QDockWidget):
    """STAAD-style spreadsheet member editor — connectivity only.

    - Always shows 5 empty rows at the bottom for new members.
    - Single-click to edit start/end node cells.
    - Typing both nodes in an empty row auto-creates a member.
    - Real-time 3D sync on every change.
    """

    member_changed = Signal()

    def __init__(self, document, parent=None):
        super().__init__("MEMBER EDITOR", parent)
        self._doc = document
        self._suppress = False

        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.setMinimumWidth(230)

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
        """Rebuild table: existing members + empty rows."""
        self._suppress = True
        members = self._doc.member_list()
        total = len(members) + EMPTY_ROWS
        self._table.setRowCount(total)

        for row in range(total):
            if row < len(members):
                self._fill_member_row(row, members[row])
            else:
                self._fill_empty_row(row)

        self._suppress = False

    def _fill_member_row(self, row, member):
        """Populate row with existing member data."""
        # Label (read-only)
        lbl = QTableWidgetItem(member.label)
        lbl.setFlags(lbl.flags() & ~Qt.ItemFlag.ItemIsEditable)
        lbl.setForeground(QColor("#88CCFF"))
        lbl.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setData(Qt.ItemDataRole.UserRole, member.id)
        self._table.setItem(row, 0, lbl)

        # Start node (read-only)
        sn = self._doc.nodes.get(member.start_node_id)
        sn_text = sn.label if sn else member.start_node_id[:8]
        sn_item = QTableWidgetItem(sn_text)
        sn_item.setFlags(sn_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        sn_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, 1, sn_item)

        # End node (read-only)
        en = self._doc.nodes.get(member.end_node_id)
        en_text = en.label if en else member.end_node_id[:8]
        en_item = QTableWidgetItem(en_text)
        en_item.setFlags(en_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
        en_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, 2, en_item)

        # Delete button
        btn = QPushButton("X")
        btn.setFixedSize(24, 20)
        btn.setStyleSheet(
            "QPushButton { background: #330000; color: #FF4444; font-weight: bold; "
            "border: none; font-size: 10px; } QPushButton:hover { background: #660000; }"
        )
        btn.clicked.connect(self._on_delete)
        self._table.setCellWidget(row, 3, btn)

    def _fill_empty_row(self, row):
        """Empty row: editable start/end node cells."""
        # Empty label
        lbl = QTableWidgetItem("")
        lbl.setFlags(Qt.ItemFlag.NoItemFlags)
        lbl.setForeground(QColor("#223344"))
        self._table.setItem(row, 0, lbl)

        # Editable start/end node cells
        for col in (1, 2):
            item = QTableWidgetItem("")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setForeground(QColor("#334455"))
            self._table.setItem(row, col, item)

        # No delete button
        empty = QTableWidgetItem("")
        empty.setFlags(Qt.ItemFlag.NoItemFlags)
        self._table.setItem(row, 3, empty)

    # ── Events ────────────────────────────────────

    def _on_cell_changed(self, row: int, col: int):
        if self._suppress:
            return
        if col not in (1, 2):
            return

        members = self._doc.member_list()
        if row < len(members):
            return

        # Empty row — check if both nodes are filled
        si = self._table.item(row, 1)
        ei = self._table.item(row, 2)
        start_text = si.text().strip() if si else ""
        end_text = ei.text().strip() if ei else ""

        if start_text and end_text:
            self._create_member_from_row(start_text, end_text)

    def _find_node_by_label(self, label: str) -> str | None:
        for nid, n in self._doc.nodes.items():
            if n.label.upper() == label.upper():
                return nid
        return None

    def _create_member_from_row(self, start_label: str, end_label: str):
        """Create member from typed node labels in empty row."""
        sn_id = self._find_node_by_label(start_label)
        en_id = self._find_node_by_label(end_label)
        if not sn_id or not en_id:
            return
        try:
            self._doc.add_member(sn_id, en_id)
            self.member_changed.emit()
            self.refresh()
        except ValueError:
            pass

    def _on_delete(self):
        """Find sender button row, delete member, remove row."""
        btn = self.sender()
        if btn is None:
            return
        for row in range(self._table.rowCount()):
            if self._table.cellWidget(row, 3) is btn:
                item = self._table.item(row, 0)
                if item is None:
                    continue
                member_id = item.data(Qt.ItemDataRole.UserRole)
                if member_id:
                    self._doc.delete_entity(member_id)
                    self.member_changed.emit()
                    self._suppress = True
                    self._table.removeRow(row)
                    self._suppress = False
                break
