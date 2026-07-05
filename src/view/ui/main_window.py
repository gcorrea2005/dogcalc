"""MainWindow — DogCalC application shell with viewport, tools, and status bar.

Layout:
  ┌──────────────────────────────────────────┐
  │  Menu Bar: File | Edit | View | Analysis │
  ├──────────────────────────────────────────┤
  │                    │                     │
  │    StructView      │   Screen Menu       │
  │   (QOpenGLWidget)  │   (Task 7)          │
  │                    │                     │
  ├──────────────────────────────────────────┤
  │  Status: Nodes: 3 | Members: 2 | Orbit   │
  ├──────────────────────────────────────────┤
  │  Command: _                              │
  └──────────────────────────────────────────┘
"""

from PySide6.QtWidgets import (QMainWindow, QStatusBar, QLabel, QMenuBar, QMenu,
    QDockWidget)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence

from src.view.struct_view import StructView
from src.view.camera import OrbitCamera
from src.view.ui.screen_menu import ScreenMenu
from src.view.ui.command_line import CommandLine
from src.model.document import Document
from src.controller.tool_manager import ToolManager
from src.controller.tools.orbit_tool import OrbitTool
from src.controller.tools.node_tool import NodeTool
from src.controller.tools.member_tool import MemberTool
from src.controller.tools.select_tool import SelectTool
from src.controller.tools.delete_tool import DeleteTool
from src.engine.solver import run_analysis_for_document


# ── Color palette (inherited from cad2d-lite) ──
CLR_BG         = "#000000"
CLR_MENU_BG    = "#000022"
CLR_MENU_TEXT  = "#FFFFFF"
CLR_MENU_SEL   = "#003388"
CLR_STATUS_BG  = "#000022"
CLR_SCREEN_BG  = "#0000AA"
CLR_HEADER     = "#44AAFF"


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("DogCalC — Structural Analysis")
        self.resize(1400, 900)
        self.raise_()
        self.activateWindow()

        # ── Document (single source of truth) ──
        self._document = Document()
        self._filename = None

        # ── Viewport ──
        self._view = StructView(self._document)
        self.setCentralWidget(self._view)

        # ── UI chrome (must come before tools — tools reference status bar) ──
        self._setup_status_bar()
        self._setup_menus()
        self._setup_screen_menu()
        self._setup_command_line()
        self._apply_theme()

        # ── Tool system (references status bar via _status_callback) ──
        self._init_tools()

        # Bridge callbacks
        self._view._status_callback = self._update_status
        self._view._on_mouse_move = self._update_coord_status

        # Keyboard focus
        self._view.setFocus()

    # ── Tools ─────────────────────────────────────────

    def _init_tools(self):
        v, d = self._view, self._document
        self._tool_manager = ToolManager(v, d)

        # Register all tools
        self._tool_manager.register_tool("orbit", OrbitTool(v, d))
        self._tool_manager.register_tool("select", SelectTool(v, d))
        self._tool_manager.register_tool("node", NodeTool(v, d))
        self._tool_manager.register_tool("member", MemberTool(v, d))
        self._tool_manager.register_tool("delete", DeleteTool(v, d))

        # Wire viewport → tool_manager
        v.tool_manager = self._tool_manager
        v._status_callback = self._update_status

        # Default: orbit
        self._tool_manager.activate_tool("orbit")

    def _activate_tool(self, name: str):
        """Activate a tool by name. Called by menus, hotkeys, screen menu."""
        if name in self._tool_manager.tools:
            self._tool_manager.activate_tool(name)
            self._update_status(self._tool_manager.active_tool_name or "")

    # ── Menus ────────────────────────────────────────

    def _setup_menus(self):
        mb = self.menuBar()

        # File
        m = mb.addMenu("FILE")
        m.addAction("New", self._on_new, QKeySequence.StandardKey.New)
        m.addAction("Open", self._on_open, QKeySequence.StandardKey.Open)
        m.addAction("Save", self._on_save, QKeySequence.StandardKey.Save)
        m.addSeparator()
        m.addAction("Open STD...", self._on_open_std)
        m.addAction("Save STD...", self._on_save_std)
        m.addSeparator()
        m.addAction("Quit", self.close, "Ctrl+Q")

        # Edit
        m = mb.addMenu("EDIT")
        m.addAction("Undo", self._document.undo, "Ctrl+Z")
        m.addAction("Redo", self._document.redo, "Ctrl+Y")
        m.addSeparator()
        act = m.addAction("Delete", lambda: self._activate_tool("delete"), QKeySequence.StandardKey.Delete)
        m.addAction("Select All", self._on_select_all)

        # View
        m = mb.addMenu("VIEW")
        m.addAction("Zoom Extents", self._view.zoom_extents, "F")
        m.addAction("Zoom In", self._view.zoom_in, "Ctrl+=")
        m.addAction("Zoom Out", self._view.zoom_out, "Ctrl+-")
        m.addAction("Toggle Grid", self._toggle_grid, "G")

        # Analysis
        m = mb.addMenu("ANALYSIS")
        m.addAction("Run Analysis", self._run_analysis, "F5")
        m.addSeparator()
        act = m.addAction("Show Deformed", self._toggle_deformed, "F6")
        act.setCheckable(True)

    # ── Keyboard shortcuts (global) ──────────────────

    def keyPressEvent(self, event):
        """Global hotkeys that work regardless of focus."""
        key = event.key()

        if key == Qt.Key.Key_Escape:
            self._activate_tool("orbit")
            return
        elif key == Qt.Key.Key_N and not event.modifiers():
            self._activate_tool("node")
            return
        elif key == Qt.Key.Key_M and not event.modifiers():
            self._activate_tool("member")
            return
        elif key == Qt.Key.Key_S and not event.modifiers():
            self._activate_tool("select")
            return
        elif key in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self._activate_tool("delete")
            return
        elif key == Qt.Key.Key_F5:
            self._run_analysis()
            return

        super().keyPressEvent(event)

    # ── Status bar ───────────────────────────────────

    def _setup_status_bar(self):
        self._status_label = QLabel("Ready | Nodes: 0 | Members: 0")
        self._status_label.setStyleSheet(
            "color: white; font-family: 'Courier New', monospace; font-size: 12px; padding: 0 8px;"
        )
        sb = QStatusBar()
        sb.addWidget(self._status_label)
        self.setStatusBar(sb)

    def _update_status(self, message: str):
        """Update status bar from tool callbacks."""
        d = self._document
        self._status_label.setText(
            f"{message} | Nodes: {d.node_count} | Members: {d.member_count}"
        )

    def _update_coord_status(self, scene_pos):
        """Update coordinate display in status bar."""
        # Simple impl — full coord display on status bar
        pass

    def _echo(self, msg: str):
        self._update_status(msg)

    # ── Screen Menu ─────────────────────────────────

    def _setup_screen_menu(self):
        """Create right-docked screen menu (classic AutoCAD/STAAD style)."""
        dock = QDockWidget("SCREEN MENU", self)
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self._screen_menu = ScreenMenu(self)
        dock.setWidget(self._screen_menu)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, dock)

    def _setup_command_line(self):
        """Create bottom command line (STAAD-style text input)."""
        dock = QDockWidget("Command", self)
        dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self._cmd = CommandLine()
        dock.setWidget(self._cmd)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        self._cmd.command_entered.connect(self._parse_command)

    def _parse_command(self, text: str):
        """Parse STAAD-like text commands."""
        parts = text.strip().split()
        if not parts:
            return
        cmd = parts[0].upper()
        args = parts[1:] if len(parts) > 1 else []

        try:
            if cmd == "NODE":
                # NODE x,y,z
                x, y, z = [float(c.strip()) for c in text[4:].split(",")]
                node = self._document.add_node(x, y, z)
                self._view.update()
                self._echo(f"Node {node.label} ({x:.1f}, {y:.1f}, {z:.1f})")

            elif cmd == "MEMBER":
                # MEMBER n1,n2  (1-indexed)
                n1, n2 = [int(i.strip()) - 1 for i in text[6:].split(",")]
                ids = list(self._document.nodes.keys())
                if n1 < 0 or n2 < 0 or n1 >= len(ids) or n2 >= len(ids):
                    raise ValueError(f"Node index out of range (1-{len(ids)})")
                m = self._document.add_member(ids[n1], ids[n2])
                self._view.update()
                n1l = self._document.nodes[ids[n1]].label
                n2l = self._document.nodes[ids[n2]].label
                self._echo(f"Member {m.label}: {n1l} → {n2l}")

            elif cmd == "SUPPORT":
                # SUPPORT n TYPE
                n = int(args[0]) - 1
                stype = args[1].upper()
                ids = list(self._document.nodes.keys())
                from src.model.entities.node import SupportType
                st = SupportType[stype]
                self._document.nodes[ids[n]].support_type = st
                self._view.update()
                self._echo(f"Node {n+1}: {stype}")

            elif cmd == "ANALYZE":
                self._run_analysis()

            elif cmd == "ZOOM":
                if args and args[0] == "E":
                    self._view.camera = OrbitCamera()
                    self._view.update()
                    self._echo("Zoom Extents")

            elif cmd in ("Q", "QUIT", "EXIT"):
                self.close()

            else:
                # Forward to screen action dispatcher
                self.execute_screen_action(cmd.lower())

        except Exception as e:
            self._echo(f"Error: {e}")

    def execute_screen_action(self, action: str):
        """Central dispatcher for Screen Menu and Command Line actions."""
        if action == "root":
            self._screen_menu._state = "root"
            self._screen_menu._refresh()
            return

        # File ops
        if action == "save":     self._on_save()
        elif action == "open":   self._on_open()
        elif action == "open_std": self._on_open_std()
        elif action == "save_std": self._on_save_std()
        elif action == "export": self._on_export()
        elif action == "quit":   self.close()

        # Tools
        elif action == "select":       self._activate_tool("select")
        elif action == "node":         self._activate_tool("node")
        elif action == "member":       self._activate_tool("member")
        elif action == "delete":       self._activate_tool("delete")
        elif action == "support":      self._echo("Support tool — coming soon")
        elif action == "nodal_load":   self._echo("Nodal load — coming soon")
        elif action == "member_load":  self._echo("Member load — coming soon")
        elif action == "load_cases":   self._echo("Load cases dialog — coming soon")
        elif action == "load_combos":  self._echo("Load combos dialog — coming soon")

        # Analysis
        elif action == "analyze":
            self._run_analysis()

        # Results
        elif action == "show_displacements":
            self._show_results_table("displacements")
        elif action == "show_reactions":
            self._show_results_table("reactions")
        elif action == "show_forces":
            self._show_results_table("forces")
        elif action == "toggle_deformed":
            v = self._view
            v.show_deformed = not v.show_deformed
            self._echo(f"Deformed: {'ON' if v.show_deformed else 'OFF'} | Scale: {v.deformed_scale:.0f}x")
            v.update()
        elif action == "scale_up":
            self._view.deformed_scale *= 1.5
            self._echo(f"Scale: {self._view.deformed_scale:.0f}x")
            self._view.update()
        elif action == "scale_down":
            self._view.deformed_scale /= 1.5
            self._echo(f"Scale: {self._view.deformed_scale:.0f}x")
            self._view.update()

        # Settings
        elif action == "grid_toggle":
            self._view.renderer.draw_grid_enabled = not self._view.renderer.draw_grid_enabled
            self._view.update()
        elif action == "materials":
            self._echo("Materials dialog — coming soon")
        elif action == "sections":
            self._echo("Sections dialog — coming soon")
        elif action == "units":
            self._echo("Units: metric (kN, m)")

        else:
            self._echo(f"Unknown: {action}")

    def _show_results_table(self, what: str):
        """Show analysis results in status bar / future dialog."""
        r = self._view.analysis_result
        if not r or not r.success:
            self._echo("No results — run analysis first")
            return
        if what == "displacements":
            self._echo(f"Max displacement: {r.max_displacement()*1000:.2f} mm")
        elif what == "reactions":
            self._echo("Reactions — check Export XLSX for full table")
        elif what == "forces":
            self._echo("Forces — check Export XLSX for full table")

    # ── Actions ──────────────────────────────────────

    def _run_analysis(self):
        """Execute FEM analysis on the current model."""
        if self._document.member_count == 0:
            self._echo("No members to analyze")
            return
        self._echo("Running analysis...")
        try:
            result = run_analysis_for_document(self._document)
            if result.success:
                self._view.analysis_result = result
                self._echo(
                    f"Analysis OK | Max displacement: {result.max_displacement()*1000:.2f} mm"
                )
            else:
                self._echo(f"Analysis failed: {result.errors[0] if result.errors else 'unknown'}")
        except Exception as e:
            self._echo(f"Error: {e}")

    def _toggle_deformed(self):
        v = self._view
        v.show_deformed = not v.show_deformed
        self._echo(f"Deformed shape: {'ON' if v.show_deformed else 'OFF'} | Scale: {v.deformed_scale:.0f}x")
        v.update()

    def _toggle_grid(self):
        self._view.renderer.draw_grid_enabled = not self._view.renderer.draw_grid_enabled
        self._view.update()

    def _on_new(self):
        self._document = Document()
        self._view.document = self._document
        self._view.analysis_result = None
        self._view.update()
        self._echo("New project")

    def _on_open(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "Open", "", "DogCalC (*.dogcalc)")
        if path:
            from src.io.project_file import load_document
            self._document = load_document(path)
            self._view.document = self._document
            self._filename = path
            self._view.update()
            self._echo(f"Loaded: {path}")

    def _on_save(self):
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Save", self._filename or "", "DogCalC (*.dogcalc)")
        if path:
            from src.io.project_file import save_document
            save_document(self._document, path)
            self._filename = path
            self._echo(f"Saved: {path}")

    def _on_open_std(self):
        """Import STAAD .std file."""
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getOpenFileName(self, "Open STAAD File", "", "STAAD (*.std);;All (*.*)")
        if path:
            from src.io.staad_file import parse_std
            self._document = parse_std(path)
            self._view.document = self._document
            self._filename = None
            self._view.analysis_result = None
            self._view.update()
            self._fit_view_to_model()
            self._echo(f"Imported STD: {path} ({self._document.node_count}N, {self._document.member_count}M)")

    def _on_save_std(self):
        """Export to STAAD .std file."""
        from PySide6.QtWidgets import QFileDialog
        path, _ = QFileDialog.getSaveFileName(self, "Save STAAD File", "model.std", "STAAD (*.std)")
        if path:
            from src.io.staad_file import write_std
            write_std(self._document, path)
            self._echo(f"Exported STD: {path}")

    def _on_export(self):
        """Export results to Excel."""
        from PySide6.QtWidgets import QFileDialog
        r = self._view.analysis_result
        if not r or not r.success:
            self._echo("No results to export — run analysis first")
            return
        path, _ = QFileDialog.getSaveFileName(self, "Export Results", "results.xlsx", "Excel (*.xlsx)")
        if path:
            from src.io.export import export_results_to_excel
            export_results_to_excel(self._document, r, path)
            self._echo(f"Exported: {path}")

    def _on_select_all(self):
        self._echo("Select All — not implemented")

    def _fit_view_to_model(self):
        """Adjust camera to frame all model content."""
        doc = self._document
        if not doc or doc.node_count == 0:
            return
        from numpy import array
        xs = array([n.x for n in doc.nodes.values()])
        ys = array([n.y for n in doc.nodes.values()])
        zs = array([n.z for n in doc.nodes.values()])
        center = array([(xs.max()+xs.min())/2, (ys.max()+ys.min())/2, (zs.max()+zs.min())/2])
        span = max(xs.max()-xs.min(), ys.max()-ys.min(), zs.max()-zs.min(), 1.0)
        self._view.camera.target = center
        self._view.camera.radius = span * 2.0
        # Adjust grid and node size to model
        gs = 10 ** round(__import__('math').log10(span / 10))
        self._view.renderer.grid_spacing = max(gs, 0.5)
        self._view.renderer.grid_size = int(span / gs) + 5
        self._view.renderer._node_scale = max(span / 8.0, 0.5)
        self._view.update()

    # ── Theme ────────────────────────────────────────

    def _apply_theme(self):
        self.setStyleSheet(f"""
            QMainWindow {{ background-color: {CLR_MENU_BG}; }}
            QMenuBar {{
                background-color: {CLR_MENU_BG}; color: {CLR_MENU_TEXT};
                border-bottom: 1px solid #1a1a2e;
            }}
            QMenuBar::item:selected {{ background-color: {CLR_MENU_SEL}; }}
            QMenu {{
                background-color: {CLR_MENU_BG}; color: {CLR_MENU_TEXT};
                border: 1px solid #1a1a2e;
            }}
            QMenu::item:selected {{ background-color: {CLR_MENU_SEL}; }}
            QStatusBar {{
                background-color: {CLR_STATUS_BG}; color: white;
                font-family: 'Courier New', monospace; font-size: 12px;
                border-top: 1px solid #1a1a2e;
            }}
        """)
