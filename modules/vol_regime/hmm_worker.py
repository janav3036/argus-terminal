from dataclasses import dataclass

import numpy as np
import pandas as pd
import yfinance as yf
from hmmlearn.hmm import GaussianHMM
from PySide6.QtCore import QThread, Signal

NIFTY_TICKER = "^NSEI"
REALIZED_VOL_WINDOW = 30

STATE_LABELS = {
    2: ["Low Vol", "High Vol"],
    3: ["Low Vol", "Elevated Vol", "Crisis"],
}

@dataclass 
class RegimeResult:
    dates: np.ndarray
    price: np.ndarray
    vol: np.ndarray
    state_labels: np.ndarray
    label_order: list[str]
    current_label: str
    current_posterior: dict[str, float]
    transmat: np.ndarray

def _load_price_and_vol():
    hist = yf.Ticker(NIFTY_TICKER).history(period="10y")
    log_returns = np.log(hist["Close"]).diff()
    realized_vol = log_returns.rolling(REALIZED_VOL_WINDOW).std() * np.sqrt(252)
    df = pd.DataFrame({"price": hist["Close"], "vol": realized_vol}).dropna()
    return df.index.to_numpy(), df["price"].to_numpy(), df["vol"].to_numpy()


class HMMWorker(QThread):
    finished_regime = Signal(object)
    failed = Signal(str)

    def __init__(self, n_states=2, parent=None):
        super().__init__(parent)
        self.n_states = n_states

    def run(self):
        try:
            dates, price, vol = _load_price_and_vol()
            X = vol.reshape(-1, 1)

            model = GaussianHMM(n_components=self.n_states, covariance_type="diag", n_iter=1000, random_state=42)
            model.fit(X)
            raw_states = model.predict(X)

            order = np.argsort(model.means_.flatten())
            rank_of_raw = np.empty_like(order)
            rank_of_raw[order] = np.arange(self.n_states)
            label_order = STATE_LABELS[self.n_states]
            state_labels = np.array(label_order)[rank_of_raw[raw_states]]

            current_rank = rank_of_raw[raw_states[-1]]
            current_label = label_order[current_rank]

            posterior_raw = model.predict_proba(X)[-1]
            current_posterior = {
                label_order[rank_of_raw[raw]]: posterior_raw[raw]
                for raw in range(self.n_states)
            }

            transmat = model.transmat_[np.ix_(order, order)]

            result = RegimeResult(
                dates=dates,
                price=price,
                vol=vol,
                state_labels=state_labels,
                label_order=label_order,
                current_label=current_label,
                current_posterior=current_posterior,
                transmat=transmat,
            )
            self.finished_regime.emit(result)
        except Exception as e:
            self.failed.emit(str(e))

    