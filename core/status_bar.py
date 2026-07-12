from PySide6.QtWidgets import QStatusBar, QLabel, QWidget

class StatusBar(QStatusBar):
    """Bottom status bar showing live / stale / disconnected state per data source"""

    SOURCES = ["Bybit WSS", "NSE Options", "RBI Curve", "yfinance"]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._labels: dict[str, QLabel] = {}

        for source in self.SOURCES:
            label = QLabel()
            self._labels[source] = label
            self.addPermanentWidget(label)
            self.set_status(source, "disconnected")

    def set_status(self, source: str, state: str) -> None:
        symbol = {"live": "●", "stale": "⚠", "disconnected": "●"}[state]
        color = {"live": "#3fbf5f", "stale": "#e0a030", "disconnected": "#c0392b"}[state]
        label = self._labels[source]
        label.setText(f"{source}: {symbol} {state.capitalize()}")
        label.setStyleSheet(f"color: {color}")