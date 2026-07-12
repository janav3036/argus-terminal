from pathlib import Path
from core.external_import import load_external_modules

HESTON_SDE_ROOT = Path.home() / "Programs" / "heston_sde"

_mods = load_external_modules(
    HESTON_SDE_ROOT,
    [
        "models",
        "models.heston_fft",
        "models.black_scholes",
        "data.nse_loader",
        "calibration.calibrate",
    ],
)

HestonParams = _mods["models"].HestonParams
MarketData = _mods["models"].MarketData
CalibrationResult = _mods["models"].CalibrationResult
load_snapshot = _mods["data.nse_loader"].load_snapshot
calibrate = _mods["calibration.calibrate"].calibrate
carr_madan_price = _mods["models.heston_fft"].carr_madan_price
price_at_strikes = _mods["models.heston_fft"].price_at_strikes
implied_vol = _mods["models.black_scholes"].implied_vol

