from PySide6.QtWidgets import QWidget, QHBoxLayout, QLabel

class TopBar(QWidget):
    """Persistent live market strip across every page"""

    INSTRUMENTS = ["NIFTY 50", "NIFTY Bank", "India VIX", "SENSEX", "INR/USD", "Gold", "Crude"]

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self._labels: dict[str, QLabel] = {}

        layout = QHBoxLayout(self)
        for name in self.INSTRUMENTS:
            label = QLabel(f"{name} -")
            self._labels[name] = label 
            layout.addWidget(label)
    
    def update_data(self, payload: dict) -> None:
        market_open = payload["market_open"]
        for name, values in payload["instruments"].items():
            label = self._labels.get(name)
            if label is None:
                continue
            price = values["price"]
            change = values["change"]
            pct_change = values["pct_change"]
            if market_open:
                arrow = "▲" if change >= 0 else "▼"
                color = "#2ECC71" if change >= 0 else "#E74C3C"
            else:
                arrow = "•"
                color = "#E8E8E8"
            label.setText(f"{name}  {price:,.2f} {arrow} {pct_change:+.2f}%")
            label.setStyleSheet(f"color: {color};")
