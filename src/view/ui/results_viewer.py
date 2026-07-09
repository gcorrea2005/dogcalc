"""Results Viewer — STAAD-style tabbed analysis output."""

from PySide6.QtWidgets import (
    QDockWidget, QWidget, QVBoxLayout, QTabWidget, QTableWidget,
    QTableWidgetItem, QPushButton, QHBoxLayout, QFileDialog, QAbstractItemView,
    QComboBox, QLabel
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from src.engine.results import AnalysisResult

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


class ResultsViewer(QDockWidget):
    """Tabbed analysis results: Displacements, Reactions, Forces."""

    def __init__(self, parent=None):
        super().__init__("RESULTS", parent)
        self._doc = None
        self._result = None

        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable |
            QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.setMinimumWidth(500)

        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)

        self._tabs = QTabWidget()
        self._tabs.setStyleSheet("QTabWidget::pane { border: 1px solid #112244; } "
                                 "QTabBar::tab { background: #001133; color: #88AAFF; padding: 3px 8px; } "
                                 "QTabBar::tab:selected { background: #002255; color: #FFF; }")

        self._disp_table = self._make_table(["Node", "DX mm", "DY mm", "DZ mm", "Result mm"])
        self._react_table = self._make_table(["Node", "FX kN", "FY kN", "FZ kN", "MX kN-m", "MY kN-m", "MZ kN-m"])
        self._force_table = self._make_table(["Member", "Axial kN", "Shear Y kN", "Shear Z kN", "Moment Y kN-m", "Moment Z kN-m"])
        self._code_table = self._make_table(["Member", "Section", "Axial kN", "φPn kN", "Ratio", "Status"])

        self._tabs.addTab(self._disp_table, " Displacements ")
        self._tabs.addTab(self._react_table, " Reactions ")
        self._tabs.addTab(self._force_table, " Forces ")
        self._tabs.addTab(self._code_table, " Code Check ")
        layout.addWidget(self._tabs)

        # Combo selector
        filter_row = QHBoxLayout()
        filter_row.addWidget(QLabel(" Combo: "))
        self._combo_selector = QComboBox()
        self._combo_selector.setStyleSheet("QComboBox { background: #000033; color: #DDD; border: 1px solid #225; font: 11px 'Courier New'; padding: 2px 4px; }")
        self._combo_selector.currentIndexChanged.connect(self._on_combo_changed)
        filter_row.addWidget(self._combo_selector)
        filter_row.addStretch()
        layout.addLayout(filter_row)

        btns = QHBoxLayout()
        export_btn = QPushButton(" Export Excel ")
        export_btn.setStyleSheet("QPushButton { background: #002244; color: #88BBFF; font-weight: bold; padding: 4px 12px; } QPushButton:hover { background: #003366; }")
        export_btn.clicked.connect(self._export)
        btns.addStretch()
        btns.addWidget(export_btn)
        layout.addLayout(btns)

        self.setWidget(body)

    def _make_table(self, headers):
        t = QTableWidget(0, len(headers))
        t.setHorizontalHeaderLabels(headers)
        t.setStyleSheet(TABLE_STYLE)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.verticalHeader().setVisible(False)
        t.horizontalHeader().setStretchLastSection(True)
        return t

    def set_results(self, doc, result: AnalysisResult):
        self._doc = doc
        self._result = result
        if not result or not result.success:
            self._disp_table.setRowCount(1)
            self._disp_table.setItem(0, 0, QTableWidgetItem("No results"))
            return
        # Populate combo selector
        self._combo_selector.blockSignals(True)
        self._combo_selector.clear()
        combos = list(result.combo_results.keys()) if result.combo_results else [result.load_case_name]
        for c in combos:
            # Show friendly name for load cases
            label = c
            if doc:
                lc = doc.load_cases.get(c)
                if lc:
                    label = f"{lc.load_type.upper()} ({lc.name.split()[0]})"
            self._combo_selector.addItem(label, c)
        # Add envelope option
        env_names = [e.name for e in (doc.envelopes.values() if doc else [])]
        for en in env_names:
            self._combo_selector.addItem(f"ENV: {en}", f"__env__{en}")
        self._combo_selector.blockSignals(False)
        self._refresh_tabs()

    def _refresh_tabs(self):
        self._fill_displacements()
        self._fill_reactions()
        self._fill_forces()
        self._fill_code_check()

    def _on_combo_changed(self):
        self._refresh_tabs()

    def _get_active_result(self) -> dict | None:
        """Get node/member results for the currently selected combo."""
        if not self._result or not self._result.combo_results:
            return None
        selected = self._combo_selector.currentData()
        if selected and str(selected).startswith("__env__"):
            return None  # envelope: use default primary results
        return self._result.combo_results.get(selected)

    def _fill_displacements(self):
        nr_data = self._get_active_result()
        results = nr_data['node_results'] if nr_data else self._result.node_results if self._result else {}
        items = []
        for nid, nr in results.items():
            node = self._doc.nodes.get(nid) if self._doc else None
            label = node.label if node else nid[:8]
            res = (nr.dx**2 + nr.dy**2 + nr.dz**2)**0.5
            items.append((label, nr.dx*1000, nr.dy*1000, nr.dz*1000, res*1000))
        items.sort(key=lambda x: abs(x[4]), reverse=True)
        self._fill_table(self._disp_table, items)

    def _fill_reactions(self):
        nr_data = self._get_active_result()
        results = nr_data['node_results'] if nr_data else self._result.node_results if self._result else {}
        items = []
        for nid, nr in results.items():
            if all(abs(v) < 1e-6 for v in (nr.rxn_fx, nr.rxn_fy, nr.rxn_fz, nr.rxn_mx, nr.rxn_my, nr.rxn_mz)):
                continue
            node = self._doc.nodes.get(nid) if self._doc else None
            label = node.label if node else nid[:8]
            items.append((label, nr.rxn_fx, nr.rxn_fy, nr.rxn_fz,
                          nr.rxn_mx, nr.rxn_my, nr.rxn_mz))
        self._fill_table(self._react_table, items)

    def _fill_forces(self):
        nr_data = self._get_active_result()
        results = nr_data['member_results'] if nr_data else self._result.member_results if self._result else {}
        items = []
        for mid, mr in results.items():
            member = self._doc.members.get(mid) if self._doc else None
            label = member.label if member else mid[:8]
            # Get max forces from segments
            # Get max absolute axial and its sign
            axials = [s.get('axial', 0) for s in mr.segments] if mr.segments else [0]
            max_abs = max(abs(a) for a in axials)
            # Find the actual value (preserve sign)
            max_axial = next((a for a in axials if abs(a) == max_abs), max_abs)
            max_sy = max(abs(s.get('shear_y', 0)) for s in mr.segments) if mr.segments else 0
            max_sz = max(abs(s.get('shear_z', 0)) for s in mr.segments) if mr.segments else 0
            max_my = max(abs(s.get('moment_y', 0)) for s in mr.segments) if mr.segments else 0
            max_mz = max(abs(s.get('moment_z', 0)) for s in mr.segments) if mr.segments else 0
            items.append((label, max_axial, max_sy, max_sz, max_my, max_mz))
        items.sort(key=lambda x: abs(x[1]), reverse=True)
        self._fill_table(self._force_table, items)

    def _fill_table(self, table, items):
        self._fill_table_offset(table, items, offset=0)

    def _fill_table_offset(self, table, items, offset=0):
        table.setRowCount(len(items) + offset)
        for row, vals in enumerate(items):
            for col, val in enumerate(vals):
                if isinstance(val, float):
                    text = f"{val:.2f}"
                else:
                    text = str(val)
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if col == 0:
                    item.setForeground(QColor("#88CCFF"))
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                table.setItem(row, col, item)

    def _fill_code_check(self):
        """Compute and display code check results per NSR-10 / AISC 360-10."""
        if not self._doc or not self._result or not self._doc.envelopes:
            self._code_table.setRowCount(1)
            self._code_table.setItem(0, 0, QTableWidgetItem("No envelope — add DEFINE ENVELOPE"))
            return
        from src.engine.code_check import check_all_members
        env = list(self._doc.envelopes.values())[0]
        if not env.max_axial:
            self._code_table.setRowCount(1)
            self._code_table.setItem(0, 0, QTableWidgetItem("Run analysis first (F5)"))
            return
        results = check_all_members(self._doc, env)
        over = [r for r in results if r.status == 'OVERSTRESS']
        ok = len(results) - len(over)
        worst = results[0] if results else None
        # Summary row at top
        summary = f"Total: {len(results)} | OK: {ok} | OVERSTRESS: {len(over)}"
        if worst:
            summary += f" | Worst: {worst.label} ratio={worst.ratio:.2f}"
        self._code_table.setRowCount(len(results) + 1)
        # Summary
        s_item = QTableWidgetItem(summary)
        s_item.setForeground(QColor("#FFCC44"))
        s_item.setFlags(Qt.ItemFlag.NoItemFlags)
        self._code_table.setItem(0, 0, s_item)
        self._code_table.setSpan(0, 0, 1, 6)
        items = []
        for r in results:
            items.append((r.label, r.section, f"{r.axial_demand:.1f}",
                          f"{r.axial_capacity:.1f}", f"{r.ratio:.3f}", r.status))
        self._fill_table_offset(self._code_table, items, offset=1)
        # Color the status column
        for row, r in enumerate(results):
            item = self._code_table.item(row + 1, 5)  # +1 for summary row
            if item:
                if r.status == "OK":
                    item.setForeground(QColor("#44FF44"))
                else:
                    item.setForeground(QColor("#FF4444"))

    def _export(self):
        if not self._result or not self._result.success:
            return
        from src.io.export import export_results_to_excel
        path, _ = QFileDialog.getSaveFileName(self, "Export Results", "resultados.xlsx", "Excel (*.xlsx)")
        if path:
            export_results_to_excel(self._doc, self._result, path)
