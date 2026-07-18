import time 
import requests
from PySide6.QtCore import QThread, Signal

KLINE_URL = "https://api.bybit.com/v5/market/kline"

_INTERVAL_MAP = {
    60: "1",
    300: "5",
    900: "15", 
    3600: "60",
    14400: "240",
    86400: "D",
}

def fetch_klines(symbol: str, interval_seconds: int, limit: int = 300) -> list[dict]:
    """Fetch historical candles from Bybit, oldest first. Last entry is the currently forming candle"""
    interval = _INTERVAL_MAP[interval_seconds]
    response = requests.get(
        KLINE_URL,
        params={"category": "linear", "symbol": symbol, "interval": interval, "limit": limit},
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()
    if payload["retCode"] != 0:
        raise RuntimeError(payload["retMsg"])
    
    candles = []
    for start_ms, open_, high, low, close, *_ in reversed(payload["result"]["list"]):
        bucket = int(int(start_ms) / 1000 // interval_seconds)
        candles.append({
            "bucket": bucket,
            "open": float(open_),
            "high": float(high),
            "low": float(low),
            "close": float(close),
        })
    return candles

class KlineFetchWorker(QThread):
    """One shot fetch of historical candles for one symbol / interval"""

    finished_fetch = Signal(str, int, list)
    failed = Signal(str)
    def __init__(self, symbol: str, interval_seconds: int):
        super().__init__()
        self._symbol = symbol
        self._interval_seconds = interval_seconds

    def run(self) -> None:
        try: 
            candles = fetch_klines(self._symbol, self._interval_seconds)
        except Exception as e:
            self.failed.emit(str(e))
            return
        self.finished_fetch.emit(self._symbol, self._interval_seconds, candles)