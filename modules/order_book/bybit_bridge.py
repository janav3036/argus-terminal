from pathlib import Path
from core.external_import import load_external_modules

LOB_ROOT = Path.home() / "Programs" / "Limit Order Book"

_mods = load_external_modules(
    LOB_ROOT, 
    [
        "config.settings",
        "replay.order_book",
        "features.microstructure",
        "recorder.bybit_ws",

    ]
)

INSTRUMENTS = _mods["config.settings"].INSTRUMENTS
OrderBook = _mods["replay.order_book"].OrderBook
compute_features = _mods["features.microstructure"].compute_features
BybitWebSocketClient = _mods["recorder.bybit_ws"].BybitWebSocketClient

