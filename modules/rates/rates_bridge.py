from pathlib import Path
from core.external_import import load_external_modules

INTEREST_RATE_ROOT = Path.home() / "Programs" / "InterestRate"

_mods = load_external_modules(
    INTEREST_RATE_ROOT,
    [
        "models.vasicek",
        "models.cir",
        "calibration.vasicek_calibrate",
        "calibration.cir_calibrate",
        "calibration.hull_white_calibrate",
        "pricing.yield_curve",
        "data.rbi_loader",
    ],
)

vasicek_yield = _mods["models.vasicek"].vasicek_yield
cir_yield = _mods["models.cir"].cir_yield
calibrate_vasicek = _mods["calibration.vasicek_calibrate"].calibrate_vasicek
calibrate_cir = _mods["calibration.cir_calibrate"].calibrate_cir
calibrate_hull_white_historical = _mods["calibration.hull_white_calibrate"].calibrate_hull_white_historical
validate_yield_curve_fit = _mods["calibration.hull_white_calibrate"].validate_yield_curve_fit
fit_nelson_siegel = _mods["pricing.yield_curve"].fit_nelson_siegel
nelson_siegel_yield = _mods["pricing.yield_curve"].nelson_siegel_yield
load_cached_yields = _mods["data.rbi_loader"].load_cached_yields
get_yield_snapshot = _mods["data.rbi_loader"].get_yield_snapshot
TENORS = _mods["data.rbi_loader"].TENORS
TENOR_COLS = _mods["data.rbi_loader"].TENOR_COLS