import yfinance as yf
from core.base_thread import ArgusDataThread

SECTOR_TICKERS = {
    "IT": "^CNXIT",
    "Banking": "^NSEBANK",
    "Financial Services": "NIFTY_FIN_SERVICE.NS",
    "FMCG": "^CNXFMCG",
    "Auto": "^CNXAUTO",
    "Pharma": "^CNXPHARMA",
    "Energy": "^CNXENERGY",
    "Metal": "^CNXMETAL",
    "Realty": "^CNXREALTY",
    "Media": "^CNXMEDIA",
}

SECTOR_WEIGHTS = {
    "Banking": 28,
    "IT": 13,
    "Energy": 12,
    "Financial Services": 10,
    "FMCG": 8,
    "Auto": 7,
    "Pharma": 4,
    "Metal": 4,
    "Realty": 1.5,
    "Media": 0.5,
}

POLL_SECONDS = 900

class SectorFeedThread(ArgusDataThread):
    def run(self):
        while not self.isInterruptionRequested():
            payload = {}
            any_success = False
            for label, ticker in SECTOR_TICKERS.items():
                try:
                    bars = yf.Ticker(ticker).history(period="1mo", interval="1d")
                    pct_change = (bars.Close.iloc[-1] - bars.Close.iloc[-2]) / bars.Close.iloc[-2] * 100
                    payload[label] = {
                        "pct_change": pct_change,
                        "weight": SECTOR_WEIGHTS[label]
                    }
                    any_success = True
                except Exception:
                    continue

            if payload:
                self.data_updated.emit(payload)
            self.status_changed.emit("live" if any_success else "disconnected")

            for _ in range(POLL_SECONDS * 10):
                if self.isInterruptionRequested():
                    return
                self.msleep(100)