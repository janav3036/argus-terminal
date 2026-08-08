import sys
from pathlib import Path
from PySide6.QtCore import Qt, QCoreApplication, QPropertyAnimation, QEasingCurve
from PySide6.QtWidgets import QApplication, QMainWindow, QHBoxLayout, QStackedWidget, QWidget, QVBoxLayout, QPushButton
from PySide6.QtWebEngineWidgets import QWebEngineView

from core.base_module import ArgusModule
from core.sidebar import Sidebar 
from core.status_bar import StatusBar
from core.top_bar import TopBar
from home.home_page import HomePage
from module_registry import MODULES
from data.watchlist_feed import WatchlistFeedThread
from data.sector_feed import SectorFeedThread
from data.yfinance_feed import YFinanceFeedThread
from data.fx_commodities_feed import FxCommoditiesFeedThread

class ArgusMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Argus")
        self.resize(1600, 900)

        self._modules = MODULES
        self._module_widgets: dict[ArgusModule, QWidget] = {}

        self._sidebar = Sidebar(self._modules)
        self._sidebar.module_selected.connect(self._show_module)
        self._sidebar.setMinimumWidth(0)
        self._sidebar.setMaximumWidth(240)

        self._content = QStackedWidget()

        # A QWebEngineView added to the window's widget tree for the first
        # time *after* the window has already been shown forces Qt/Cocoa to
        # convert the native window's backing store to support OpenGL
        # compositing - on macOS this is visible as the whole window closing
        # and reopening. Adding one here, before window.show() is ever
        # called (this constructor runs before that), means that conversion
        # happens once during the window's initial creation instead of
        # later, mid-session, the first time a module actually shows one.
        # It has to be a genuine page of self._content (part of the window's
        # tree) to matter — an orphaned, unparented QWebEngineView doesn't
        # affect the main window's surface at all.
        self._webengine_warmup = QWebEngineView()
        self._webengine_warmup.setFixedSize(0, 0)
        self._content.addWidget(self._webengine_warmup)

        self._home_page = HomePage()
        self._content.addWidget(self._home_page)
        self._content.setCurrentWidget(self._home_page)

        self._top_bar = TopBar()

        self._sidebar_toggle_btn = QPushButton("☰")
        self._sidebar_toggle_btn.setFixedWidth(28)
        self._sidebar_toggle_btn.clicked.connect(self._toggle_sidebar)
        self._sidebar.home_requested.connect(
            lambda: self._content.setCurrentWidget(self._home_page)
        )

        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(12, 12, 0, 12)
        row_layout.addWidget(self._sidebar)
        row_layout.addWidget(self._sidebar_toggle_btn)
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

        self._watchlist_thread = WatchlistFeedThread()
        self._watchlist_thread.data_updated.connect(self._home_page.watchlist_chart.update_data)
        self._watchlist_thread.start()

        self._sector_thread = SectorFeedThread()
        self._sector_thread.data_updated.connect(self._home_page.sector_heatmap.update_data)
        self._sector_thread.start()

        self._fx_commodities_thread = FxCommoditiesFeedThread()
        self._fx_commodities_thread.data_updated.connect(self._home_page.fx_commodities_panel.update_data)
        self._fx_commodities_thread.start()


    def _toggle_sidebar(self) -> None:
        target_width = 0 if self._sidebar.maximumWidth() > 0 else 240
        self._sidebar_animation = QPropertyAnimation(self._sidebar, b"maximumWidth")
        self._sidebar_animation.setDuration(200)
        self._sidebar_animation.setStartValue(self._sidebar.maximumWidth())
        self._sidebar_animation.setEndValue(target_width)
        self._sidebar_animation.setEasingCurve(QEasingCurve.InOutCubic)
        self._sidebar_animation.start()

    def _show_module(self, module: ArgusModule) -> None:
        if module not in self._module_widgets:
            widget = module.build_widget()
            self._module_widgets[module] = widget
            self._content.addWidget(widget)

        source = module.get_status_source()
        signal = module.get_status_signal()
        if source is not None and signal is not None:
            signal.connect(lambda state, src=source: self._status_bar.set_status(src, state))

        self._content.setCurrentWidget(self._module_widgets[module])
        
    def closeEvent(self, event) -> None:
        for module, widget in self._module_widgets.items():
            module.shutdown()
        self._yfinance_thread.requestInterruption()
        self._yfinance_thread.wait()
        self._watchlist_thread.requestInterruption()
        self._watchlist_thread.wait()
        self._sector_thread.requestInterruption()
        self._sector_thread.wait()
        self._fx_commodities_thread.requestInterruption()
        self._fx_commodities_thread.wait()
        super().closeEvent(event)

def run() -> None:
    QCoreApplication.setAttribute(Qt.AA_ShareOpenGLContexts, True)
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    stylesheet_path = Path(__file__).parent / "assets" / "styles" / "argus_dark.qss"
    app.setStyleSheet(stylesheet_path.read_text())

    window = ArgusMainWindow()
    window.show()
    sys.exit(app.exec())