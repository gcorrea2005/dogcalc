"""Material Editor — STAAD-style spreadsheet for material properties."""

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
COLUMNS = ["Name", "E (GPa)", "ν", "ρ (kg/m³)", "Fy (MPa)", "Fu (MPa)", ""]
COL_WIDTHS = [90, 80, 50, 70, 80, 80, 32]


class MaterialTable(QDockWidget):
    """STAAD-style material property editor."""

    materials_changed = Signal()

    def __init__(self, document, parent=None):
        super().__init__("MATERIAL EDITOR", parent)
        self._doc = document
        self._suppress = False

        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.setMinimumWidth(470)

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

    def refresh(self):
        self._suppress = True
        mats = list(self._doc.materials.values())
        self._table.setRowCount(len(mats))

        for row, mat in enumerate(mats):
            # Name (read-only)
            name = QTableWidgetItem(mat.name)
            name.setFlags(name.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name.setForeground(QColor("#88CCFF"))
            name.setData(Qt.ItemDataRole.UserRole, mat.id)
            self._table.setItem(row, 0, name)

            # E (GPa) — convert from Pa
            e_item = QTableWidgetItem(f"{mat.elastic_modulus / 1e9:.1f}")
            e_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 1, e_item)

            # ν
            nu_item = QTableWidgetItem(f"{mat.poisson_ratio:.2f}")
            nu_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 2, nu_item)

            # ρ
            rho_item = QTableWidgetItem(f"{mat.density:.0f}")
            rho_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 3, rho_item)

            # Fy (MPa) — convert from Pa
            fy_item = QTableWidgetItem(f"{mat.yield_strength / 1e6:.0f}")
            fy_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 4, fy_item)

            # Fu (MPa)
            fu_item = QTableWidgetItem(f"{mat.ultimate_strength / 1e6:.0f}")
            fu_item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            self._table.setItem(row, 5, fu_item)

            # Delete
            btn = QPushButton("X")
            btn.setFixedSize(24, 20)
            btn.setStyleSheet("QPushButton { background: #330000; color: #FF4444; font-weight: bold; border: none; font-size: 10px; } QPushButton:hover { background: #660000; }")
            btn.clicked.connect(self._on_delete)
            self._table.setCellWidget(row, 6, btn)

        self._suppress = False

    def _on_cell_changed(self, row: int, col: int):
        if self._suppress or col == 0:
            return
        item = self._table.item(row, col)
        name_item = self._table.item(row, 0)
        if item is None or name_item is None:
            return
        mat_id = name_item.data(Qt.ItemDataRole.UserRole)
        if mat_id not in self._doc.materials:
            return
        mat = self._doc.materials[mat_id]
        text = item.text().strip()
        try:
            val = float(text)
            if col == 1: mat.elastic_modulus = val * 1e9    # GPa → Pa
            elif col == 2: mat.poisson_ratio = val
            elif col == 3: mat.density = val
            elif col == 4: mat.yield_strength = val * 1e6     # MPa → Pa
            elif col == 5: mat.ultimate_strength = val * 1e6  # MPa → Pa
            self.materials_changed.emit()
        except ValueError:
            self._suppress = True
            # Restore original value
            values = {
                1: mat.elastic_modulus / 1e9, 2: mat.poisson_ratio, 3: mat.density,
                4: mat.yield_strength / 1e6, 5: mat.ultimate_strength / 1e6
            }
            item.setText(f"{values[col]:.1f}")
            self._suppress = False

    def _on_delete(self):
        btn = self.sender()
        if btn is None:
            return
        for row in range(self._table.rowCount()):
            if self._table.cellWidget(row, 6) is btn:
                item = self._table.item(row, 0)
                if item:
                    mat_id = item.data(Qt.ItemDataRole.UserRole)
                    if mat_id and mat_id in self._doc.materials:
                        del self._doc.materials[mat_id]
                        self.materials_changed.emit()
                        self.refresh()
                break
