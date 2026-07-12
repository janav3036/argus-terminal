import yfinance as yf
from core.base_thread import ArgusDataThread

from datetime import datetime, time
from zoneinfo import ZoneInfo

MARKET_TZ = ZoneInfo("Asia/Kolkata")
MARKET_OPEN = time(9,15)
MARKET_CLOSE = time(15, 30)

def _is_market_open() -> bool:
    now = datetime.now(MARKET_TZ)
    if now.weekday() >=5:
        return False
    return MARKET_OPEN <= now.time() <= MARKET_CLOSE

class YFinanceFeedThread(ArgusDataThread):
    """Polls yfinance every 5 seconds for the top bar market strip"""

    TICKERS = {
        "NIFTY 50": "^NSEI",
        "NIFTY Bank": "^NSEBANK",
        "India VIX": "^INDIAVIX",
        "SENSEX": "^BSESN",
        "INR/USD": "INR=X",
        "Gold": "GC=F",
        "Crude": "CL=F",
    }
    POLL_SECONDS = 5

    def run(self) -> None:
        while not self.isInterruptionRequested():
            try:
                payload = {}
                for name, symbol in self.TICKERS.items():
                    if self.isInterruptionRequested():
                        return
                    info = yf.Ticker(symbol).fast_info
                    price = info.last_price
                    prev_close = info.previous_close
                    change = price - prev_close
                    pct_change = (change/prev_close) * 100
                    payload[name] = {
                        "price": price,
                        "change": change,
                        "pct_change": pct_change,
                    }
                self.data_updated.emit({
                    "market_open": _is_market_open(),
                    "instruments": payload,
                })
                self.status_changed.emit("live")
            except Exception:
                self.status_changed.emit("disconnected")
            for _ in range(self.POLL_SECONDS * 10):
                if self.isInterruptionRequested():
                    return
                self.msleep(100)