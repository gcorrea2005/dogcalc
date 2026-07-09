"""Load Combination Editor — STAAD-style read-only spreadsheet."""

from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QPushButton, QAbstractItemView
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

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
COLUMNS = ["#", "Name", "Factors", ""]
COL_WIDTHS = [40, 160, 180, 32]


class ComboTable(QDockWidget):
    """Read-only load combination viewer."""

    combos_changed = Signal()

    def __init__(self, document, parent=None):
        super().__init__("COMBO EDITOR", parent)
        self._doc = document
        self._suppress = False

        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.setMinimumWidth(420)

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)

        self._table = QTableWidget(0, len(COLUMNS))
        self._table.setHorizontalHeaderLabels(COLUMNS)
        self._table.setStyleSheet(TABLE_STYLE)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
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
        combos = list(self._doc.load_combinations.values())
        self._table.setRowCount(len(combos))

        for row, combo in enumerate(combos):
            # Index
            idx = QTableWidgetItem(str(combo.id))
            idx.setFlags(Qt.ItemFlag.NoItemFlags)
            idx.setForeground(QColor("#88CCFF"))
            idx.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self._table.setItem(row, 0, idx)

            # Name
            name = QTableWidgetItem(combo.name)
            name.setFlags(Qt.ItemFlag.NoItemFlags)
            self._table.setItem(row, 1, name)

            # Factors text (e.g., "1.2D + 1.6Lr + 0.5W")
            parts = []
            for lc_id, factor in combo.factors.items():
                lc = self._doc.load_cases.get(lc_id)
                lc_label = lc.load_type.upper() if lc else lc_id[:6]
                parts.append(f"{factor:.1f}{lc_label}")
            factors_text = " + ".join(parts)
            ft = QTableWidgetItem(factors_text)
            ft.setFlags(Qt.ItemFlag.NoItemFlags)
            ft.setForeground(QColor("#FFCC44"))
            self._table.setItem(row, 2, ft)

            # Delete
            btn = QPushButton("X")
            btn.setFixedSize(24, 20)
            btn.setStyleSheet("QPushButton { background: #330000; color: #FF4444; font-weight: bold; border: none; font-size: 10px; } QPushButton:hover { background: #660000; }")
            btn.clicked.connect(self._on_delete)
            self._table.setCellWidget(row, 3, btn)

    def _on_delete(self):
        btn = self.sender()
        if btn is None:
            return
        for row in range(self._table.rowCount()):
            if self._table.cellWidget(row, 3) is btn:
                combo_id = self._table.item(row, 0).text()
                if combo_id in self._doc.load_combinations:
                    del self._doc.load_combinations[combo_id]
                    self.combos_changed.emit()
                    self.refresh()
                break
