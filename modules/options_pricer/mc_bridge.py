from pathlib import Path
from core.external_import import load_external_modules

MONTE_CARLO_ROOT = Path.home() / "Programs" / "MonteCarlo"

_mods = load_external_modules(
    MONTE_CARLO_ROOT,
    [
        "models.gbm",
        "models.heston_mc",
        "payoffs.european",
        "payoffs.asian",
    ],
)

simulate_gbm = _mods["models.gbm"].simulate_gbm
simulate_heston = _mods["models.heston_mc"].simulate_heston
european_call = _mods["payoffs.european"].european_call
european_put = _mods["payoffs.european"].european_put
arithmetic_asian_call = _mods["payoffs.asian"].arithmetic_asian_call
arithmetic_asian_put = _mods["payoffs.asian"].arithmetic_asian_put