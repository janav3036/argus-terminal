from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QFrame, QLabel
from home.watchlist_chart import WatchlistChart
from home.sector_heatmap import SectorHeatmap
from home.fx_commodities_panel import FxCommoditiesPanel

def _placeholder_panel(title: str) -> QFrame:
    frame = QFrame()
    frame.setFrameShape(QFrame.Shape.StyledPanel)
    layout = QVBoxLayout(frame)
    layout.addWidget(QLabel(title))
    return frame

class HomePage(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        news_column = _placeholder_panel("News Feed")

        overview_column = QVBoxLayout()
        self.watchlist_chart = WatchlistChart()
        overview_column.addWidget(self.watchlist_chart, stretch=1)
        self.sector_heatmap = SectorHeatmap()
        overview_column.addWidget(self.sector_heatmap, stretch=1)
        overview_widget = QWidget()
        overview_widget.setLayout(overview_column)

        conditions_column = QVBoxLayout()
        conditions_column.addWidget(_placeholder_panel("Volatility Conditions"))
        conditions_column.addWidget(_placeholder_panel("Yield Curve Snapshot"))
        self.fx_commodities_panel = FxCommoditiesPanel()
        conditions_column.addWidget(self.fx_commodities_panel)
        conditions_widget = QWidget()
        conditions_widget.setLayout(conditions_column)

        layout = QHBoxLayout(self)
        layout.addWidget(news_column, stretch=1)
        layout.addWidget(overview_widget, stretch=3)
        layout.addWidget(conditions_widget, stretch=1)