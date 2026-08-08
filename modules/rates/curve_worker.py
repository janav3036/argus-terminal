from dataclasses import dataclass 

import numpy as np
from PySide6.QtCore import QThread, Signal

from modules.rates.rates_bridge import (
    vasicek_yield, cir_yield,
    calibrate_vasicek, calibrate_cir,
    calibrate_hull_white_historical, validate_yield_curve_fit,
    fit_nelson_siegel, nelson_siegel_yield,
    load_cached_yields, get_yield_snapshot,
    TENORS, TENOR_COLS,
)

@dataclass 
class CurveResult:
    tenors: np.ndarray
    market_yields: np.ndarray
    vas_yields: np.ndarray
    cir_yields: np.ndarray
    hw_yields: np.ndarray
    vas_params: dict
    cir_params: dict
    hw_a: float
    hw_sigma: float
    vas_rmse_bps: float
    cir_rmse_bps: float
    hw_rmse_bps: float

def _rmse_bps(model_y: np.ndarray, market_y: np.ndarray) -> float:
    return float(np.sqrt(np.mean((model_y-market_y)**2))*10000)


class CurveWorker(QThread):

    finished_curve = Signal(object)
    failed = Signal(str)

    def run(self) -> None:
        try:
            df = load_cached_yields()
            rates = df["tenor_3m"].values

            snapshot = get_yield_snapshot(df)
            market_yields = snapshot[TENOR_COLS].values.astype(float)
            tenors = np.array(TENORS)

            ns_params = fit_nelson_siegel(tenors, market_yields)

            r0 = rates[-1]
            r0_hw = nelson_siegel_yield(1e-4, **ns_params)

            vas_params = calibrate_vasicek(rates)
            cir_params = calibrate_cir(rates)
            a, sigma_hw = calibrate_hull_white_historical(rates, dt=1 / 252)

            vas_yields = np.array([
                vasicek_yield(r0, vas_params["kappa"], vas_params["theta"], vas_params["sigma"], tau)
                for tau in tenors
            ])
            cir_yields = np.array([
                cir_yield(r0, cir_params["kappa"], cir_params["theta"], cir_params["sigma"], tau)
                for tau in tenors
            ])
            hw_df = validate_yield_curve_fit(a, sigma_hw, r0_hw, tenors, market_yields, ns_params)
            hw_yields = hw_df["model_yield"].values

            result = CurveResult(
                tenors=tenors,
                market_yields=market_yields,
                vas_yields=vas_yields,
                cir_yields=cir_yields,
                hw_yields=hw_yields,
                vas_params=vas_params,
                cir_params=cir_params,
                hw_a=a,
                hw_sigma=sigma_hw,
                vas_rmse_bps=_rmse_bps(vas_yields, market_yields),
                cir_rmse_bps=_rmse_bps(cir_yields, market_yields),
                hw_rmse_bps=_rmse_bps(hw_yields, market_yields),
            )

        except Exception as e:
            self.failed.emit(str(e))
            return
        self.finished_curve.emit(result)