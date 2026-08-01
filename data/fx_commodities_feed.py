import yfinance as yf
from core.base_thread import ArgusDataThread

TICKERS = {
    "INR/USD": "INR=X",
    "Gold": "GC=F",
    "Crude": "CL=F",
}

POLL_SECONDS = 900
SPARKLINE_LEN = 5

class FxCommoditiesFeedThread(ArgusDataThread):
    def run(self):
        while not self.isInterruptionRequested():
            payload = {}
            any_success = False
            for label, ticker in TICKERS.items():
                try:
                    bars = yf.Ticker(ticker).history(period="1mo", interval="1d")
                    bars = bars.tail(SPARKLINE_LEN)
                    closes = bars.Close.tolist()
                    price = closes[-1]
                    pct_change = (closes[-1] - closes[-2]) / closes[-2] * 100
                    payload[label] = {
                        "price": price,
                        "pct_change": pct_change,
                        "sparkline": closes
                    }
                    any_success = True
                except Exception:
                    continue

            if payload:
                self.data_updated.emit(payload)
            self.status_changed.emit("live" if any_success else "disconnected")

            for _ in range(POLL_SECONDS*10):
                if self.isInterruptionRequested():
                    return
                self.msleep(100)