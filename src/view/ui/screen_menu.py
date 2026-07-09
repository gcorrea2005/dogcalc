"""Screen Menu — right-side hierarchical tool menu (classic AutoCAD / STAAD style)."""

from PySide6.QtWidgets import QListWidget, QListWidgetItem
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor

CLR_BG   = "#0000AA"
CLR_TEXT = "#FFFFFF"
CLR_HEAD = "#44AAFF"
CLR_SEL  = "#003388"
CLR_BACK = "#FFCC00"


class ScreenMenu(QListWidget):
    """Right-docked hierarchical menu for tool selection and actions.

    Navigation:
      - Click on a submenu header → enter that menu
      - Click on a tool → activates tool in MainWindow
      - Click [<-BACK] → return to parent menu
    """

    def __init__(self, main_window, parent=None):
        super().__init__(parent)
        self._mw = main_window
        self._state = "root"
        self.setFixedWidth(170)
        self.setStyleSheet(f"""
            QListWidget {{
                background-color: {CLR_BG};
                color: {CLR_TEXT};
                border: none;
                font-family: 'Courier New', monospace;
                font-size: 13px;
            }}
            QListWidget::item {{ padding: 4px 8px; }}
            QListWidget::item:selected {{ background-color: {CLR_SEL}; }}
            QListWidget::item:hover {{ background-color: #002266; }}
        """)
        self.itemClicked.connect(self._on_click)
        self._refresh()

    # ── Menu definitions ──────────────────────────

    def _refresh(self):
        self.clear()

        menus = {
            "root": [
                ("DogCalC", None, True),
                ("* * * *", None, False), ("", None, False),
                ("GEOMETRY  ", "menu_geom", False),
                ("LOADS     ", "menu_loads", False),
                ("ANALYSIS  ", "menu_analysis", False),
                ("RESULTS   ", "menu_results", False),
                ("SETTINGS  ", "menu_settings", False),
                ("", None, False),
                (" STD EDIT ", "std_editor", False),
                ("", None, False),
                (" SAVE     ", "save", False),
                (" OPEN     ", "open", False),
                (" STD IN   ", "open_std", False),
                (" STD OUT  ", "save_std", False),
                (" EXPORT   ", "export", False),
                ("", None, False),
                (" QUIT     ", "quit", False),
            ],
            "menu_geom": [
                (" GEOMETRY ", None, True), ("", None, False),
                (" NODE EDIT ", "node_table", False),
                (" MEMB EDIT ", "member_table", False),
                (" SUPP EDIT ", "support_table", False),
                ("", None, False),
                (" NODE      ", "node", False),
                (" MEMBER    ", "member", False),
                ("", None, False),
                (" SELECT    ", "select", False),
                (" DELETE    ", "delete", False),
                ("", None, False),
                (" [<-BACK]  ", "menu_root", False),
            ],
            "menu_loads": [
                ("  LOADS   ", None, True), ("", None, False),
                (" LC EDIT  ", "load_case_table", False),
                (" COMBO ED ", "combo_table", False),
                ("", None, False),
                (" [<-BACK] ", "menu_root", False),
            ],
            "menu_analysis": [
                (" ANALYSIS ", None, True), ("", None, False),
                (" RUN      ", "analyze", False),
                ("", None, False),
                (" [<-BACK] ", "menu_root", False),
            ],
            "menu_results": [
                (" RESULTS  ", None, True), ("", None, False),
                (" RESULTS  ", "results_viewer", False),
                (" DEFORMED ", "toggle_deformed", False),
                (" SCALE +  ", "scale_up", False),
                (" SCALE -  ", "scale_down", False),
                ("", None, False),
                (" [<-BACK] ", "menu_root", False),
            ],
            "menu_settings": [
                (" SETTINGS ", None, True), ("", None, False),
                (" GRID     ", "grid_toggle", False),
                ("", None, False),
                (" [<-BACK] ", "menu_root", False),
            ],
        }
        menus["menu_root"] = menus["root"]  # back button target

        S = self._state
        items = menus.get(S, [])

        for label, action, is_header in items:
            if label == "":
                item = QListWidgetItem("")
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                self.addItem(item)
                continue

            display = label.strip()
            is_back = display.startswith("[<-")

            if is_header:
                item = QListWidgetItem(display)
                item.setFlags(Qt.ItemFlag.NoItemFlags)
                item.setForeground(QColor(CLR_HEAD))
            elif is_back:
                item = QListWidgetItem(display)
                item.setData(Qt.ItemDataRole.UserRole, action)
                item.setForeground(QColor(CLR_BACK))
            else:
                item = QListWidgetItem(display)
                item.setData(Qt.ItemDataRole.UserRole, action)
                item.setForeground(QColor(CLR_TEXT))
            self.addItem(item)

    # ── Click handling ────────────────────────────

    def _on_click(self, item: QListWidgetItem):
        action = item.data(Qt.ItemDataRole.UserRole)
        if not action:
            return

        if action.startswith("menu_"):
            self._state = action
            self._refresh()
        else:
            self._mw.execute_screen_action(action)
