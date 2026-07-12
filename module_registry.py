from core.base_module import ArgusModule
from modules.volatility_lab.module import VolatilityLabModule

MODULES: list[ArgusModule] = [
    VolatilityLabModule(),
]
