import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel

class _InstrumentRow(QWidget):
    def __init__(self, label: str, parent: QWidget | None = None):
        super().__init__(parent)

        self._price_label = QLabel("--")
        self._change_label = QLabel("--")

        top_row = QHBoxLayout()
        top_row.addWidget(QLabel(label))
        top_row.addStretch()
        top_row.addWidget(self._price_label)
        top_row.addWidget(self._change_label)

        self._sparkline = pg.PlotWidget()
        self._sparkline.setBackground(None)
        self._sparkline.setFixedHeight(32)
        self._sparkline.hideAxis("bottom")
        self._sparkline.hideAxis("left")
        self._sparkline.setMouseEnabled(x=False, y=False)
        self._sparkline.setMenuEnabled(False)
        self._curve = self._sparkline.plot([], [])

        layout = QVBoxLayout(self)
        layout.addLayout(top_row)
        layout.addWidget(self._sparkline)

    def update_data(self, price: float, pct_change: float, sparkline: list[float]) -> None:
        self._price_label.setText(f"{price:,.2f}")
        color = "#2ECC71" if pct_change>=0 else "#E74C3C"
        sign = "+" if pct_change>=0 else ""
        self._change_label.setText(f"{sign}{pct_change:.2f}%")
        self._change_label.setStyleSheet(f"color: {color}")
        self._curve.setData(list(range(len(sparkline))), sparkline, pen=pg.mkPen(color, width=1.5))

class FxCommoditiesPanel(QWidget):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)

        self._rows = {}
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("FX & Commodities"))
        for label in ("INR/USD", "Gold", "Crude"):
            row = _InstrumentRow(label)
            self._rows[label] = row
            layout.addWidget(row)

    def update_data(self, payload: dict) -> None:
        for label, data in payload.items():
            if label in self._rows:
                self._rows[label].update_data(data["price"], data["pct_change"], data["sparkline"])