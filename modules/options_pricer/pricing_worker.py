from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QThread, Signal

from modules.options_pricer.mc_bridge import (
    simulate_gbm, simulate_heston,
    european_call, european_put,
    arithmetic_asian_call, arithmetic_asian_put,
)

@dataclass
class PricingResult:
    price: float
    stderr: float
    ci_low: float
    ci_high: float
    runtime_s: float
    checkpoint_ns: np.ndarray
    checkpoint_prices: np.ndarray
    checkpoint_ses: np.ndarray

def _checkpoints(n_paths: int, n_points: int = 25) -> np.ndarray:
    return np.unique(np.linspace(n_paths / n_points, n_paths, n_points).astype(int))

class PricingWorker(QThread):

    finished_pricing = Signal(object)
    failed = Signal(str)

    def __init__(self, model: str, option_type: str, params: dict, n_paths: int, n_steps: int = 100):
        super().__init__()
        self.model = model
        self.option_type = option_type
        self.params = params
        self.n_paths = n_paths
        self.n_steps = n_steps

    def _price(self, paths: np.ndarray) -> tuple[float, float]:
        K, r, T = self.params["K"], self.params["r"], self.params["T"]
        if self.option_type == "European Call":
            return european_call(paths, K, r, T)
        if self.option_type == "European Put":
            return european_put(paths, K, r, T)
        if self.option_type == "Asian Call":
            return arithmetic_asian_call(paths, K, r, T)
        if self.option_type == "Asian Put":
            return arithmetic_asian_put(paths, K, r, T)
        raise ValueError(f"Unknown option type: {self.option_type}")

    def run(self) -> None:
        import time
        start = time.perf_counter()
        try:
            p = self.params
            if self.model == "GBM":
                paths = simulate_gbm(p["S0"], p["r"], p["sigma"], p["T"], self.n_paths, self.n_steps, seed=42)
            elif self.model == "Heston":
                paths, _ = simulate_heston(p["S0"], p["r"], p["v0"], p["kappa"], p["theta"],
                                            p["sigma_v"], p["rho"], p["T"], self.n_paths, self.n_steps, seed=42)
            else:
                raise ValueError(f"Unknown model: {self.model}")

            price, se = self._price(paths)

            checkpoint_ns = _checkpoints(self.n_paths)
            checkpoint_prices = np.empty(len(checkpoint_ns))
            checkpoint_ses = np.empty(len(checkpoint_ns))
            for i, n in enumerate(checkpoint_ns):
                checkpoint_prices[i], checkpoint_ses[i] = self._price(paths[:n])

            result = PricingResult(
                price=price,
                stderr=se,
                ci_low=price - 1.96 * se,
                ci_high=price + 1.96 * se,
                runtime_s=time.perf_counter() - start,
                checkpoint_ns=checkpoint_ns,
                checkpoint_prices=checkpoint_prices,
                checkpoint_ses=checkpoint_ses,
            )
        except Exception as e:
            self.failed.emit(str(e))
            return
        self.finished_pricing.emit(result)