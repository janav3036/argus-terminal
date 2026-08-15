from pathlib import Path
import tempfile

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QGridLayout, QFrame
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from core.base_module import ArgusModule
from modules.yield_pca.pca_worker import PCAWorker
from modules.yield_pca.pca_chart import build_pca_html


class YieldPCAModule(ArgusModule):
    """PCA decomposition of the Indian G-Sec yield curve into Level/Slope/Curvature."""

    def __init__(self):
        self._result = None
        self._worker: PCAWorker | None = None

    def get_sidebar_label(self):
        return "Yield PCA"

    def get_status_preview(self):
        if self._result is None:
            return "Not Run"
        top_var = self._result.explained_variance_ratio[0]
        return f"Level explains {top_var:.0%}"

    def build_widget(self) -> QWidget:
        widget = QWidget()
        outer_layout = QVBoxLayout(widget)

        heading = QLabel("YIELD CURVE PCA")
        heading.setAlignment(Qt.AlignCenter)
        heading.setStyleSheet("font-size: 16px; font-weight: bold; padding: 6px;")
        outer_layout.addWidget(heading)

        description_frame = QFrame()
        description_frame.setFrameShape(QFrame.Box)
        description_layout = QVBoxLayout(description_frame)
        description = QLabel(
            "Decomposes daily G-Sec yield curve changes into three principal "
            "components: Level, Slope, and Curvature."
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

        self._pca_view = QWebEngineView()
        chart_layout.addWidget(self._pca_view)

        middle_row.addWidget(chart_frame, 3)

        right_col = QVBoxLayout()
        middle_row.addLayout(right_col, 2)

        controls_frame = QFrame()
        controls_frame.setFrameShape(QFrame.Box)
        controls_layout = QVBoxLayout(controls_frame)

        self._run_btn = QPushButton("Run PCA")
        self._run_btn.clicked.connect(self._on_run_clicked)
        controls_layout.addWidget(self._run_btn)

        self._status_label = QLabel("Not Run")
        controls_layout.addWidget(self._status_label)

        right_col.addWidget(controls_frame, 1)

        variance_frame = QFrame()
        variance_frame.setFrameShape(QFrame.Box)
        variance_layout = QVBoxLayout(variance_frame)

        variance_title = QLabel("Explained Variance")
        variance_title.setAlignment(Qt.AlignCenter)
        variance_layout.addWidget(variance_title)

        self._variance_grid = QGridLayout()
        variance_layout.addLayout(self._variance_grid)

        right_col.addWidget(variance_frame, 1)

        contrib_frame = QFrame()
        contrib_frame.setFrameShape(QFrame.Box)
        contrib_layout = QVBoxLayout(contrib_frame)

        contrib_title = QLabel("Current Curve Decomposition (bps)")
        contrib_title.setAlignment(Qt.AlignCenter)
        contrib_layout.addWidget(contrib_title)

        self._contrib_grid = QGridLayout()
        contrib_layout.addLayout(self._contrib_grid)

        right_col.addWidget(contrib_frame, 1)

        return widget

    def _on_run_clicked(self) -> None:
        self._run_btn.setEnabled(False)
        self._status_label.setText("Running...")

        self._worker = PCAWorker()
        self._worker.finished_pca.connect(self._on_pca_finished)
        self._worker.failed.connect(self._on_pca_failed)
        self._worker.start()

    def _on_pca_finished(self, result) -> None:
        self._result = result
        self._run_btn.setEnabled(True)
        self._status_label.setText("Done")

        while self._variance_grid.count():
            self._variance_grid.takeAt(0).widget().deleteLater()

        for row, label in enumerate(result.component_labels):
            self._variance_grid.addWidget(QLabel(label), row, 0)
            pct = result.explained_variance_ratio[row]
            self._variance_grid.addWidget(QLabel(f"{pct:.1%}"), row, 1)

        while self._contrib_grid.count():
            self._contrib_grid.takeAt(0).widget().deleteLater()

        for row, label in enumerate(result.component_labels):
            self._contrib_grid.addWidget(QLabel(label), row, 0)
            bps = result.current_contributions[row] * 10000
            self._contrib_grid.addWidget(QLabel(f"{bps:+.1f}"), row, 1)

        html = build_pca_html(result)
        pca_path = Path(tempfile.gettempdir()) / f"argus_yield_pca_{id(self)}.html"
        pca_path.write_text(html, encoding="utf-8")
        self._pca_view.setUrl(QUrl.fromLocalFile(str(pca_path)))

    def _on_pca_failed(self, message: str) -> None:
        self._run_btn.setEnabled(True)
        self._status_label.setText(f"PCA Failed: {message}")