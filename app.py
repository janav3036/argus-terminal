import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QStackedWidget, QWidget, QVBoxLayout

from core.base_module import ArgusModule
from core.sidebar import Sidebar 
from core.status_bar import StatusBar
from core.top_bar import TopBar
from module_registry import MODULES
from data.yfinance_feed import YFinanceFeedThread

class ArgusMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Argus")
        self.resize(1600, 900)

        self._modules = MODULES
        self._module_widgets: dict[ArgusModule, QWidget] = {}

        self._sidebar = Sidebar(self._modules)
        self._sidebar.module_selected.connect(self._show_module)
        self._sidebar.setFixedWidth(240)

        self._content = QStackedWidget()

        self._top_bar = TopBar()

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)
        row_layout.addWidget(self._sidebar)
        row_layout.addWidget(self._content)

        central = QWidget()
        outer_layout = QVBoxLayout(central)
        outer_layout.setContentsMargins(0, 0, 0, 0)
        outer_layout.addWidget(self._top_bar)
        outer_layout.addWidget(row)
        self.setCentralWidget(central)

        self._status_bar = StatusBar()
        self.setStatusBar(self._status_bar)

        self._yfinance_thread = YFinanceFeedThread()
        self._yfinance_thread.data_updated.connect(self._top_bar.update_data)
        self._yfinance_thread.status_changed.connect(
            lambda state: self._status_bar.set_status("yfinance", state)
        )
        self._yfinance_thread.start()


    def _show_module(self, module: ArgusModule) -> None:
        if module not in self._module_widgets:
            widget = module.build_widget()
            self._module_widgets[module] = widget
            self._content.addWidget(widget)
        self._content.setCurrentWidget(self._module_widgets[module])
        
    def closeEvent(self, event) -> None:
        self._yfinance_thread.requestInterruption()
        self._yfinance_thread.wait()
        super().closeEvent(event)

def run() -> None:
    app = QApplication(sys.argv)
    window = ArgusMainWindow()
    window.show()
    sys.exit(app.exec())