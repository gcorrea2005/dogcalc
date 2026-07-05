import sys
from PySide6.QtWidgets import QApplication
from src.view.ui.main_window import MainWindow


def run():
    app = QApplication(sys.argv)
    app.setApplicationName("DogCalC")
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
