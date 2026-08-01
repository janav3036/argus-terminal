import yfinance as yf
from core.base_thread import ArgusDataThread

SYMBOLS = {
    "NIFTY 50": "^NSEI",
    "RELIANCE": "RELIANCE.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "INFY": "INFY.NS",

}
POLL_SECONDS = 900
CANDLE_HISTORY_LEN = 90

class WatchlistFeedThread(ArgusDataThread):
    def run(self):
        while not self.isInterruptionRequested():
            all_candles = {}
            any_success = False
            for label, ticker in SYMBOLS.items():
                try: 
                    bars = yf.Ticker(ticker).history(period="3mo", interval="1d")
                    bars = bars.tail(CANDLE_HISTORY_LEN)
                    all_candles[label] = [
                        (i, row.Open, row.High, row.Low, row.Close)
                        for i, row in enumerate(bars.itertuples())
                    ]
                    any_success = True
                except Exception:
                    continue

            if all_candles:
                self.data_updated.emit(all_candles)
            self.status_changed.emit("live" if any_success else "disconnected")
            for _ in range(POLL_SECONDS * 10):
                if self.isInterruptionRequested():
                    return
                self.msleep(100)