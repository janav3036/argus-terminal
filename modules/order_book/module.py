from collections import deque
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QButtonGroup, QFrame, QGridLayout
)

from core.base_module import ArgusModule 
from modules.order_book.bybit_bridge import INSTRUMENTS
from modules.order_book.lob_feed_thread import LOBFeedThread

PRICE_HISTORY_LEN = 300

class OrderBookModule(ArgusModule):
    """Wraps LOB microstructure lab as an argus module"""

    def __init__(self):
        self._thread: LOBFeedThread | None = None
        self._latest: dict[str, dict] = {}
        self._selected_symbol = INSTRUMENTS[0]
        self._price_history: dict[str, deque[float]] = {
            symbol: deque(maxlen=PRICE_HISTORY_LEN) for symbol in INSTRUMENTS
        }

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

    def _on_data(self, payload: dict) -> None:
        symbol = payload["symbol"]
        self._latest[symbol] = payload
        mid = payload.get("mid_price")
        if mid is not None:
            self._price_history[symbol].append(mid)
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

        self._price_curve.setData(list(self._price_history[self._selected_symbol]))

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
        self._price_curve = self._price_plot.plot(pen=pg.mkPen("#2B5EA7", width=1.5))
        chart_layout.addWidget(self._price_plot)

        outer_layout.addWidget(chart_frame, 1)

        self._tab_group.buttonClicked.connect(self._on_tab_clicked)

        self._thread = LOBFeedThread()
        self._thread.data_updated.connect(self._on_data)
        self._thread.start()

        return widget