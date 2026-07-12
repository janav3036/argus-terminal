from PySide6.QtCore import Qt, QDateTime
from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QDateTimeEdit
from PySide6.QtWebEngineWidgets import QWebEngineView

from core.base_module import ArgusModule
from modules.volatility_lab.calibration_worker import CalibrationWorker
from modules.volatility_lab.smile_chart import build_smile_html

class VolatilityLabModule(ArgusModule):
    """Wraps Heston Calibration Engine as Argus Module"""

    def __init__(self):
        self._data = None
        self._result = None
        self._worker: CalibrationWorker | None = None

    def get_sidebar_label(self) -> str:
        return "Volatility Lab"

    def get_status_preview(self) -> str:
        if self._result is None:
            return "Not Calibrated"
        status = "OK" if self._result.success else "FAILED"
        return f"ATM IV - RMSE {self._result.rmse:.4f} ({status})" 
    
    def build_widget(self) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self._snapshot_picker = QDateTimeEdit()
        self._snapshot_picker.setCalendarPopup(True)
        self._snapshot_picker.setDisplayFormat("yyyy-MM-dd HH:mm")
        self._snapshot_picker.setMinimumDateTime(QDateTime(2021, 4, 1, 9, 15, 0))
        self._snapshot_picker.setMaximumDateTime(QDateTime(2026, 4, 9, 13, 9, 0))
        self._snapshot_picker.setDateTime(QDateTime(2026, 4, 9, 13, 9, 0))
        layout.addWidget(self._snapshot_picker)

        self._recalibrate_btn = QPushButton("Recalibrate")
        self._recalibrate_btn.clicked.connect(self._on_recalibrate_clicked)
        layout.addWidget(self._recalibrate_btn)

        self._params_label = QLabel("Not Calibrated")
        layout.addWidget(self._params_label)

        self._chart_view = QWebEngineView()
        layout.addWidget(self._chart_view)

        return widget
    
    def _on_recalibrate_clicked(self) -> None:
        self._recalibrate_btn.setEnabled(False)
        self._params_label.setText("Calibrating...")

        snapshot_dt = self._snapshot_picker.dateTime().toString(Qt.ISODate)
        self._worker = CalibrationWorker(snapshot_dt=snapshot_dt)
        self._worker.finished_calibration.connect(self._on_calibration_finished)
        self._worker.failed.connect(self._on_calibration_failed)
        self._worker.start()

    def _on_calibration_finished(self, data, result) -> None:
        self._data = data
        self._result = result
        self._recalibrate_btn.setEnabled(True)
        
        params = result.params
        self._params_label.setText(
            f"kappa={params.kappa:.4f} theta={params.theta:.4f}  "
            f"sigma={params.sigma:.4f}  rho={params.rho:.4f}  v0={params.v0:.4f} "
            f"RMSE={result.rmse:.4f}"
        )

        html = build_smile_html(params, data)
        self._chart_view.setHtml(html)

    def _on_calibration_failed(self, message: str) -> None:
        self._recalibrate_btn.setEnabled(True)
        self._params_label.setText(f"Calibration failed: {message}")