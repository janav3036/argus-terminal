from pathlib import Path
import tempfile

import numpy as np
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QDoubleSpinBox, QButtonGroup
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from core.base_module import ArgusModule
from modules.factor_analyzer.factor_worker import FactorWorker, FACTOR_NAMES
from modules.factor_analyzer.factor_chart import CHART_TABS

CHART_PLACEHOLDER_HTML = (
    "<html><body style='background:#0D0D0D; color:#888888; display:flex; "
    "align-items:center; justify-content:center; height:100vh; margin:0; "
    "font-family:sans-serif;'><p>Run the analysis to see this chart.</p></body></html>"
)

STATUS_PILL_STYLES = {
    "not_run": ("#888888", "rgba(136, 136, 136, 0.12)", "rgba(136, 136, 136, 0.4)"),
    "running": ("#2B5EA7", "rgba(43, 94, 167, 0.15)", "rgba(43, 94, 167, 0.45)"),
    "done": ("#2ECC71", "rgba(46, 204, 113, 0.12)", "rgba(46, 204, 113, 0.4)"),
    "failed": ("#E74C3C", "rgba(231, 76, 60, 0.12)", "rgba(231, 76, 60, 0.4)"),
}

class FactorAnalyzerModule(ArgusModule):

    def __init__(self):
        self._result = None
        self._worker: FactorWorker | None = None
        self._chart_paths: dict[str, Path] = {}

    def get_sidebar_label(self):
        return "Factor Analyzer"

    def get_status_preview(self):
        if self._result is None:
            return "Not Run"
        return f"R\u00b2: {self._result.r_squared:.2f}"

    def build_widget(self) -> QWidget:
        widget = QWidget()
        outer_layout = QVBoxLayout(widget)

        heading = QLabel("FACTOR ANALYZER")
        heading.setAlignment(Qt.AlignCenter)
        heading.setStyleSheet("font-size: 16px; font-weight: bold; padding: 6px;")
        outer_layout.addWidget(heading)

        body_row = QHBoxLayout()
        outer_layout.addLayout(body_row, 1)

        body_row.addLayout(self._build_chart_column(), 3)
        body_row.addLayout(self._build_data_column(), 2)

        return widget

    def _build_chart_column(self) -> QVBoxLayout:
        left_col = QVBoxLayout()

        tab_row = QHBoxLayout()
        self._chart_tab_group = QButtonGroup()
        self._chart_tab_group.setExclusive(True)
        for i, tab in enumerate(CHART_TABS):
            btn = QPushButton(tab["label"])
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            btn.setProperty("chart_key", tab["key"])
            btn.clicked.connect(self._on_chart_tab_clicked)
            self._chart_tab_group.addButton(btn)
            tab_row.addWidget(btn)
        left_col.addLayout(tab_row)

        chart_frame = QFrame()
        chart_frame.setFrameShape(QFrame.Box)
        chart_layout = QVBoxLayout(chart_frame)
        self._factor_view = QWebEngineView()
        self._factor_view.setHtml(CHART_PLACEHOLDER_HTML)
        chart_layout.addWidget(self._factor_view)
        left_col.addWidget(chart_frame, 1)

        description_frame = QFrame()
        description_frame.setFrameShape(QFrame.Box)
        description_layout = QVBoxLayout(description_frame)
        description_layout.setContentsMargins(16, 12, 16, 12)
        self._chart_description_label = QLabel(CHART_TABS[0]["description"])
        self._chart_description_label.setWordWrap(True)
        self._chart_description_label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self._chart_description_label.setStyleSheet("color: #888888; font-size: 12px;")
        description_layout.addWidget(self._chart_description_label)
        left_col.addWidget(description_frame)

        return left_col

    def _on_chart_tab_clicked(self) -> None:
        btn = self._chart_tab_group.checkedButton()
        key = btn.property("chart_key")
        tab = next(t for t in CHART_TABS if t["key"] == key)
        self._chart_description_label.setText(tab["description"])

        if self._chart_paths and key in self._chart_paths:
            self._factor_view.setUrl(QUrl.fromLocalFile(str(self._chart_paths[key])))
        else:
            self._factor_view.setHtml(CHART_PLACEHOLDER_HTML)

    def _build_data_column(self) -> QVBoxLayout:
        right_col = QVBoxLayout()

        right_col.addWidget(self._build_portfolio_panel(), 3)
        right_col.addWidget(self._build_controls_panel(), 1)
        right_col.addWidget(self._build_results_panel(), 3)

        self._set_status("not_run", "Not Run")
        return right_col

    def _build_controls_panel(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.Box)
        layout = QVBoxLayout(frame)

        button_row = QHBoxLayout()
        self._run_btn = QPushButton("Run Analysis")
        self._run_btn.clicked.connect(self._on_run_clicked)
        button_row.addWidget(self._run_btn, 2)

        self._reset_btn = QPushButton("Reset")
        self._reset_btn.setEnabled(False)
        self._reset_btn.clicked.connect(self._on_reset_clicked)
        button_row.addWidget(self._reset_btn, 1)
        layout.addLayout(button_row)

        self._status_label = QLabel()
        layout.addWidget(self._status_label, alignment=Qt.AlignLeft)

        return frame

    def _build_results_panel(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.Box)
        layout = QVBoxLayout(frame)

        title_label = QLabel("REGRESSION SUMMARY")
        title_label.setStyleSheet("color: #888888; font-size: 11px; font-weight: 600; letter-spacing: 1px;")
        layout.addWidget(title_label)

        self._r2_label = QLabel("R\u00b2: \u2014")
        self._r2_label.setStyleSheet("font-size: 13px; font-weight: 600; padding: 4px 0;")
        layout.addWidget(self._r2_label)

        grid = QGridLayout()
        grid.addWidget(QLabel("Factor"), 0, 0)
        grid.addWidget(QLabel("Beta"), 0, 1)
        grid.addWidget(QLabel("t-stat"), 0, 2)

        self._result_rows: dict[str, tuple[QLabel, QLabel]] = {}
        row_keys = ["const"] + FACTOR_NAMES
        row_labels = ["Alpha"] + FACTOR_NAMES
        for i, (key, label) in enumerate(zip(row_keys, row_labels), start=1):
            grid.addWidget(QLabel(label), i, 0)
            beta_label = QLabel("\u2014")
            tstat_label = QLabel("\u2014")
            grid.addWidget(beta_label, i, 1)
            grid.addWidget(tstat_label, i, 2)
            self._result_rows[key] = (beta_label, tstat_label)

        layout.addLayout(grid)
        layout.addStretch()
        return frame

    def _set_status(self, state: str, text: str) -> None:
        color, background, border = STATUS_PILL_STYLES[state]
        self._status_label.setText(text)
        self._status_label.setStyleSheet(f"""
            font-size: 11px;
            font-weight: 600;
            letter-spacing: 0.05em;
            color: {color};
            background-color: {background};
            border: 1px solid {border};
            border-radius: 3px;
            padding: 3px 10px;
        """)

    def _on_run_clicked(self) -> None:
        tickers = []
        weights = []
        for r in self._portfolio_rows:
            ticker = r["ticker_edit"].text().strip()
            if not ticker:
                continue
            tickers.append(ticker)
            weights.append(r["weight_spin"].value())

        if not tickers:
            self._set_status("failed", "Failed: add at least one ticker")
            return

        weight_sum = sum(weights)
        if abs(weight_sum - 1.0) > 0.01:
            self._set_status("failed", f"Failed: weights sum to {weight_sum:.2f}, must sum to 1.00")
            return

        self._run_btn.setEnabled(False)
        self._reset_btn.setEnabled(False)
        self._set_status("running", "Running...")

        self._worker = FactorWorker(tickers, np.array(weights))
        self._worker.finished_factors.connect(self._on_factor_finished)
        self._worker.failed.connect(self._on_factor_failed)
        self._worker.start()

    def _on_factor_finished(self, result) -> None:
        self._result = result
        self._run_btn.setEnabled(True)
        self._reset_btn.setEnabled(True)
        self._set_status("done", "Done")

        self._r2_label.setText(f"R\u00b2: {result.r_squared:.3f}")
        for key, (beta_label, tstat_label) in self._result_rows.items():
            beta_label.setText(f"{result.coefficients[key]:.4f}")
            tstat_label.setText(f"{result.tstats[key]:.2f}")

        self._chart_paths = {}
        for tab in CHART_TABS:
            html = tab["build"](result)
            path = Path(tempfile.gettempdir()) / f"argus_factor_analyzer_{tab['key']}_{id(self)}.html"
            path.write_text(html, encoding="utf-8")
            self._chart_paths[tab["key"]] = path

        selected_key = self._chart_tab_group.checkedButton().property("chart_key")
        self._factor_view.setUrl(QUrl.fromLocalFile(str(self._chart_paths[selected_key])))

    def _on_factor_failed(self, message: str) -> None:
        self._run_btn.setEnabled(True)
        self._reset_btn.setEnabled(self._result is not None)
        self._set_status("failed", f"Failed: {message}")

    def _on_reset_clicked(self) -> None:
        self._result = None
        self._chart_paths = {}
        self._reset_btn.setEnabled(False)
        self._set_status("not_run", "Not Run")
        self._factor_view.setHtml(CHART_PLACEHOLDER_HTML)
        self._r2_label.setText("R\u00b2: \u2014")
        for beta_label, tstat_label in self._result_rows.values():
            beta_label.setText("\u2014")
            tstat_label.setText("\u2014")

    def _build_portfolio_panel(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.Box)
        layout = QVBoxLayout(frame)

        self._portfolio_rows: list[dict] = []
        self._rows_layout = QVBoxLayout()
        layout.addLayout(self._rows_layout)

        add_btn = QPushButton("Add Ticker")
        add_btn.clicked.connect(lambda: self._add_portfolio_row())
        layout.addWidget(add_btn)

        self._add_portfolio_row("RELIANCE.NS", 1.0)

        return frame

    def _add_portfolio_row(self, ticker: str = "", weight: float = 0.0) -> None:
        row = QWidget()
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 0, 0, 0)

        ticker_edit = QLineEdit(ticker)
        ticker_edit.setPlaceholderText("Ticker (eg. RELIANCE.NS)")
        row_layout.addWidget(ticker_edit, 2)

        weight_spin = QDoubleSpinBox()
        weight_spin.setRange(0.0, 1.0)
        weight_spin.setSingleStep(0.05)
        weight_spin.setDecimals(2)
        weight_spin.setValue(weight)
        row_layout.addWidget(weight_spin, 1)

        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(lambda: self._remove_portfolio_row(row))
        row_layout.addWidget(remove_btn)

        self._rows_layout.addWidget(row)
        self._portfolio_rows.append({"row": row, "ticker_edit": ticker_edit, "weight_spin": weight_spin})

    def _remove_portfolio_row(self, row: QWidget) -> None:
        self._portfolio_rows = [r for r in self._portfolio_rows if r["row"] is not row]
        self._rows_layout.removeWidget(row)
        row.deleteLater()