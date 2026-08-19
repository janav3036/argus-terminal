from core.base_module import ArgusModule
from modules.volatility_lab.module import VolatilityLabModule
from modules.order_book.module import OrderBookModule
from modules.rates.module import RatesModule
from modules.options_pricer.module import OptionsPricerModule
from modules.vol_regime.module import VolRegimeModule
from modules.yield_pca.module import YieldPCAModule
from modules.risk_engine.module import RiskEngineModule
from modules.factor_analyzer.module import FactorAnalyzerModule

MODULES: list[ArgusModule] = [
    VolatilityLabModule(),
    OrderBookModule(),
    RatesModule(),
    OptionsPricerModule(),
    VolRegimeModule(),
    YieldPCAModule(),
    RiskEngineModule(),
    FactorAnalyzerModule(),
]
