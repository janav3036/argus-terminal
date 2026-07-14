from core.base_module import ArgusModule
from modules.volatility_lab.module import VolatilityLabModule
from modules.order_book.module import OrderBookModule

MODULES: list[ArgusModule] = [
    VolatilityLabModule(),
    OrderBookModule(),
]
