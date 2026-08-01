import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QButtonGroup

from modules.order_book.module import CandlestickItem
from data.watchlist_feed import SYMBOLS

CHART_Y_PADDING_FRAC = 0.05

class WatchlistChart(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        tab_row = QHBoxLayout()
        self._tab_group = QButtonGroup(self)
        self._tab_group.setExclusive(True)
        self._tab_buttons = {}
        for label in SYMBOLS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            self._tab_group.addButton(btn)
            self._tab_buttons[label] = btn
            tab_row.addWidget(btn)
            btn.clicked.connect(lambda checked, l=label: self._on_tab_clicked(l))
        self._tab_buttons["NIFTY 50"].setChecked(True)
        self._data = {}
        self._active_label = "NIFTY 50"
        tab_row.addStretch()

        self._plot = pg.PlotWidget()
        self._plot.setBackground("#141414")
        self._plot.showGrid(x=False, y=True, alpha=0.15)
        self._candle_item = CandlestickItem()
        self._plot.addItem(self._candle_item)
        self._plot.setMouseEnabled(x=True, y=True)
        self._plot.getViewBox().disableAutoRange()
        self._plot.getViewBox().setDefaultPadding(0.05)

        layout = QVBoxLayout(self)
        layout.addLayout(tab_row)
        layout.addWidget(self._plot)
        
    def update_data(self, payload: dict) -> None:
        self._data.update(payload)
        self._render(self._active_label)

    def _on_tab_clicked(self, label: str) -> None:
        self._active_label = label
        self._render(label)

    def _render(self, label: str) -> None:
        candles = self._data.get(label, [])
        self._candle_item.invalidate()
        self._candle_item.set_data(candles)
        if not candles:
            return

        highs = [c[2] for c in candles]
        lows = [c[3] for c in candles]
        data_high = max(highs)
        data_low = min(lows)
        span = data_high - data_low
        mid_price = (data_high + data_low) / 2
        pad = max(span * CHART_Y_PADDING_FRAC, mid_price * 0.001)

        min_y_range = max(mid_price * 0.0005, span * 0.02, 0.0001)
        max_y_range = span + 2 * pad
        self._plot.setLimits(
            xMin=0, xMax=len(candles),
            minXRange=10, maxXRange=len(candles),
            minYRange=min_y_range, maxYRange=max_y_range,
            yMin=data_low - pad, yMax=data_high + pad,
        )

        self._plot.setXRange(0, len(candles), padding=0.02)
        self._plot.setYRange(data_low - pad, data_high + pad, padding=0)