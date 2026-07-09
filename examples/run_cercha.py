"""Launch DogCalC with Warren truss pre-loaded."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PySide6.QtWidgets import QApplication
from src.view.ui.main_window import MainWindow
from src.io.staad_file import parse_std

STD_PATH = os.path.join(os.path.dirname(__file__), "cercha_warren.std")

app = QApplication(sys.argv)
app.setApplicationName("DogCalC")
window = MainWindow()

doc = parse_std(STD_PATH)
window._document = doc
window._view.document = doc
window._node_table._doc = doc
window._node_table.refresh()
window._member_table._doc = doc
window._member_table.refresh()
window._support_table._doc = doc
window._support_table.refresh()
window._view.refresh_view()
window._view.fit_to_model()
window._update_status(f"Warren: {doc.node_count}N {doc.member_count}M")

with open(STD_PATH) as f:
    window._std_editor.set_text(f.read())
window._std_editor._filepath = STD_PATH

window.show()
sys.exit(app.exec())
