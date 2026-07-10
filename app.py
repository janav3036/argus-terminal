import sys
from PySide6.QtWidgets import QApplication, QMainWindow

class ArgusMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Argus")
        self.resize(1600,900)

def run() -> None:
    app = QApplication(sys.argv)
    window = ArgusMainWindow()
    window.show()
    sys.exit(app.exec())