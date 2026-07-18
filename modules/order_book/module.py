from collections import deque
import time
import pyqtgraph as pg
from PySide6.QtCore import Qt,QPointF, QRectF, QTimer
from PySide6.QtGui import QPainter, QPicture, QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QButtonGroup, QFrame, QGridLayout,
    QListWidget, QListWidgetItem, QScrollArea
)

from core.base_module import ArgusModule 
from modules.order_book.bybit_bridge import INSTRUMENTS
from modules.order_book.lob_feed_thread import LOBFeedThread
from modules.order_book.bybit_kline import KlineFetchWorker

PRICE_HISTORY_LEN = 300
CANDLE_HISTORY_LEN = 300
INTERVALS = [
    ("1m", 60),
    ("5m", 300),
    ("15m", 900),
    ("1h", 3600),
    ("4h", 14400),
    ("1D", 86400),
]


class CandlestickItem(pg.GraphicsObject):
    """Renders a list of (x, ohlc) tuples.

    Closed candles are cached in a separate picture from the live-updating
    current candle, so a tick only repaints one candle instead of redrawing
    the entire history every time.
    """

    def __init__(self, ):
        super().__init__()
        self._history_picture = QPicture()
        self._current_picture = QPicture()
        self._history_count = -1

    def invalidate(self) -> None:
        """Force the next set_data() call to rebuild the history picture
        from scratch, e.g. after switching symbol/interval."""
        self._history_count = -1

    def _draw_candle(self, painter: QPainter, x, open_, high, low, close, width=0.6) -> None:
        color = QColor("#2ECC71") if close >= open_ else QColor("#E74C3C")
        painter.setPen(pg.mkPen(color))
        painter.drawLine(QPointF(x, low), QPointF(x, high))
        painter.setBrush(pg.mkBrush(color))
        body_top = max(open_, close)
        body_height = abs(close - open_) or 0.01
        painter.drawRect(QRectF(x - width / 2, body_top, width, -body_height))

    def set_data(self, candles: list[tuple[float, float, float, float, float]]) -> None:
        if not candles:
            self._history_picture = QPicture()
            self._current_picture = QPicture()
            self._history_count = -1
            self.informViewBoundsChanged()
            self.update()
            return

        history, current = candles[:-1], candles[-1]

        if len(history) != self._history_count:
            self._history_picture = QPicture()
            painter = QPainter(self._history_picture)
            for x, open_, high, low, close in history:
                self._draw_candle(painter, x, open_, high, low, close)
            painter.end()
            self._history_count = len(history)

        self._current_picture = QPicture()
        painter = QPainter(self._current_picture)
        self._draw_candle(painter, *current)
        painter.end()

        self.informViewBoundsChanged()
        self.update()

    def paint(self, painter, *args) -> None:
        painter.drawPicture(0, 0, self._history_picture)
        painter.drawPicture(0, 0, self._current_picture)

    def boundingRect(self):
        rect = QRectF(self._history_picture.boundingRect())
        return rect.united(QRectF(self._current_picture.boundingRect()))

class OrderBookModule(ArgusModule):
    """Wraps LOB microstructure lab as an argus module"""

    def __init__(self):
        self._thread: LOBFeedThread | None = None
        self._latest: dict[str, dict] = {}
        self._selected_symbol = INSTRUMENTS[0]
        self._price_history: dict[str, deque[float]] = {
            symbol: deque(maxlen=PRICE_HISTORY_LEN) for symbol in INSTRUMENTS
        }
        self._selected_interval_seconds = INTERVALS[0][1]
        self._active_candles: deque[tuple[float, float, float, float]] = deque(maxlen=CANDLE_HISTORY_LEN)
        self._active_current_candle: list[float] | None = None
        self._active_bucket: int | None = None
        self._kline_worker: KlineFetchWorker | None = None
        self._feed_log: dict[str, deque[dict]] = {
            symbol: deque(maxlen=200) for symbol in INSTRUMENTS
        }
        self._depth_needs_fit = True
        self._connection_status = "disconnected"
        self._connected_since: float | None = None
        self._reconnect_count = 0
        self._sequence_gap_count = 0

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


    def _update_active_candle(self, price: float) -> None:
        if self._active_bucket is None:
            return
        bucket = int(time.time() // self._selected_interval_seconds)

        if bucket!=self._active_bucket:
            self._active_candles.append(tuple(self._active_current_candle))
            self._active_bucket = bucket
            self._active_current_candle = [price, price, price, price]
        else:
            candle = self._active_current_candle
            candle[1] = max(candle[1], price)
            candle[2] = min(candle[2], price)
            candle[3] = price

    def _make_ladder_row(self, color: str) -> tuple[QHBoxLayout, QLabel, QLabel]:
        row = QHBoxLayout()
        price_label = QLabel("")
        price_label.setStyleSheet(f"color: {color}; font-size: 12px;")
        size_label = QLabel("")
        size_label.setAlignment(Qt.AlignRight)
        size_label.setStyleSheet("color: #888888; font-size: 12px;")
        row.addWidget(price_label)
        row.addWidget(size_label)
        return row, price_label, size_label
    
    def _on_data(self, payload: dict) -> None:
        symbol = payload["symbol"]
        self._latest[symbol] = payload
        mid = payload.get("mid_price")
        if mid is not None:
            self._price_history[symbol].append(mid)
            if symbol == self._selected_symbol:
                self._update_active_candle(mid)
        if symbol == self._selected_symbol:
            self._refresh_display()

    def _on_connection_event(self, event: dict) -> None:
        kind = event["event"]
        if kind == "connected":
            self._connection_status = "connected"
            self._connected_since = time.time()
            self._refresh_diagnostics()
        elif kind == "reconnecting":
            self._connection_status = "reconnecting"
            self._connected_since = None
            self._reconnect_count += 1
            self._refresh_diagnostics()
        elif kind == "sequence_gap":
            self._sequence_gap_count += 1
            # not refreshed immediately — sequence_gap fires at high frequency
            # and the 1s QTimer already keeps this label current
        

    def _refresh_diagnostics(self) -> None:
        # (text color, background tint, border) per connection state
        status_pill_styles = {
            "connected": ("#2ECC71", "rgba(46, 204, 113, 0.12)", "rgba(46, 204, 113, 0.4)"),
            "reconnecting": ("#e0a030", "rgba(224, 160, 48, 0.12)", "rgba(224, 160, 48, 0.4)"),
            "disconnected": ("#E74C3C", "rgba(231, 76, 60, 0.12)", "rgba(231, 76, 60, 0.4)"),
        }
        color, background, border = status_pill_styles[self._connection_status]
        status_label = self._diagnostics_labels["status"]
        status_label.setText(self._connection_status.capitalize())
        status_label.setStyleSheet(f"""
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.05em;
            color: {color};
            background-color: {background};
            border: 1px solid {border};
            border-radius: 3px;
            padding: 3px 10px;
        """)

        if self._connected_since is not None:
            elapsed = int(time.time() - self._connected_since)
            minutes, seconds = divmod(elapsed, 60)
            self._diagnostics_labels['connected_since'].setText(f"{minutes:02d}:{seconds:02d}")
        else: 
            self._diagnostics_labels["connected_since"].setText("-")

        self._diagnostics_labels["reconnects"].setText(str(self._reconnect_count))
        self._diagnostics_labels["sequence_gaps"].setText(str(self._sequence_gap_count))

    def _set_controls_enabled(self, enabled: bool) -> None:
        for btn in self._tab_group.buttons():
            btn.setEnabled(enabled)
        for btn in self._interval_group.buttons():
            btn.setEnabled(enabled)

    def _fetch_candles(self) -> None:
        self._active_candles.clear()
        self._active_current_candle = None
        self._active_bucket = None
        self._depth_needs_fit = True
        self._candle_item.invalidate()
        self._refresh_display()

        self._price_plot.setXRange(0, CANDLE_HISTORY_LEN, padding = 0.02)
        self._price_plot.enableAutoRange(axis="y")
        self._price_plot.getViewBox().updateAutoRange()

        self._set_controls_enabled(False)
        self._kline_worker = KlineFetchWorker(self._selected_symbol, self._selected_interval_seconds)
        self._kline_worker.finished_fetch.connect(self._on_klines_fetched)
        self._kline_worker.failed.connect(self._on_klines_failed)
        self._kline_worker.start()

    def _on_klines_fetched(self, symbol: str, interval_seconds: int, candles: list[dict]) -> None:
        self._set_controls_enabled(True)
        if symbol!=self._selected_symbol or interval_seconds!=self._selected_interval_seconds:
            return
        
        *history, current = candles
        self._active_candles.extend((c["open"], c["high"], c["low"], c["close"]) for c in history)
        self._active_current_candle = [current["open"], current["high"], current["low"], current["close"]]
        self._active_bucket = current["bucket"]
        self._refresh_display()

    def _on_klines_failed(self, message: str) -> None:
        self._set_controls_enabled(True)
        print(f"Kline fetch failed: {message}")

    def _on_tab_clicked(self, button) -> None:
        self._selected_symbol = button.text()
        self._rebuild_feed_log_widget()
        self._fetch_candles()

    def _on_interval_clicked(self, button) -> None:
        self._selected_interval_seconds = button.property("interval_seconds")
        self._fetch_candles()

    def _format_feed_row(self, row: dict) -> str:
        return f"{row['side'].upper():>3}  {row['price']:>12,.2f}  {row['size']:>10.4f}"

    def _on_tick(self, row: dict) -> None:
        symbol = row["symbol"]
        self._feed_log[symbol].append(row)
        if symbol != self._selected_symbol:
            return

        item = QListWidgetItem(self._format_feed_row(row))
        item.setForeground(QColor("#2ECC71") if row["side"] == "bid" else QColor("#E74C3C"))
        self._feed_log_widget.insertItem(0, item)
        while self._feed_log_widget.count() > 40:
            self._feed_log_widget.takeItem(self._feed_log_widget.count() - 1)

    def _rebuild_feed_log_widget(self) -> None:
        self._feed_log_widget.clear()
        for row in reversed(self._feed_log[self._selected_symbol]):
            item = QListWidgetItem(self._format_feed_row(row))
            item.setForeground(QColor("#2ECC71") if row["side"] == "bid" else QColor("#E74C3C"))
            self._feed_log_widget.addItem(item)


    def _refresh_ladder(self) -> None:
        data = self._latest.get(self._selected_symbol, {})
        asks = list(reversed(data.get("top_asks", [])))
        bids = data.get("top_bids", [])

        for i, (price_label, size_label) in enumerate(self._ask_row_labels):
            if i < len(asks):
                price, size = asks[i]
                price_label.setText(f"{price:,.2f}")
                size_label.setText(f"{size:.4f}")
            else:
                price_label.setText("")
                size_label.setText("")

        for i, (price_label, size_label) in enumerate(self._bid_row_labels):
            if i < len(bids):
                price, size = bids[i]
                price_label.setText(f"{price:,.2f}")
                size_label.setText(f"{size:.4f}")
            else:
                price_label.setText("")
                size_label.setText("")

        if asks and bids:
            spread = asks[-1][0] - bids[0][0]
            self._ladder_spread_label.setText(f"spread {spread:.2f}")
        else:
            self._ladder_spread_label.setText("")
    
    def _refresh_depth_chart(self) -> None:
        data = self._latest.get(self._selected_symbol, {})
        bids = data.get("top_bids", [])
        asks = data.get("top_asks", [])

        running = 0.0
        bid_points = []
        for price, size in bids:
            running += size
            bid_points.append((price, running))
        bid_points.reverse()

        running = 0.0
        ask_points = []
        for price, size in asks:
            running += size
            ask_points.append((price, running))

        if bid_points:
            x_bids, y_bids = zip(*bid_points)
            self._bid_depth_curve.setData(x_bids, y_bids)
        else:
            self._bid_depth_curve.setData([], [])

        if ask_points:
            x_asks, y_asks = zip(*ask_points)
            self._ask_depth_curve.setData(x_asks, y_asks)
        else:
            self._ask_depth_curve.setData([], [])

        if self._depth_needs_fit and (bid_points or ask_points):
            self._depth_plot.getViewBox().autoRange()
            self._depth_needs_fit = False

    def _periodic_depth_refit(self) -> None:
        # The depth chart deliberately doesn't refit on every tick (that was
        # jittery) - but fitting only once, right after load, means the view
        # goes stale as price drifts, leaving growing dead margins on the
        # sides. Refit occasionally instead, as a middle ground.
        data = self._latest.get(self._selected_symbol, {})
        if data.get("top_bids") or data.get("top_asks"):
            self._depth_plot.getViewBox().autoRange()

    def _update_price_zoom_limits(self, candle_data: list[tuple[float, float, float, float, float]]) -> None:
        if not candle_data:
            return

        highs = [c[2] for c in candle_data]
        lows = [c[3] for c in candle_data]
        data_high = max(highs)
        data_low = min(lows)
        span = data_high - data_low
        mid_price = (data_high + data_low) / 2

        min_y_range = max(mid_price * 0.0005, span * 0.05, 0.0001)
        max_y_range = max(span * 5, min_y_range * 10)

        self._price_plot.setLimits(minYRange=min_y_range, maxYRange=max_y_range)

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
        
        candles = self._active_candles
        current = self._active_current_candle
        candle_data = [(i, o, h, l, c) for i, (o, h, l, c) in enumerate(candles)]
        if current is not None:
            candle_data.append((len(candles), *current))
        self._candle_item.set_data(candle_data)
        self._update_price_zoom_limits(candle_data)
        self._refresh_ladder()
        self._refresh_depth_chart()

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

        interval_row = QHBoxLayout()
        self._interval_group = QButtonGroup(widget)
        self._interval_group.setExclusive(True)
        for label, seconds in INTERVALS:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setChecked(seconds == self._selected_interval_seconds)
            btn.setProperty("interval_seconds", seconds)
            self._interval_group.addButton(btn)
            interval_row.addWidget(btn)
        interval_row.addStretch()
        outer_layout.addLayout(interval_row)

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
        self._price_plot.setXRange(0, CANDLE_HISTORY_LEN, padding=0.02)
        self._price_plot.setMouseEnabled(x=True, y=True)
        self._price_plot.setLimits(
            xMin=0, xMax=CANDLE_HISTORY_LEN,
            minXRange=10, maxXRange=CANDLE_HISTORY_LEN,
        )
        self._price_plot.enableAutoRange(axis="y")
        self._price_plot.getViewBox().setDefaultPadding(0.05)
        chart_layout.addWidget(self._price_plot)

        outer_layout.addWidget(chart_frame, 1)

        ladder_frame = QFrame()
        ladder_frame.setFrameShape(QFrame.Box)
        ladder_layout = QVBoxLayout(ladder_frame)

        ladder_heading = QLabel("DEPTH LADDER")
        ladder_heading.setAlignment(Qt.AlignCenter)
        ladder_heading.setStyleSheet("color: #888888; font-size: 10px; padding: 4px")
        ladder_layout.addWidget(ladder_heading)        
        
        self._ask_row_labels: list[tuple[QLabel, QLabel]] = []
        for _ in range(8):
            row, price_label, size_label = self._make_ladder_row("#E74C3C")
            ladder_layout.addLayout(row)
            self._ask_row_labels.append((price_label, size_label))

        self._ladder_spread_label = QLabel("")
        self._ladder_spread_label.setAlignment(Qt.AlignCenter)
        self._ladder_spread_label.setStyleSheet("color: #888888; font-size: 11px; padding: 4px;")
        ladder_layout.addWidget(self._ladder_spread_label)

        self._bid_row_labels: list[tuple[QLabel, QLabel]] = []
        for _ in range(8):
            row, price_label, size_label = self._make_ladder_row("#2ECC71")
            ladder_layout.addLayout(row)
            self._bid_row_labels.append((price_label, size_label))


        depth_frame = QFrame()
        depth_frame.setFrameShape(QFrame.Box)
        depth_layout = QVBoxLayout(depth_frame)

        depth_heading = QLabel("CUMULATIVE MARKET DEPTH")
        depth_heading.setAlignment(Qt.AlignCenter)
        depth_heading.setStyleSheet("color: #888888; font-size: 10px; padding: 4px;")
        depth_layout.addWidget(depth_heading)

        self._depth_plot = pg.PlotWidget()
        self._depth_plot.setBackground("#141414")
        self._depth_plot.showGrid(x=False, y=True, alpha=0.15)
        self._bid_depth_curve = self._depth_plot.plot(
            pen=pg.mkPen("#2ECC71", width=1.5), fillLevel=0, brush=pg.mkBrush(46, 204, 113, 60)
        )
        self._ask_depth_curve = self._depth_plot.plot(
            pen=pg.mkPen("#E74C3C", width=1.5), fillLevel=0, brush=pg.mkBrush(231, 76, 60, 60)
        )
        self._depth_plot.setMouseEnabled(x=False, y=False)
        self._depth_plot.getViewBox().setDefaultPadding(0.05)
        self._depth_plot.getViewBox().disableAutoRange()
        depth_layout.addWidget(self._depth_plot)

        depth_row = QHBoxLayout()
        depth_row.addWidget(ladder_frame, 3)
        depth_row.addWidget(depth_frame, 7)
        outer_layout.addLayout(depth_row)

        feed_log_frame = QFrame()
        feed_log_frame.setFrameShape(QFrame.Box)
        feed_log_layout = QVBoxLayout(feed_log_frame)

        feed_log_heading = QLabel("FEED LOG")
        feed_log_heading.setAlignment(Qt.AlignCenter)
        feed_log_heading.setStyleSheet("color: #888888; font-size: 10px; padding: 4px;")
        feed_log_layout.addWidget(feed_log_heading)

        self._feed_log_widget = QListWidget()
        self._feed_log_widget.setStyleSheet("font-family: monospace; font-size: 11px;")
        feed_log_layout.addWidget(self._feed_log_widget)

        diagnostics_frame = QFrame()
        diagnostics_frame.setFrameShape(QFrame.Box)
        diagnostics_layout = QVBoxLayout(diagnostics_frame)

        diagnostics_heading = QLabel("CONNECTION DIAGNOSTICS")
        diagnostics_heading.setAlignment(Qt.AlignCenter)
        diagnostics_heading.setStyleSheet("color: #888888; font-size: 10px; padding: 4px;")
        diagnostics_layout.addWidget(diagnostics_heading)

        diagnostics_grid = QGridLayout()

        self._diagnostics_defs = [
            ("status", "Status"),
            ("connected_since", "Connected"),
            ("reconnects", "Reconnects"),
            ("sequence_gaps", "Sequence Gaps"),
        ]

        self._diagnostics_labels: dict[str, QLabel] = {}
        for col, (key, label_text) in enumerate(self._diagnostics_defs):
            label = QLabel(label_text)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("color: #888888; font-size: 10px;")
            diagnostics_grid.addWidget(label, 0, col)

            value = QLabel("-")
            value.setAlignment(Qt.AlignCenter)
            value.setStyleSheet("font-size: 14px; font-weight: 600;")
            diagnostics_grid.addWidget(value, 1, col)
            self._diagnostics_labels[key] = value

        diagnostics_layout.addLayout(diagnostics_grid)
        diagnostics_layout.addStretch()

        bottom_row = QHBoxLayout()
        bottom_row.addWidget(feed_log_frame, 2)
        bottom_row.addWidget(diagnostics_frame, 1)
        outer_layout.addLayout(bottom_row)
        self._tab_group.buttonClicked.connect(self._on_tab_clicked)
        self._interval_group.buttonClicked.connect(self._on_interval_clicked)

        self._thread = LOBFeedThread()
        self._thread.data_updated.connect(self._on_data)
        self._thread.tick_received.connect(self._on_tick)
        self._thread.connection_event.connect(self._on_connection_event)
        self._thread.start()
        self._fetch_candles()

        self._diagnostics_timer = QTimer(widget)
        self._diagnostics_timer.timeout.connect(self._refresh_diagnostics)
        self._diagnostics_timer.start(1000)

        self._depth_refit_timer = QTimer(widget)
        self._depth_refit_timer.timeout.connect(self._periodic_depth_refit)
        self._depth_refit_timer.start(7000)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setWidget(widget)
        return scroll_area