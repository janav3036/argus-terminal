import asyncio
from core.base_thread import ArgusDataThread
from modules.order_book.bybit_bridge import (
    INSTRUMENTS,
    OrderBook,
    compute_features,
    BybitWebSocketClient
)

class LOBFeedThread(ArgusDataThread):
    """Streams order book + microstructure features for all Bybit instruments"""

    def __init__(self):
        super().__init__()
        self._books: dict[str, OrderBook] = {symbol: OrderBook() for symbol in INSTRUMENTS}
        self._client: BybitWebSocketClient | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._connected = False

    def run(self) -> None:
        asyncio.run(self._stream())

    async def _stream(self) -> None:
        self._loop = asyncio.get_running_loop()
        self._client = BybitWebSocketClient(self._on_rows)
        await self._client.run()

    async def _on_rows(self, rows: list[dict]) -> None:
        if not self._connected:
            self._connected = True
            self.status_changed.emit("live")
        
        touched = set()
        for row in rows:
            book = self._books[row["symbol"]]
            book.apply(row)
            touched.add(row["symbol"])

        for symbol in touched:
            features = compute_features(self._books[symbol])
            self.data_updated.emit({"symbol": symbol, **features})

    def stop(self) -> None:
        if self._client is not None and self._loop is not None:
            asyncio.run_coroutine_threadsafe(self._client.close(), self._loop)
