from core.base_module import ArgusModule
from modules.volatility_lab.module import VolatilityLabModule
from modules.order_book.module import OrderBookModule
from modules.rates.module import RatesModule
from modules.options_pricer.module import OptionsPricerModule

MODULES: list[ArgusModule] = [
    VolatilityLabModule(),
    OrderBookModule(),
    RatesModule(),
    OptionsPricerModule(),
]
