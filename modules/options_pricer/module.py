import tempfile
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFormLayout, QPushButton,
    QLabel, QLineEdit, QComboBox, QFrame
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from core.base_module import ArgusModule 
from modules.options_pricer.pricing_worker import PricingWorker
from modules.options_pricer.convergence_chart import build_convergence_html

class OptionsPricerModule(ArgusModule):

    def __init__(self):
        self._result = None
        self._worker : PricingWorker | None = None

    def get_sidebar_label(self):
        return "Options Pricer"

    def get_status_preview(self):
        if self._result is None:
            return "No pricing run"
        return f"Last: {self._result.price:.2f} ± {self._result.stderr:.2f}"

    def build_widget(self) -> QWidget:
        widget = QWidget()
        outer_layout = QVBoxLayout(widget)

        heading = QLabel("OPTIONS PRICER")
        heading.setAlignment(Qt.AlignCenter)
        heading.setStyleSheet("font-size: 16px; font-weight: bold; padding: 6px;")
        outer_layout.addWidget(heading)

        description_frame = QFrame()
        description_frame.setFrameShape(QFrame.Box)
        description_layout = QVBoxLayout(description_frame)
        description = QLabel(
            "Monte Carlo pricer for European and Asian options under GBM or "
            "Heston dynamics, with live convergence tracking."
        )
        description.setWordWrap(True)
        description.setAlignment(Qt.AlignCenter)
        description_layout.addWidget(description)
        outer_layout.addWidget(description_frame)

        middle_row = QHBoxLayout()
        outer_layout.addLayout(middle_row, 3)

        chart_frame = QFrame()
        chart_frame.setFrameShape(QFrame.Box)
        chart_layout = QVBoxLayout(chart_frame)

        self._convergence_view = QWebEngineView()
        chart_layout.addWidget(self._convergence_view)

        middle_row.addWidget(chart_frame, 3)

        right_col = QVBoxLayout()
        middle_row.addLayout(right_col, 2)

        controls_frame = QFrame()
        controls_frame.setFrameShape(QFrame.Box)
        form = QFormLayout(controls_frame)

        self._model_combo = QComboBox()
        self._model_combo.addItems(["GBM", "Heston"])
        form.addRow("Model", self._model_combo)

        self._option_combo = QComboBox()
        self._option_combo.addItems(["European Call", "European Put", "Asian Call", "Asian Put"])
        form.addRow("Option Type", self._option_combo)

        self._s0_input = QLineEdit("100")
        form.addRow("Spot (S0)", self._s0_input)

        self._k_input = QLineEdit("100")
        form.addRow("Strike (K)", self._k_input)

        self._r_input = QLineEdit("0.05")
        form.addRow("Rate (r)", self._r_input)

        self._t_input = QLineEdit("1.0")
        form.addRow("Maturity (T, yrs)", self._t_input)

        self._n_paths_input = QLineEdit("20000")
        form.addRow("N paths", self._n_paths_input)

        self._sigma_input = QLineEdit("0.20")
        form.addRow("GBM sigma", self._sigma_input)

        self._v0_input = QLineEdit("0.04")
        form.addRow("Heston v0", self._v0_input)

        self._kappa_input = QLineEdit("2.0")
        form.addRow("Heston kappa", self._kappa_input)

        self._theta_input = QLineEdit("0.04")
        form.addRow("Heston theta", self._theta_input)

        self._sigma_v_input = QLineEdit("0.30")
        form.addRow("Heston sigma_v", self._sigma_v_input)

        self._rho_input = QLineEdit("-0.70")
        form.addRow("Heston rho", self._rho_input)

        right_col.addWidget(controls_frame, 3)

        button_frame = QFrame()
        button_frame.setFrameShape(QFrame.Box)
        button_layout = QVBoxLayout(button_frame)

        self._price_btn = QPushButton("Price")
        self._price_btn.clicked.connect(self._on_price_clicked)
        button_layout.addWidget(self._price_btn)

        self._status_label = QLabel("Not priced")
        button_layout.addWidget(self._status_label)

        self._results_label = QLabel("")
        self._results_label.setWordWrap(True)
        button_layout.addWidget(self._results_label)

        right_col.addWidget(button_frame, 2)

        return widget

    def _on_price_clicked(self) -> None:
        self._price_btn.setEnabled(False)
        self._status_label.setText("Pricing...")

        params = {
            "S0": float(self._s0_input.text()),
            "K": float(self._k_input.text()),
            "r": float(self._r_input.text()),
            "T": float(self._t_input.text()),
            "sigma": float(self._sigma_input.text()),
            "v0": float(self._v0_input.text()),
            "kappa": float(self._kappa_input.text()),
            "theta": float(self._theta_input.text()),
            "sigma_v": float(self._sigma_v_input.text()),
            "rho": float(self._rho_input.text()),
        }
        n_paths = int(self._n_paths_input.text())

        self._worker = PricingWorker(
            self._model_combo.currentText(),
            self._option_combo.currentText(),
            params,
            n_paths,
        )
        self._worker.finished_pricing.connect(self._on_priced)
        self._worker.failed.connect(self._on_price_failed)
        self._worker.start()

    def _on_priced(self, result) -> None:
        self._result = result
        self._price_btn.setEnabled(True)
        self._status_label.setText("Done")

        self._results_label.setText(
            f"Price: {result.price:.4f}\n"
            f"Std. Error: {result.stderr:.4f}\n"
            f"95% CI: [{result.ci_low:.4f}, {result.ci_high:.4f}]\n"
            f"Runtime: {result.runtime_s:.2f}s"
        )

        html = build_convergence_html(result)
        chart_path = Path(tempfile.gettempdir()) / f"argus_options_convergence_{id(self)}.html"
        chart_path.write_text(html, encoding="utf-8")
        self._convergence_view.setUrl(QUrl.fromLocalFile(str(chart_path)))

    def _on_price_failed(self, message: str) -> None:
        self._price_btn.setEnabled(True)
        self._status_label.setText(f"Pricing failed: {message}")