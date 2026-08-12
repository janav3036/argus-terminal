import tempfile
from pathlib import Path

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QButtonGroup,
    QLabel, QGridLayout, QTableWidget, QTableWidgetItem, QFrame, QHeaderView
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from core.base_module import ArgusModule
from modules.vol_regime.hmm_worker import HMMWorker
from modules.vol_regime.regime_chart import build_regime_html

class VolRegimeModule(ArgusModule):

    def __init__(self):
        self._result = None
        self._worker: HMMWorker | None = None

    def get_sidebar_label(self):
        return "Vol Regime"

    def get_status_preview(self):
        if self._result is None:
            return "Not detected"
        confidence = self._result.current_posterior[self._result.current_label]
        return f"{self._result.current_label} ({confidence:.0%})"

    def build_widget(self) -> QWidget:
        widget = QWidget()
        outer_layout = QVBoxLayout(widget)

        heading = QLabel("VOLATILITY REGIME")
        heading.setAlignment(Qt.AlignCenter)
        heading.setStyleSheet("font-size: 16px; font-weight: bold; padding: 6px;")
        outer_layout.addWidget(heading)

        description_frame = QFrame()
        description_frame.setFrameShape(QFrame.Box)
        description_layout = QVBoxLayout(description_frame)
        description = QLabel(
            "Fits a Hidden Markov Model to NIFTY's 30-day realized volatility "
            "to classify the current market regime."
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

        self._regime_view = QWebEngineView()
        chart_layout.addWidget(self._regime_view)

        middle_row.addWidget(chart_frame, 3)

        right_col = QVBoxLayout()
        middle_row.addLayout(right_col, 2)

        controls_frame = QFrame()
        controls_frame.setFrameShape(QFrame.Box)
        controls_layout = QVBoxLayout(controls_frame)

        toggle_row = QHBoxLayout()
        self._n_states_group = QButtonGroup(controls_frame)
        self._n_states_group.setExclusive(True)

        two_state_btn = QPushButton("2-State")
        two_state_btn.setCheckable(True)
        two_state_btn.setChecked(True)
        two_state_btn.setProperty("n_states", 2)
        self._n_states_group.addButton(two_state_btn)
        toggle_row.addWidget(two_state_btn)

        three_state_btn = QPushButton("3-State")
        three_state_btn.setCheckable(True)
        three_state_btn.setProperty("n_states", 3)
        self._n_states_group.addButton(three_state_btn)
        toggle_row.addWidget(three_state_btn)

        controls_layout.addLayout(toggle_row)

        self._detect_btn = QPushButton("Detect Regime")
        self._detect_btn.clicked.connect(self._on_detect_clicked)
        controls_layout.addWidget(self._detect_btn)

        self._status_label = QLabel("Not Detected")
        controls_layout.addWidget(self._status_label)

        right_col.addWidget(controls_frame, 1)

        regime_frame = QFrame()
        regime_frame.setFrameShape(QFrame.Box)
        regime_layout = QVBoxLayout(regime_frame)

        self._current_regime_label = QLabel("-")
        self._current_regime_label.setAlignment(Qt.AlignCenter)
        self._current_regime_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        regime_layout.addWidget(self._current_regime_label)

        self._posterior_grid = QGridLayout()
        regime_layout.addLayout(self._posterior_grid)

        right_col.addWidget(regime_frame, 1)

        transmat_frame = QFrame()
        transmat_frame.setFrameShape(QFrame.Box)
        transmat_layout = QVBoxLayout(transmat_frame)

        transmat_title = QLabel("Transition Matrix")
        transmat_title.setAlignment(Qt.AlignCenter)
        transmat_layout.addWidget(transmat_title)

        self._transmat_table = QTableWidget()
        self._transmat_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self._transmat_table.verticalHeader().setSectionResizeMode(QHeaderView.Stretch)
        transmat_layout.addWidget(self._transmat_table)

        right_col.addWidget(transmat_frame, 2)

        return widget

    def _on_detect_clicked(self) -> None:
        self._detect_btn.setEnabled(False)
        self._status_label.setText("Detecting...")

        n_states = self._n_states_group.checkedButton().property("n_states")

        self._worker = HMMWorker(n_states=n_states)
        self._worker.finished_regime.connect(self._on_regime_finished)
        self._worker.failed.connect(self._on_regime_failed)
        self._worker.start()

    def _on_regime_finished(self, result) -> None:
        self._result = result
        self._detect_btn.setEnabled(True)
        self._status_label.setText("Done")

        self._current_regime_label.setText(result.current_label)

        while self._posterior_grid.count():
            self._posterior_grid.takeAt(0).widget().deleteLater()

        for row, label in enumerate(result.label_order):
            self._posterior_grid.addWidget(QLabel(label), row, 0)
            prob = result.current_posterior[label]
            self._posterior_grid.addWidget(QLabel(f"{prob:.1%}"), row, 1)

        n = len(result.label_order)
        self._transmat_table.setRowCount(n)
        self._transmat_table.setColumnCount(n)
        self._transmat_table.setHorizontalHeaderLabels(result.label_order)
        self._transmat_table.setVerticalHeaderLabels(result.label_order)
        for i in range(n):
            for j in range(n):
                item = QTableWidgetItem(f"{result.transmat[i, j]:.1%}")
                item.setTextAlignment(Qt.AlignCenter)
                self._transmat_table.setItem(i, j, item)

        html = build_regime_html(result)
        regime_path = Path(tempfile.gettempdir()) / f"argus_vol_regime_{id(self)}.html"
        regime_path.write_text(html, encoding="utf-8")
        self._regime_view.setUrl(QUrl.fromLocalFile(str(regime_path)))

    def _on_regime_failed(self, message: str) -> None:
        self._detect_btn.setEnabled(True)
        self._status_label.setText(f"Detection Failed: {message}")