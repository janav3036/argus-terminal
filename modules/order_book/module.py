from collections import deque
import time
import pyqtgraph as pg
from PySide6.QtCore import Qt,QPointF, QRectF
from PySide6.QtGui import QPainter, QPicture, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QButtonGroup, QFrame, QGridLayout
)

from core.base_module import ArgusModule 
from modules.order_book.bybit_bridge import INSTRUMENTS
from modules.order_book.lob_feed_thread import LOBFeedThread

PRICE_HISTORY_LEN = 300
CANDLE_INTERVAL_SECONDS = 1
CANDLE_HISTORY_LEN = 120

class CandlestickItem(pg.GraphicsObject):
    """Renders a list of (x, ohlc) tuples"""

    def __init__(self, ):
        super().__init__()
        self._picture = QPicture()

    def set_data(self, candles: list[tuple[float, float, float, float, float]]) -> None:
        self._picture = QPicture()
        painter = QPainter(self._picture)
        width = 0.6

        for x, open_, high, low, close in candles:
            color = QColor("#2ECC71") if close >= open_ else QColor("#E74C3C")
            painter.setPen(pg.mkPen(color))
            painter.drawLine(QPointF(x, low), QPointF(x, high))
            painter.setBrush(pg.mkBrush(color))
            body_top = max(open_, close)
            body_height = abs(close - open_) or 0.01
            painter.drawRect(QRectF(x - width / 2, body_top, width, -body_height))

        painter.end()
        self.informViewBoundsChanged()
        self.update()

    def paint(self, painter, *args) -> None:
        painter.drawPicture(0, 0, self._picture)

    def boundingRect(self):
        return QRectF(self._picture.boundingRect())

class OrderBookModule(ArgusModule):
    """Wraps LOB microstructure lab as an argus module"""

    def __init__(self):
        self._thread: LOBFeedThread | None = None
        self._latest: dict[str, dict] = {}
        self._selected_symbol = INSTRUMENTS[0]
        self._price_history: dict[str, deque[float]] = {
            symbol: deque(maxlen=PRICE_HISTORY_LEN) for symbol in INSTRUMENTS
        }
        self._candles: dict[str, deque[tuple[float, float, float, float]]] = {
            symbol: deque(maxlen=CANDLE_HISTORY_LEN) for symbol in INSTRUMENTS
        }
        self._current_candle: dict[str, list[float]] = {}
        self._current_bucket: dict[str, int] = {}

    def get_sidebar_label(self) -> str:
        return "Order Book"

    def get_status_preview(self) -> str:
        data = self._latest.get(self._selected_symbol)
        if data is None or data.get("mid_price") is None:
            return "Connecting..."
        return f"{self._selected_symbol}, Mid - {data['mid_price']:,.2f}"
    
    def get_status_source(self) -> str | None:
        return "Bybit WSS"
    
    def get_status_signal(self):
        return self._thread.status_changed if self._thread is not None else None

    def _on_tab_clicked(self, button) -> None:
        self._selected_symbol = button.text()
        self._refresh_display()

    def _update_candle(self, symbol: str, price: float) -> None:
        bucket = int(time.time() // CANDLE_INTERVAL_SECONDS)
        current_bucket = self._current_bucket.get(symbol)

        if current_bucket is None:
            self._current_bucket[symbol] = bucket
            self._current_candle[symbol] = [price, price, price, price]
            return

        if bucket != current_bucket:
            self._candles[symbol].append(tuple(self._current_candle[symbol]))
            self._current_bucket[symbol] = bucket
            self._current_candle[symbol] = [price, price, price, price]
        else:
            candle = self._current_candle[symbol]
            candle[1] = max(candle[1], price)
            candle[2] = min(candle[2], price)
            candle[3] = price

    def _on_data(self, payload: dict) -> None:
        symbol = payload["symbol"]
        self._latest[symbol] = payload
        mid = payload.get("mid_price")
        if mid is not None:
            self._price_history[symbol].append(mid)
            self._update_candle(symbol, mid)
        if symbol == self._selected_symbol:
            self._refresh_display()

    def _refresh_display(self) -> None:
        data = self._latest.get(self._selected_symbol, {})
        for key, _ in self._metrics_defs:
            value = data.get(key)
            label = self._value_labels[key]
            if value is None:
                label.setText("-")
            elif key == "relative_spread":
                label.setText(f"{value:.6f}")
            elif key == "obi":
                label.setText(f"{value:+.3f}")
                label.setStyleSheet(
                    "font-size: 16px; font-weight: 600; color: "
                    + ("#2ECC71" if value >= 0 else "#E74C3C")
                )
            else:
                label.setText(f"{value:,.2f}")    
        
        candles = self._candles[self._selected_symbol]
        current = self._current_candle.get(self._selected_symbol)
        candle_data = [(i, o, h, l, c) for i, (o, h, l, c) in enumerate(candles)]
        if current is not None:
            candle_data.append((len(candles), *current))
        self._candle_item.set_data(candle_data)

    def shutdown(self) -> None:
        if self._thread is not None:
            self._thread.stop()
            self._thread.wait()

    def build_widget(self) -> QWidget:
        widget = QWidget()
        outer_layout = QVBoxLayout(widget)

        heading = QLabel("ORDER BOOK")
        heading.setAlignment(Qt.AlignCenter)
        heading.setStyleSheet("font-size: 16px; font-weight: bold; padding: 6px")
        outer_layout.addWidget(heading)

        description_frame = QFrame()
        description_frame.setFrameShape(QFrame.Box)
        description_layout = QVBoxLayout(description_frame)
        description = QLabel(
            "Live L2 order book and microstructure metrics streamed from Bybit. "
            "All three instruments stream concurrently — the tabs below only "
            "change which symbol is displayed."
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignCenter)
        description_layout.addWidget(description)
        outer_layout.addWidget(description_frame)

        tab_row = QHBoxLayout()
        self._tab_group = QButtonGroup(widget)
        self._tab_group.setExclusive(True)
        for symbol in INSTRUMENTS:
            btn = QPushButton(symbol)
            btn.setCheckable(True)
            btn.setChecked(symbol == self._selected_symbol)
            self._tab_group.addButton(btn)
            tab_row.addWidget(btn)
        tab_row.addStretch()
        outer_layout.addLayout(tab_row)

        metrics_frame = QFrame()
        metrics_frame.setFrameShape(QFrame.Box)
        metrics_grid = QGridLayout(metrics_frame)

        self._metrics_defs = [
            ("mid_price", "Mid Price"),
            ("spread", "Spread"),
            ("relative_spread", "Relative Spread"),
            ("microprice", "Microprice"),
            ("obi", "Order Book Imbalance"),
        ]

        self._value_labels: dict[str, QLabel] = {}
        for col, (key, label_text) in enumerate(self._metrics_defs):
            label = QLabel(label_text)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: #888888; font-size: 10px;")
            metrics_grid.addWidget(label, 0, col)

            value = QLabel("-")
            value.setAlignment(Qt.AlignCenter)
            value.setStyleSheet("font-size: 16px; font-weight: 600;")
            metrics_grid.addWidget(value, 1, col)
            self._value_labels[key] = value

        outer_layout.addWidget(metrics_frame)
        
        chart_frame = QFrame()
        chart_frame.setFrameShape(QFrame.Box)
        chart_layout = QVBoxLayout(chart_frame)

        self._price_plot = pg.PlotWidget()
        self._price_plot.setBackground("#141414")
        self._price_plot.showGrid(x=False, y=True, alpha=0.15)
        self._candle_item = CandlestickItem()
        self._price_plot.addItem(self._candle_item)
        chart_layout.addWidget(self._price_plot)

        outer_layout.addWidget(chart_frame, 1)

        self._tab_group.buttonClicked.connect(self._on_tab_clicked)

        self._thread = LOBFeedThread()
        self._thread.data_updated.connect(self._on_data)
        self._thread.start()

        return widget