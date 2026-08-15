from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QThread, Signal
from sklearn.decomposition import PCA

from modules.rates.rates_bridge import load_cached_yields, TENORS, TENOR_COLS

COMPONENT_LABELS = ["Level", "Slope", "Curvature"]

@dataclass 
class PCAResult: 
    tenors: np.ndarray
    explained_variance_ratio: np.ndarray
    loadings: np.ndarray
    factor_scores: np.ndarray
    dates: np.ndarray
    component_labels: list[str]
    current_curve: np.ndarray
    mean_curve: np.ndarray
    current_contributions: np.ndarray
    
class PCAWorker(QThread):
    finished_pca = Signal(object)
    failed = Signal(str)

    def run(self) -> None:
        try:
            df = load_cached_yields()
            tenors = np.array(TENORS)
            yields = df[TENOR_COLS].values.astype(float)

            changes = np.diff(yields, axis=0)
            dates = df["date"].values[1:]

            pca = PCA(n_components=3)
            factor_scores = pca.fit_transform(changes)
            loadings = pca.components_

            mean_curve = yields.mean(axis=0)
            current_curve = yields[-1]
            deviation = current_curve - mean_curve
            current_contributions = loadings @ deviation

            result = PCAResult(
                tenors=tenors,
                explained_variance_ratio=pca.explained_variance_ratio_,
                loadings=loadings,
                factor_scores=factor_scores,
                dates=dates,
                component_labels=COMPONENT_LABELS,
                current_curve=current_curve,
                mean_curve=mean_curve,
                current_contributions=current_contributions,
            )

        except Exception as e:
            self.failed.emit(str(e))
            return
        self.finished_pca.emit(result)
