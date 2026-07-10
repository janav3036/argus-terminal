import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QStackedWidget, QWidget

from core.base_module import ArgusModule
from core.sidebar import Sidebar 
from module_registry import MODULES

class ArgusMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Argus")
        self.resize(1600, 900)

        self._modules = [cls() for cls in MODULES]
        self._module_widgets: dict[ArgusModule, QWidget] = {}

        self._sidebar = Sidebar(self._modules)
        self._sidebar.module_selected.connect(self._show_module)
        self._sidebar.setFixedWidth(240)

        self._content = QStackedWidget()

        central = QWidget()
        layout = QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._sidebar)
        layout.addWidget(self._content)
        self.setCentralWidget(central)

    def _show_module(self, module: ArgusModule) -> None:
        if module not in self._module_widgets:
            widget = module.build_widget()
            self._module_widgets[module] = widget
            self._content.addWidget(widget)
        self._content.setCurrentWidget(self._module_widgets[module])
        
def run() -> None:
    app = QApplication(sys.argv)
    window = ArgusMainWindow()
    window.show()
    sys.exit(app.exec())