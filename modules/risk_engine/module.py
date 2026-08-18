from pathlib import Path
import tempfile

import numpy as np
from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame,
    QPushButton, QLineEdit, QDoubleSpinBox, QButtonGroup,
    QTableWidget, QTableWidgetItem, QHeaderView
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from core.base_module import ArgusModule
from modules.risk_engine.risk_worker import RiskWorker
from modules.risk_engine.risk_chart import CHART_TABS

CHART_PLACEHOLDER_HTML = (
    "<html><body style='background:#0D0D0D; color:#888888; display:flex; "
    "align-items:center; justify-content:center; height:100vh; margin:0; "
    "font-family:sans-serif;'><p>Calculate risk to see this chart.</p></body></html>"
)
RISK_METHODS = [("historical", "Historical"), ("parametric", "Parametric"), ("monte_carlo", "Monte Carlo")]
RISK_COLUMNS = [("1d 95%", 1, 0.95), ("1d 99%", 1, 0.99), ("5d 95%", 5, 0.95), ("5d 99%", 5, 0.99)]

STATUS_PILL_STYLES = {
    "not_run": ("#888888", "rgba(136, 136, 136, 0.12)", "rgba(136, 136, 136, 0.4)"),
    "running": ("#2B5EA7", "rgba(43, 94, 167, 0.15)", "rgba(43, 94, 167, 0.45)"),
    "done": ("#2ECC71", "rgba(46, 204, 113, 0.12)", "rgba(46, 204, 113, 0.4)"),
    "failed": ("#E74C3C", "rgba(231, 76, 60, 0.12)", "rgba(231, 76, 60, 0.4)"),
}

class RiskEngineModule(ArgusModule):

    def __init__(self):
        self._result = None
        self._worker: RiskWorker | None = None
        self._chart_paths: dict[str, Path] = {}

    def get_sidebar_label(self):
        return "Risk Engine"

    def get_status_preview(self):
        if self._result is None:
            return "Not Run"
        var_1d_95 = self._result.var_table["historical"][1][0.95]
        return f"VaR (1d): {var_1d_95:.2%}"

    def build_widget(self) -> QWidget:
        widget = QWidget()
        outer_layout = QVBoxLayout(widget)

        heading = QLabel("PORTFOLIO RISK ENGINE")
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
        self._risk_view = QWebEngineView()
        self._risk_view.setHtml(CHART_PLACEHOLDER_HTML)
        chart_layout.addWidget(self._risk_view)
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
            self._risk_view.setUrl(QUrl.fromLocalFile(str(self._chart_paths[key])))
        else:
            self._risk_view.setHtml(CHART_PLACEHOLDER_HTML)

    def _build_data_column(self) -> QVBoxLayout:
        right_col = QVBoxLayout()

        right_col.addWidget(self._build_portfolio_panel(), 3)
        right_col.addWidget(self._build_controls_panel(), 1)

        var_frame, self._var_table = self._build_table_panel("VALUE AT RISK")
        right_col.addWidget(var_frame, 3)

        cvar_frame, self._cvar_table = self._build_table_panel("CONDITIONAL VaR (EXPECTED SHORTFALL)")
        right_col.addWidget(cvar_frame, 3)

        self._set_status("not_run", "Not Run")
        return right_col

    def _build_controls_panel(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.Box)
        layout = QVBoxLayout(frame)

        button_row = QHBoxLayout()
        self._run_btn = QPushButton("Calculate Risk")
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

    def _build_table_panel(self, title: str) -> tuple[QFrame, QTableWidget]:
        frame = QFrame()
        frame.setFrameShape(QFrame.Box)
        layout = QVBoxLayout(frame)

        title_label = QLabel(title)
        title_label.setStyleSheet("color: #888888; font-size: 11px; font-weight: 600; letter-spacing: 1px;")
        layout.addWidget(title_label)

        table = self._build_risk_table()
        layout.addWidget(table)

        return frame, table

    @staticmethod
    def _build_risk_table() -> QTableWidget:
        table = QTableWidget(len(RISK_METHODS), len(RISK_COLUMNS))
        table.setHorizontalHeaderLabels([label for label, _, _ in RISK_COLUMNS])
        table.setVerticalHeaderLabels([label for _, label in RISK_METHODS])
        table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        return table

    @staticmethod
    def _populate_risk_table(table: QTableWidget, data: dict) -> None:
        for row, (method_key, _) in enumerate(RISK_METHODS):
            for col, (_, horizon, confidence) in enumerate(RISK_COLUMNS):
                value = data.get(method_key, {}).get(horizon, {}).get(confidence)
                text = f"{value:.2%}" if value is not None else "—"
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignCenter)
                table.setItem(row, col, item)

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
        self._set_status("running", "Calculating...")

        self._worker = RiskWorker(tickers, np.array(weights))
        self._worker.finished_risk.connect(self._on_risk_finished)
        self._worker.failed.connect(self._on_risk_failed)
        self._worker.start()

    def _on_risk_finished(self, result) -> None:
        self._result = result
        self._run_btn.setEnabled(True)
        self._reset_btn.setEnabled(True)
        self._set_status("done", "Done")

        self._populate_risk_table(self._var_table, result.var_table)
        self._populate_risk_table(self._cvar_table, result.cvar_table)

        self._chart_paths = {}
        for tab in CHART_TABS:
            html = tab["build"](result)
            path = Path(tempfile.gettempdir()) / f"argus_risk_engine_{tab['key']}_{id(self)}.html"
            path.write_text(html, encoding="utf-8")
            self._chart_paths[tab["key"]] = path

        selected_key = self._chart_tab_group.checkedButton().property("chart_key")
        self._risk_view.setUrl(QUrl.fromLocalFile(str(self._chart_paths[selected_key])))

    def _on_risk_failed(self, message: str) -> None:
        self._run_btn.setEnabled(True)
        self._reset_btn.setEnabled(self._result is not None)
        self._set_status("failed", f"Failed: {message}")

    def _on_reset_clicked(self) -> None:
        self._result = None
        self._chart_paths = {}
        self._reset_btn.setEnabled(False)
        self._set_status("not_run", "Not Run")
        self._risk_view.setHtml(CHART_PLACEHOLDER_HTML)
        self._var_table.clearContents()
        self._cvar_table.clearContents()

    def _build_portfolio_panel(self) -> QFrame:
        frame = QFrame()
        frame.setFrameShape(QFrame.Box)
        layout = QVBoxLayout(frame)

        self._portfolio_rows: list[dict] =[]
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