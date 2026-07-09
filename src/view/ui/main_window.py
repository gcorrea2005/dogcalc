"""MainWindow — DogCalC application shell (QGraphicsView-based 3D viewport).

Layout:
  ┌──────────────────────────────────────────┐
  │  Menu Bar: File | Edit | View | Analysis │
  ├──────────────────────────────────────────┤
  │                    │                     │
  │    StructView      │   Screen Menu       │
  │   (QGraphicsView)  │                     │
  │                    │                     │
  ├──────────────────────────────────────────┤
  │  Status: Nodes: 0 | Members: 0           │
  ├──────────────────────────────────────────┤
  │  Command: _                              │
  └──────────────────────────────────────────┘
"""

from PySide6.QtWidgets import (QMainWindow, QStatusBar, QLabel, QMenuBar, QMenu,
    QDockWidget, QFileDialog)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence

from src.view.struct_view import StructView
from src.view.ui.screen_menu import ScreenMenu
from src.view.ui.command_line import CommandLine
from src.view.ui.node_table import NodeTable
from src.view.ui.member_table import MemberTable
from src.view.ui.support_table import SupportTable
from src.view.ui.load_case_table import LoadCaseTable
from src.view.ui.combo_table import ComboTable
from src.view.ui.results_viewer import ResultsViewer
from src.view.ui.std_editor import StdEditor
from src.model.document import Document
from src.controller.tool_manager import ToolManager
from src.controller.tools.orbit_tool import OrbitTool
from src.controller.tools.node_tool import NodeTool
from src.controller.tools.member_tool import MemberTool
from src.controller.tools.select_tool import SelectTool
from src.controller.tools.delete_tool import DeleteTool
from src.engine.solver import run_analysis_for_document


CLR_MENU_BG    = "#000022"
CLR_MENU_TEXT  = "#FFFFFF"
CLR_MENU_SEL   = "#003388"
CLR_STATUS_BG  = "#000022"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DogCalC — Structural Analysis")
        self.resize(1400, 900)
        self.raise_()
        self.activateWindow()

        self._document = Document()
        self._filename = None

        self._view = StructView(self._document)
        self.setCentralWidget(self._view)

        self._setup_status_bar()
        self._setup_menus()
        self._setup_screen_menu()
        self._setup_command_line()
        self._apply_theme()
        self._init_tools()

        self._view._status_callback = self._update_status
        self._view.setFocus()

        self._setup_tables()

    def _setup_tables(self):
        """Create CRUD table docks (hidden by default, only STD editor visible)."""
        self._node_table = NodeTable(self._document)
        self._node_table.node_changed.connect(self._on_table_changed)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._node_table)
        self._node_table.setMinimumWidth(360)
        self._node_table.hide()

        self._member_table = MemberTable(self._document)
        self._member_table.member_changed.connect(self._on_table_changed)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._member_table)
        self._member_table.setMinimumWidth(420)
        self._member_table.hide()

        self._support_table = SupportTable(self._document)
        self._support_table.supports_changed.connect(self._on_table_changed)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._support_table)
        self._support_table.setMinimumWidth(220)
        self._support_table.hide()

        self._load_case_table = LoadCaseTable(self._document)
        self._load_case_table.load_cases_changed.connect(self._on_table_changed)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._load_case_table)
        self._load_case_table.setMinimumWidth(320)
        self._load_case_table.hide()

        self._combo_table = ComboTable(self._document)
        self._combo_table.combos_changed.connect(self._on_table_changed)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._combo_table)
        self._combo_table.setMinimumWidth(420)
        self._combo_table.hide()

        self._results_viewer = ResultsViewer()
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._results_viewer)
        self._results_viewer.hide()

        self._std_editor = StdEditor(self._document)
        self._std_editor.model_loaded.connect(self._on_std_loaded)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self._std_editor)
        self._std_editor.setMinimumWidth(420)
        # STD editor visible by default

    def _on_table_changed(self):
        self._view.refresh_view()
        self._update_status("Edited")
        # Regenerate .std text from current document
        from src.io.staad_file import build_std_text
        self._std_editor.set_text(build_std_text(self._document))

    def toggle_node_table(self):
        if self._node_table.isVisible():
            self._node_table.hide()
        else:
            self._node_table.refresh()
            self._node_table.show()

    def toggle_member_table(self):
        if self._member_table.isVisible():
            self._member_table.hide()
        else:
            self._member_table.refresh()
            self._member_table.show()

    def toggle_support_table(self):
        if self._support_table.isVisible():
            self._support_table.hide()
        else:
            self._support_table.refresh()
            self._support_table.show()

    def toggle_load_case_table(self):
        if self._load_case_table.isVisible():
            self._load_case_table.hide()
        else:
            self._load_case_table.refresh()
            self._load_case_table.show()

    def toggle_combo_table(self):
        if self._combo_table.isVisible():
            self._combo_table.hide()
        else:
            self._combo_table.refresh()
            self._combo_table.show()

    def toggle_results_viewer(self):
        if self._results_viewer.isVisible():
            self._results_viewer.hide()
        else:
            self._results_viewer.show()

    def toggle_std_editor(self):
        if self._std_editor.isVisible():
            self._std_editor.hide()
        else:
            self._std_editor.show()

    def _on_std_loaded(self, new_doc):
        self._document = new_doc
        self._view.document = new_doc
        self._view.analysis_result = None
        self._node_table._doc = new_doc
        self._node_table.refresh()
        self._member_table._doc = new_doc
        self._member_table.refresh()
        self._support_table._doc = new_doc
        self._support_table.refresh()
        self._load_case_table._doc = new_doc
        self._load_case_table.refresh()
        self._combo_table._doc = new_doc
        self._combo_table.refresh()
        self._view.refresh_view()
        self._view.fit_to_model()
        self._update_status(f"STD: {new_doc.node_count}N {new_doc.member_count}M")

    def _init_tools(self):
        v, d = self._view, self._document
        self._tool_manager = ToolManager(v, d)
        self._tool_manager.register_tool("orbit", OrbitTool(v, d))
        self._tool_manager.register_tool("select", SelectTool(v, d))
        self._tool_manager.register_tool("node", NodeTool(v, d))
        self._tool_manager.register_tool("member", MemberTool(v, d))
        self._tool_manager.register_tool("delete", DeleteTool(v, d))
        v.tool_manager = self._tool_manager
        v._status_callback = self._update_status
        self._tool_manager.activate_tool("orbit")

    def _activate_tool(self, name: str):
        if name in self._tool_manager.tools:
            self._tool_manager.activate_tool(name)

    def _setup_menus(self):
        mb = self.menuBar()
        m = mb.addMenu("FILE")
        m.addAction("New", self._on_new, QKeySequence.StandardKey.New)
        m.addAction("Open", self._on_open, QKeySequence.StandardKey.Open)
        m.addAction("Save", self._on_save, QKeySequence.StandardKey.Save)
        m.addSeparator()
        m.addAction("Open STD...", self._on_open_std)
        m.addAction("Save STD...", self._on_save_std)
        m.addSeparator()
        m.addAction("Quit", self.close, "Ctrl+Q")

        m = mb.addMenu("VIEW")
        m.addAction("Reset View", lambda: setattr(self._view, '_target', __import__('numpy').array([0.,0.,0.])) or setattr(self._view, '_radius', 20.0) or self._view.refresh_view(), "R")
        m.addAction("Fit Model", self._view.fit_to_model, "F")

        m = mb.addMenu("ANALYSIS")
        m.addAction("Run Analysis", self._run_analysis, "F5")
        act = m.addAction("Show Deformed", self._toggle_deformed, "F6")
        act.setCheckable(True)

    def keyPressEvent(self, event):
        key = event.key()
        if key == Qt.Key.Key_Escape:      self._activate_tool("orbit")
        elif key == Qt.Key.Key_N and not event.modifiers(): self._activate_tool("node")
        elif key == Qt.Key.Key_M and not event.modifiers(): self._activate_tool("member")
        elif key == Qt.Key.Key_S and not event.modifiers(): self._activate_tool("select")
        elif key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace): self._activate_tool("delete")
        elif key == Qt.Key.Key_F5:        self._run_analysis()
        else: super().keyPressEvent(event)

    def _setup_status_bar(self):
        self._status_label = QLabel("Ready | Nodes: 0 | Members: 0")
        self._status_label.setStyleSheet("color: white; font: 12px 'Courier New'; padding: 0 8px;")
        sb = QStatusBar()
        sb.addWidget(self._status_label)
        self.setStatusBar(sb)

    def _update_status(self, message: str):
        d = self._document
        self._status_label.setText(f"{message} | Nodes: {d.node_count} | Members: {d.member_count}")

    def _echo(self, msg: str):
        self._update_status(msg)

    def _setup_screen_menu(self):
        dock = QDockWidget("SCREEN MENU", self)
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self._screen_menu = ScreenMenu(self)
        dock.setWidget(self._screen_menu)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    def _setup_command_line(self):
        dock = QDockWidget("Command", self)
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self._cmd = CommandLine()
        dock.setWidget(self._cmd)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        self._cmd.command_entered.connect(self._parse_command)

    def _parse_command(self, text: str):
        parts = text.strip().split()
        if not parts: return
        cmd = parts[0].upper()
        try:
            if cmd == "NODE":
                x, y, z = [float(c.strip()) for c in text[4:].split(",")]
                self._document.add_node(x, y, z)
                self._view.refresh_view()
                self._echo(f"Node at ({x:.0f},{y:.0f},{z:.0f})")
            elif cmd == "MEMBER":
                n1, n2 = [int(i.strip()) - 1 for i in text[6:].split(",")]
                ids = list(self._document.nodes.keys())
                m = self._document.add_member(ids[n1], ids[n2])
                self._view.refresh_view()
                self._echo(f"Member {m.label}")
            elif cmd == "SUPPORT":
                n = int(parts[1]) - 1; stype = parts[2].upper()
                from src.model.entities.node import SupportType
                ids = list(self._document.nodes.keys())
                self._document.nodes[ids[n]].support_type = SupportType[stype]
                self._view.refresh_view()
                self._echo(f"Node {n+1}: {stype}")
            elif cmd == "ANALYZE": self._run_analysis()
            elif cmd in ("Q", "QUIT", "EXIT"): self.close()
            else: self.execute_screen_action(cmd.lower())
        except Exception as e: self._echo(f"Error: {e}")

    def execute_screen_action(self, action: str):
        if action.startswith("menu_"): return
        if action == "save":      self._on_save()
        elif action == "open":    self._on_open()
        elif action == "open_std": self._on_open_std()
        elif action == "save_std": self._on_save_std()
        elif action == "export":  self._on_export()
        elif action == "quit":    self.close()
        elif action == "select":  self._activate_tool("select")
        elif action == "node":    self._activate_tool("node")
        elif action == "member":  self._activate_tool("member")
        elif action == "delete":  self._activate_tool("delete")
        elif action == "analyze": self._run_analysis()
        elif action == "toggle_deformed":
            self._view.show_deformed = not self._view.show_deformed
            self._view.refresh_view()
        elif action == "scale_up":
            self._view.deformed_scale *= 1.5; self._view.refresh_view()
        elif action == "scale_down":
            self._view.deformed_scale /= 1.5; self._view.refresh_view()
        elif action == "show_displacements":
            r = self._view.analysis_result
            if r and r.success:
                self._echo(f"Max disp: {r.max_displacement()*1000:.2f} mm")
            else: self._echo("No results")
        elif action == "node_table":
            self.toggle_node_table()
        elif action == "member_table":
            self.toggle_member_table()
        elif action == "support_table":
            self.toggle_support_table()
        elif action == "load_case_table":
            self.toggle_load_case_table()
        elif action == "combo_table":
            self.toggle_combo_table()
        elif action == "results_viewer":
            self.toggle_results_viewer()
        elif action == "std_editor":
            self.toggle_std_editor()
        else: self._echo(f"Unknown: {action}")

    def _run_analysis(self):
        if self._document.member_count == 0:
            self._echo("No members"); return
        self._echo("Running...")
        try:
            result = run_analysis_for_document(self._document)
            if result.success:
                self._view.analysis_result = result
                self._results_viewer.set_results(self._document, result)
                self._results_viewer.show()
                self._results_viewer.raise_()
                self._echo(f"OK | Max disp: {result.max_displacement()*1000:.2f} mm")
            else:
                self._echo(f"Failed: {result.errors[0] if result.errors else '?'}")
        except Exception as e: self._echo(f"Error: {e}")

    def _toggle_deformed(self):
        self._view.show_deformed = not self._view.show_deformed
        self._view.refresh_view()

    def _on_new(self):
        self._document = Document()
        self._view.document = self._document
        self._view.analysis_result = None
        self._view.refresh_view()
        self._echo("New project")

    def _on_open(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open", "", "DogCalC (*.dogcalc)")
        if path:
            from src.io.project_file import load_document
            self._document = load_document(path)
            self._view.document = self._document
            self._view.analysis_result = None
            self._view.refresh_view()
            self._view.fit_to_model()
            self._echo(f"Loaded: {path}")

    def _on_save(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save", self._filename or "", "DogCalC (*.dogcalc)")
        if path:
            from src.io.project_file import save_document
            save_document(self._document, path)
            self._filename = path
            self._echo(f"Saved: {path}")

    def _on_open_std(self):
        path, _ = QFileDialog.getOpenFileName(self, "Open STAAD", "", "STAAD (*.std);;All (*.*)")
        if path:
            from src.io.staad_file import parse_std
            self._document = parse_std(path)
            self._view.document = self._document
            self._view.analysis_result = None
            self._view.refresh_view()
            self._view.fit_to_model()
            self._echo(f"STD: {path} ({self._document.node_count}N {self._document.member_count}M)")
            self._std_editor.load_file(path)

    def _on_save_std(self):
        path, _ = QFileDialog.getSaveFileName(self, "Save STAAD", "model.std", "STAAD (*.std)")
        if path:
            from src.io.staad_file import write_std
            write_std(self._document, path)
            self._echo(f"STD saved: {path}")

    def _on_export(self):
        r = self._view.analysis_result
        if not r or not r.success:
            self._echo("No results"); return
        path, _ = QFileDialog.getSaveFileName(self, "Export", "results.xlsx", "Excel (*.xlsx)")
        if path:
            from src.io.export import export_results_to_excel
            export_results_to_excel(self._document, r, path)
            self._echo(f"Exported: {path}")

    def _apply_theme(self):
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {CLR_MENU_BG}; }}
            QMenuBar {{ background-color: {CLR_MENU_BG}; color: {CLR_MENU_TEXT}; border-bottom: 1px solid #1a1a2e; }}
            QMenuBar::item:selected {{ background-color: {CLR_MENU_SEL}; }}
            QMenu {{ background-color: {CLR_MENU_BG}; color: {CLR_MENU_TEXT}; border: 1px solid #1a1a2e; }}
            QMenu::item:selected {{ background-color: {CLR_MENU_SEL}; }}
            QStatusBar {{ background-color: {CLR_STATUS_BG}; color: white; font: 12px 'Courier New'; border-top: 1px solid #1a1a2e; }}
        """)
