import tempfile
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, QDate
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QCalendarWidget, QComboBox, QTableWidget, QTableWidgetItem,
    QFrame, QHeaderView
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from core.base_module import ArgusModule
from modules.volatility_lab.calibration_worker import CalibrationWorker
from modules.volatility_lab.smile_chart import build_smile_html, compute_model_ivs

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
        outer_layout = QVBoxLayout(widget)

        heading = QLabel("VOLATILITY LAB")
        heading.setAlignment(Qt.AlignCenter)
        heading.setStyleSheet("font-size: 16px; font-weight: bold; padding: 6px;")
        outer_layout.addWidget(heading)

        description_frame = QFrame()
        description_frame.setFrameShape(QFrame.Box)
        description_layout = QVBoxLayout(description_frame)
        description = QLabel(
            "Calibrates the Heston stochastic volatility model to a NIFTY options snapshot "
            "and compares the fitted implied volatility smile against the market."
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

        self._smile_view = QWebEngineView()
        chart_layout.addWidget(self._smile_view)

        middle_row.addWidget(chart_frame, 3)

        right_col = QVBoxLayout()
        middle_row.addLayout(right_col, 2)

        date_frame = QFrame()
        date_frame.setFrameShape(QFrame.Box)
        date_outer_layout = QVBoxLayout(date_frame)

        date_top_row = QHBoxLayout()
        date_outer_layout.addLayout(date_top_row)

        self._calendar = QCalendarWidget()
        self._calendar.setMinimumDate(QDate(2021, 4, 1))
        self._calendar.setMaximumDate(QDate(2026, 4, 9))
        self._calendar.setSelectedDate(QDate(2026, 4, 9))
        self._calendar.setGridVisible(True)
        self._calendar.setStyleSheet("""
            QCalendarWidget {
                background-color: #1A1A1A;
                color: #E8E8E8;
            }
        """)
        date_top_row.addWidget(self._calendar, 2)

        time_col = QVBoxLayout()
        date_top_row.addLayout(time_col, 1)

        time_row = QHBoxLayout()
        combo_style = """
            QComboBox {
                background-color: #1A1A1A;
                color: #E8E8E8;
                border: 1px solid #444;
                border-radius: 4px;
                padding: 4px 8px;
            }
        """

        self._hour_picker = QComboBox()
        self._hour_picker.setEditable(False)
        for hour in range(24):
            self._hour_picker.addItem(f"{hour:02d}")
        self._hour_picker.setCurrentText("13")
        self._hour_picker.setStyleSheet(combo_style)
        time_row.addWidget(self._hour_picker)

        self._minute_picker = QComboBox()
        self._minute_picker.setEditable(False)
        for minute in (0, 15, 30, 45):
            self._minute_picker.addItem(f"{minute:02d}")
        self._minute_picker.setCurrentText("00")
        self._minute_picker.setStyleSheet(combo_style)
        time_row.addWidget(self._minute_picker)

        time_col.addLayout(time_row)

        self._recalibrate_btn = QPushButton("Calibrate")
        self._recalibrate_btn.clicked.connect(self._on_recalibrate_clicked)
        time_col.addWidget(self._recalibrate_btn)

        self._status_label = QLabel("Not Calibrated")
        date_outer_layout.addWidget(self._status_label)

        right_col.addWidget(date_frame, 1)

        results_frame = QFrame()
        results_frame.setFrameShape(QFrame.Box)
        results_layout = QVBoxLayout(results_frame)
        self._results_label = QLabel("")
        self._results_label.setWordWrap(True)
        results_layout.addWidget(self._results_label)
        right_col.addWidget(results_frame, 1)

        raw_frame = QFrame()
        raw_frame.setFrameShape(QFrame.Box)
        raw_layout = QVBoxLayout(raw_frame)
        self._raw_table = QTableWidget()
        self._raw_table.setColumnCount(4)
        self._raw_table.setHorizontalHeaderLabels(["Strike", "Market IV (%)", "Model IV (%)", "Diff (%)"])
        self._raw_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        raw_layout.addWidget(self._raw_table)
        outer_layout.addWidget(raw_frame, 1)

        return widget
    
    def _on_recalibrate_clicked(self) -> None:
        self._recalibrate_btn.setEnabled(False)
        self._status_label.setText("Calibrating...")

        date_str = self._calendar.selectedDate().toString(Qt.ISODate)
        hour = self._hour_picker.currentText()
        minute = self._minute_picker.currentText()
        snapshot_dt = f"{date_str}T{hour}:{minute}:00"
        self._worker = CalibrationWorker(snapshot_dt=snapshot_dt)
        self._worker.finished_calibration.connect(self._on_calibration_finished)
        self._worker.failed.connect(self._on_calibration_failed)
        self._worker.start()

    def _on_calibration_finished(self, data, result) -> None:
        self._data = data
        self._result = result
        self._recalibrate_btn.setEnabled(True)
        
        params = result.params
        self._status_label.setText("Done")
        self._results_label.setText(
            f"kappa (mean reversion speed): {params.kappa:.4f}\n"
            f"theta (long-run variance): {params.theta:.4f}\n"
            f"sigma (vol of vol): {params.sigma:.4f}\n"
            f"rho (correlation): {params.rho:.4f}\n"
            f"v0 (initial variance): {params.v0:.4f}\n"
            f"RMSE: {result.rmse:.4f}"
        )

        model_ivs = compute_model_ivs(params, data)
        self._raw_table.setRowCount(len(data.strikes))
        for row, (strike, market_iv, model_iv) in enumerate(zip(data.strikes, data.market_ivs[0], model_ivs)):
            diff = (model_iv - market_iv) * 100
            for col, text in enumerate([f"{strike:.2f}", f"{market_iv * 100:.2f}", f"{model_iv * 100:.2f}", f"{diff:.2f}"]):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                self._raw_table.setItem(row, col, item)

        html = build_smile_html(params, data, model_ivs=model_ivs)
        smile_path = Path(tempfile.gettempdir()) / f"argus_vol_lab_smile_{id(self)}.html"
        smile_path.write_text(html, encoding="utf-8")
        self._smile_view.setUrl(QUrl.fromLocalFile(str(smile_path)))

    def _on_calibration_failed(self, message: str) -> None:
        self._recalibrate_btn.setEnabled(True)
        self._status_label.setText(f"Calibration failed: {message}")

    