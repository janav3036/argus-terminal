import tempfile
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTableWidget, QTableWidgetItem, QFrame, QHeaderView
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from core.base_module import ArgusModule
from modules.rates.curve_worker import CurveWorker
from modules.rates.curve_chart import build_curve_html


class RatesModule(ArgusModule):
    """Wraps stochastic Interest Rate models as Argus Module"""

    def __init__(self):
        self._result = None
        self._worker : CurveWorker | None = None

    def get_sidebar_label(self):
        return "Rates"

    def get_status_preview(self):
        if self._result is None:
            return "Not Calibrated"
        return f"HW RMSE {self._result.hw_rmse_bps:.1f} bps"

    def build_widget(self) -> QWidget:
        widget = QWidget()
        outer_layout = QVBoxLayout(widget)

        heading = QLabel("RATES")
        heading.setAlignment(Qt.AlignCenter)
        heading.setStyleSheet("font-size: 16px; font-weight: bold; padding: 6px;")
        outer_layout.addWidget(heading)

        description_frame = QFrame()
        description_frame.setFrameShape(QFrame.Box)
        description_layout = QVBoxLayout(description_frame)
        description = QLabel(
            "Fits Vasicek, CIR, and Hull-White short-rate models to the Indian "
            "G-Sec curve and compares each against the market."
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

        self._curve_view = QWebEngineView()
        chart_layout.addWidget(self._curve_view)

        middle_row.addWidget(chart_frame, 3)

        right_col = QVBoxLayout()
        middle_row.addLayout(right_col, 2)

        controls_frame = QFrame()
        controls_frame.setFrameShape(QFrame.Box)
        controls_layout = QVBoxLayout(controls_frame)

        self._calibrate_btn = QPushButton("Calibrate")
        self._calibrate_btn.clicked.connect(self._on_calibrate_clicked)
        controls_layout.addWidget(self._calibrate_btn)

        self._status_label = QLabel("Not Calibrated")
        controls_layout.addWidget(self._status_label)

        right_col.addWidget(controls_frame, 1)

        params_frame = QFrame()
        params_frame.setFrameShape(QFrame.Box)
        params_layout = QVBoxLayout(params_frame)
        self._params_table = QTableWidget()
        self._params_table.setColumnCount(5)
        self._params_table.setHorizontalHeaderLabels(
            ["Model", "kappa/a", "theta", "sigma", "AIC"]
        )
        self._params_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        params_layout.addWidget(self._params_table)
        right_col.addWidget(params_frame, 2)

        return widget

    def _on_calibrate_clicked(self) -> None:
        self._calibrate_btn.setEnabled(False)
        self._status_label.setText("Calibrating...")

        self._worker = CurveWorker()
        self._worker.finished_curve.connect(self._on_curve_finished)
        self._worker.failed.connect(self._on_curve_failed)
        self._worker.start()

    def _on_curve_finished(self, result) -> None:
        self._result = result
        self._calibrate_btn.setEnabled(True)
        self._status_label.setText("Done")

        rows = [
            ("Vasicek", result.vas_params["kappa"], result.vas_params["theta"],
             result.vas_params["sigma"], result.vas_params["aic"]),
            ("CIR", result.cir_params["kappa"], result.cir_params["theta"],
             result.cir_params["sigma"], result.cir_params["aic"]),
            ("Hull-White", result.hw_a, None, result.hw_sigma, None),
        ]
        self._params_table.setRowCount(len(rows))
        for row, (name, kappa, theta, sigma, aic) in enumerate(rows):
            values = [
                name,
                f"{kappa:.4f}",
                f"{theta:.4f}" if theta is not None else "-",
                f"{sigma:.4f}",
                f"{aic:.2f}" if aic is not None else "-",
            ]
            for col, text in enumerate(values):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                self._params_table.setItem(row, col, item)

        html = build_curve_html(result)
        curve_path = Path(tempfile.gettempdir()) / f"argus_rates_curve_{id(self)}.html"
        curve_path.write_text(html, encoding="utf-8")
        self._curve_view.setUrl(QUrl.fromLocalFile(str(curve_path)))

    def _on_curve_failed(self, message: str) -> None:
        self._calibrate_btn.setEnabled(True)
        self._status_label.setText(f"Calibration Failed: {message}")
