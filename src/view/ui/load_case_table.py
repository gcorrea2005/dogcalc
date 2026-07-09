"""Load Case Editor — STAAD-style spreadsheet for load cases."""

from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QComboBox, QPushButton, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

EMPTY_ROWS = 2
LOAD_TYPES = ["dead", "live", "roof_live", "wind", "seismic", "snow", "granizo", "other"]

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
COLUMNS = ["#", "Name", "Type", "Self-W", ""]
COL_WIDTHS = [30, 120, 80, 55, 32]


class LoadCaseTable(QDockWidget):
    """STAAD-style load case editor."""

    load_cases_changed = Signal()

    def __init__(self, document, parent=None):
        super().__init__("LOAD CASE EDITOR", parent)
        self._doc = document
        self._suppress = False

        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.setMinimumWidth(320)

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

    def refresh(self):
        self._suppress = True
        cases = list(self._doc.load_cases.values())
        total = len(cases) + EMPTY_ROWS
        self._table.setRowCount(total)

        for i, lc in enumerate(cases):
            self._fill_row(i, lc)
        for i in range(len(cases), total):
            self._fill_empty_row(i)

        self._suppress = False

    def _fill_row(self, row, lc):
        # Index
        idx_item = QTableWidgetItem(str(row + 1))
        idx_item.setFlags(Qt.ItemFlag.NoItemFlags)
        idx_item.setForeground(QColor("#88CCFF"))
        idx_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self._table.setItem(row, 0, idx_item)

        # Name
        name = QTableWidgetItem(lc.name)
        name.setFlags(name.flags() & ~Qt.ItemFlag.ItemIsEditable)
        name.setData(Qt.ItemDataRole.UserRole, lc.id)
        self._table.setItem(row, 1, name)

        # Type dropdown
        combo = QComboBox()
        for lt in LOAD_TYPES:
            combo.addItem(lt, lt)
        combo.setCurrentText(lc.load_type)
        combo.setStyleSheet("QComboBox { background: #000033; color: #DDD; border: 1px solid #225; font: 11px 'Courier New'; padding: 1px 2px; }")
        combo.currentIndexChanged.connect(
            lambda idx, lid=lc.id, cb=combo: self._on_type_changed(lid, cb.itemData(idx))
        )
        self._table.setCellWidget(row, 2, combo)

        # Self-weight toggle
        sw = QPushButton("ON" if lc.include_self_weight else "OFF")
        sw.setFixedSize(44, 20)
        sw.setStyleSheet(
            f"QPushButton {{ background: {'#003300' if lc.include_self_weight else '#330000'}; "
            f"color: {'#44FF44' if lc.include_self_weight else '#FF4444'}; "
            "font-weight: bold; border: none; font-size: 10px; }"
        )
        sw.clicked.connect(lambda checked=False, lid=lc.id: self._toggle_self_weight(lid))
        self._table.setCellWidget(row, 3, sw)

        # Delete
        btn = QPushButton("X")
        btn.setFixedSize(24, 20)
        btn.setStyleSheet("QPushButton { background: #330000; color: #FF4444; font-weight: bold; border: none; font-size: 10px; } QPushButton:hover { background: #660000; }")
        btn.clicked.connect(self._on_delete)
        self._table.setCellWidget(row, 4, btn)

    def _fill_empty_row(self, row):
        empty = QTableWidgetItem("")
        empty.setFlags(Qt.ItemFlag.NoItemFlags)
        self._table.setItem(row, 0, empty)
        for col in range(1, 5):
            e = QTableWidgetItem("")
            e.setFlags(Qt.ItemFlag.NoItemFlags)
            self._table.setItem(row, col, e)

    def _on_type_changed(self, lc_id, new_type):
        if lc_id in self._doc.load_cases and new_type:
            self._doc.load_cases[lc_id].load_type = new_type
            self.load_cases_changed.emit()

    def _toggle_self_weight(self, lc_id):
        if lc_id in self._doc.load_cases:
            lc = self._doc.load_cases[lc_id]
            lc.include_self_weight = not lc.include_self_weight
            self.load_cases_changed.emit()
            self.refresh()

    def _on_delete(self):
        btn = self.sender()
        if btn is None:
            return
        for row in range(self._table.rowCount()):
            if self._table.cellWidget(row, 4) is btn:
                item = self._table.item(row, 1)
                if item:
                    lc_id = item.data(Qt.ItemDataRole.UserRole)
                    if lc_id and lc_id in self._doc.load_cases:
                        del self._doc.load_cases[lc_id]
                        self.load_cases_changed.emit()
                        self.refresh()
                break
