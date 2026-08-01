import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QWidget

class _InstrumentRow(QWidget):
    def __init__(self, label: str, parent: QWidget | None = None):
        super().__init__(parent)

        self._name_label = QLabel(label)
        self._name_label.setStyleSheet("color: #888888; font-size: 11px;")

        self._price_label = QLabel("--")
        self._price_label.setStyleSheet("font-size: 15px; font-weight: 600;")
        self._change_label = QLabel("--")
        self._change_label.setStyleSheet("font-size: 12px;")

        self._sparkline = pg.PlotWidget()
        self._sparkline.setBackground(None)
        self._sparkline.setFixedSize(64, 26)
        self._sparkline.hideAxis("bottom")
        self._sparkline.hideAxis("left")
        self._sparkline.setMouseEnabled(x=False, y=False)
        self._sparkline.setMenuEnabled(False)
        self._curve = self._sparkline.plot([], [])

        value_row = QHBoxLayout()
        value_row.addWidget(self._price_label)
        value_row.addSpacing(8)
        value_row.addWidget(self._change_label)
        value_row.addStretch()
        value_row.addWidget(self._sparkline)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 6, 0, 6)
        layout.setSpacing(2)
        layout.addWidget(self._name_label)
        layout.addLayout(value_row)

    def update_data(self, price: float, pct_change: float, sparkline: list[float]) -> None:
        self._price_label.setText(f"{price:,.2f}")
        color = "#2ECC71" if pct_change >= 0 else "#E74C3C"
        sign = "+" if pct_change >= 0 else ""
        self._change_label.setText(f"{sign}{pct_change:.2f}%")
        self._change_label.setStyleSheet(f"color: {color}; font-size: 12px;")
        self._curve.setData(list(range(len(sparkline))), sparkline, pen=pg.mkPen(color, width=1.5))


def _make_divider() -> QWidget:
    divider = QWidget()
    divider.setFixedHeight(1)
    divider.setStyleSheet("background-color: #3A3A3A;")
    divider.setAttribute(Qt.WA_StyledBackground, True)
    return divider


class FxCommoditiesPanel(QFrame):
    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setFrameShape(QFrame.Shape.StyledPanel)

        title = QLabel("FX & Commodities")
        title.setStyleSheet("font-weight: 600;")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.addWidget(title)

        self._rows = {}
        labels = ("INR/USD", "Gold", "Crude")
        for i, label in enumerate(labels):
            if i > 0:
                layout.addWidget(_make_divider())
            row = _InstrumentRow(label)
            self._rows[label] = row
            layout.addWidget(row)

        layout.addStretch()

    def update_data(self, payload: dict) -> None:
        for label, data in payload.items():
            if label in self._rows:
                self._rows[label].update_data(data["price"], data["pct_change"], data["sparkline"])