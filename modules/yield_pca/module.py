from pathlib import Path
import tempfile

from PySide6.QtCore import Qt, QUrl
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QButtonGroup,
    QLabel, QFrame, QStackedWidget, QProgressBar
)
from PySide6.QtWebEngineWidgets import QWebEngineView

from core.base_module import ArgusModule
from modules.yield_pca.pca_worker import PCAWorker
from modules.yield_pca.pca_chart import CHART_TABS, COMPONENT_COLORS

MONO_FONT = "'JetBrains Mono', 'Fira Mono', monospace"

# (text color, background tint, border) per run state — same pill formula as
# Order Book's connection diagnostics status.
STATUS_PILL_STYLES = {
    "not_run": ("#888888", "rgba(136, 136, 136, 0.12)", "rgba(136, 136, 136, 0.4)"),
    "running": ("#2B5EA7", "rgba(43, 94, 167, 0.15)", "rgba(43, 94, 167, 0.45)"),
    "done": ("#2ECC71", "rgba(46, 204, 113, 0.12)", "rgba(46, 204, 113, 0.4)"),
    "failed": ("#E74C3C", "rgba(231, 76, 60, 0.12)", "rgba(231, 76, 60, 0.4)"),
}

VARIANCE_INTRO = "Share of day-to-day yield variance explained by each component:"
VARIANCE_GUIDANCE = [
    ("Level", "Usually the dominant share, often 80-95% — most days the whole curve moves up or down together."),
    ("Slope", "A smaller share — reflects the short end moving differently from the long end."),
    ("Curvature", "The smallest share — reflects the belly of the curve moving against both ends."),
]

CONTRIBUTION_INTRO = "How today's curve deviates from its historical average, by component:"
CONTRIBUTION_GUIDANCE = [
    ("Level", "A large value means today's curve sits well above or below its historical average, across all tenors."),
    ("Slope", "A large value means today's curve is unusually steep or flat versus its average shape."),
    ("Curvature", "A large value means the belly (5Y) is unusually bowed relative to the short and long ends."),
]

CHART_PLACEHOLDER_HTML = (
    "<html><body style='background:#0D0D0D; color:#888888; display:flex; "
    "align-items:center; justify-content:center; height:100vh; margin:0; "
    "font-family:sans-serif;'><p>Run PCA to see this chart.</p></body></html>"
)


def _build_divider() -> QWidget:
    divider = QWidget()
    divider.setFixedHeight(1)
    divider.setStyleSheet("background-color: #2A2A2A;")
    divider.setAttribute(Qt.WA_StyledBackground, True)
    return divider


class YieldPCAModule(ArgusModule):
    """PCA decomposition of the Indian G-Sec yield curve into Level/Slope/Curvature."""

    def __init__(self):
        self._result = None
        self._worker: PCAWorker | None = None
        self._chart_paths: dict[str, Path] = {}
        self._selected_chart_key = CHART_TABS[0]["key"]

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

        body_row = QHBoxLayout()
        outer_layout.addLayout(body_row, 1)

        body_row.addLayout(self._build_chart_column(), 3)
        body_row.addLayout(self._build_data_column(), 2)

        self._set_status("not_run", "Not Run")

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
        self._pca_view = QWebEngineView()
        self._pca_view.setHtml(CHART_PLACEHOLDER_HTML)
        chart_layout.addWidget(self._pca_view)
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

    def _build_data_column(self) -> QVBoxLayout:
        right_col = QVBoxLayout()

        controls_frame = QFrame()
        controls_frame.setFrameShape(QFrame.Box)
        controls_layout = QVBoxLayout(controls_frame)
        controls_layout.setContentsMargins(16, 12, 16, 12)
        controls_layout.setSpacing(10)

        button_row = QHBoxLayout()
        button_row.setSpacing(8)
        self._run_btn = QPushButton("Run PCA")
        self._run_btn.clicked.connect(self._on_run_clicked)
        self._run_btn.setStyleSheet("""
            QPushButton {
                background-color: #2B5EA7;
                border: 1px solid #2B5EA7;
                color: #FFFFFF;
                font-weight: 600;
            }
            QPushButton:hover { background-color: #356bb8; border-color: #356bb8; }
            QPushButton:disabled {
                background-color: #1A1A1A;
                border-color: #3A3A3A;
                color: #666666;
            }
        """)
        button_row.addWidget(self._run_btn, 2)

        self._reset_btn = QPushButton("Reset")
        self._reset_btn.setEnabled(False)
        self._reset_btn.clicked.connect(self._on_reset_clicked)
        button_row.addWidget(self._reset_btn, 1)
        controls_layout.addLayout(button_row)

        self._status_label = QLabel()
        controls_layout.addWidget(self._status_label, alignment=Qt.AlignLeft)

        right_col.addWidget(controls_frame, 2)

        variance_frame = QFrame()
        variance_frame.setFrameShape(QFrame.Box)
        variance_layout = QVBoxLayout(variance_frame)
        variance_layout.setContentsMargins(16, 14, 16, 14)
        variance_layout.addWidget(self._build_section_title("EXPLAINED VARIANCE"))
        self._variance_stack, self._variance_body = self._build_result_stack(VARIANCE_INTRO, VARIANCE_GUIDANCE)
        variance_layout.addWidget(self._variance_stack)
        right_col.addWidget(variance_frame, 9)

        contrib_frame = QFrame()
        contrib_frame.setFrameShape(QFrame.Box)
        contrib_layout = QVBoxLayout(contrib_frame)
        contrib_layout.setContentsMargins(16, 14, 16, 14)
        contrib_layout.addWidget(self._build_section_title("CURRENT CURVE DECOMPOSITION"))
        self._contrib_stack, self._contrib_body = self._build_result_stack(CONTRIBUTION_INTRO, CONTRIBUTION_GUIDANCE)
        contrib_layout.addWidget(self._contrib_stack)
        right_col.addWidget(contrib_frame, 9)

        return right_col

    @staticmethod
    def _build_section_title(text: str) -> QLabel:
        title = QLabel(text)
        title.setStyleSheet(
            "color: #888888; font-size: 11px; font-weight: 600; "
            "letter-spacing: 1.5px; padding-bottom: 6px;"
        )
        return title

    @staticmethod
    def _build_result_stack(intro_text: str, guidance: list[tuple[str, str]]) -> tuple[QStackedWidget, QVBoxLayout]:
        stack = QStackedWidget()

        placeholder_page = QWidget()
        placeholder_layout = QVBoxLayout(placeholder_page)
        placeholder_layout.setContentsMargins(0, 4, 0, 0)
        placeholder_layout.setSpacing(0)

        intro = QLabel(intro_text)
        intro.setWordWrap(True)
        intro.setStyleSheet("color: #888888; font-size: 12px; padding-bottom: 10px;")
        placeholder_layout.addWidget(intro)

        for i, (label, text) in enumerate(guidance):
            if i > 0:
                placeholder_layout.addWidget(_build_divider())
            placeholder_layout.addWidget(YieldPCAModule._build_guidance_row(label, text), 1)
        stack.addWidget(placeholder_page)

        results_page = QWidget()
        body = QVBoxLayout(results_page)
        body.setContentsMargins(0, 4, 0, 0)
        body.setSpacing(0)
        stack.addWidget(results_page)

        stack.setCurrentIndex(0)
        return stack, body

    @staticmethod
    def _build_guidance_row(label: str, text: str) -> QWidget:
        color = COMPONENT_COLORS.get(label, "#E8E8E8")

        row = QWidget()
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(0, 10, 0, 10)
        row_layout.addStretch()

        content = QVBoxLayout()
        content.setSpacing(5)

        header = QHBoxLayout()
        header.setSpacing(8)
        swatch = QLabel()
        swatch.setFixedSize(9, 9)
        swatch.setStyleSheet(f"background-color: {color}; border-radius: 2px;")
        swatch.setAttribute(Qt.WA_StyledBackground, True)
        header.addWidget(swatch)
        name = QLabel(label)
        name.setStyleSheet(f"color: {color}; font-size: 12px; font-weight: 600;")
        header.addWidget(name)
        header.addStretch()
        content.addLayout(header)

        description = QLabel(text)
        description.setWordWrap(True)
        description.setStyleSheet("color: #888888; font-size: 12px;")
        content.addWidget(description)

        row_layout.addLayout(content)
        row_layout.addStretch()
        return row

    @staticmethod
    def _build_component_row(label: str, value_text: str, fraction: float) -> QWidget:
        color = COMPONENT_COLORS.get(label, "#E8E8E8")

        row = QWidget()
        row_layout = QVBoxLayout(row)
        row_layout.setContentsMargins(0, 10, 0, 10)
        row_layout.addStretch()

        content = QVBoxLayout()
        content.setSpacing(7)

        header = QHBoxLayout()
        header.setSpacing(8)

        swatch = QLabel()
        swatch.setFixedSize(9, 9)
        swatch.setStyleSheet(f"background-color: {color}; border-radius: 2px;")
        swatch.setAttribute(Qt.WA_StyledBackground, True)
        header.addWidget(swatch)

        name = QLabel(label)
        name.setStyleSheet("color: #E8E8E8; font-size: 13px;")
        header.addWidget(name)
        header.addStretch()

        value = QLabel(value_text)
        value.setStyleSheet(f"font-family: {MONO_FONT}; font-size: 13px; font-weight: 600; color: #E8E8E8;")
        header.addWidget(value)
        content.addLayout(header)

        meter = QProgressBar()
        meter.setRange(0, 1000)
        meter.setValue(int(max(0.0, min(1.0, fraction)) * 1000))
        meter.setTextVisible(False)
        meter.setFixedHeight(4)
        meter.setStyleSheet(f"""
            QProgressBar {{
                background-color: #262626;
                border: none;
                border-radius: 2px;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 2px;
            }}
        """)
        content.addWidget(meter)

        row_layout.addLayout(content)
        row_layout.addStretch()
        return row

    @staticmethod
    def _clear_layout(layout) -> None:
        while layout.count():
            item = layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()

    def _populate_rows(self, layout, component_labels, texts, fractions) -> None:
        self._clear_layout(layout)
        for i, label in enumerate(component_labels):
            if i > 0:
                layout.addWidget(_build_divider())
            layout.addWidget(self._build_component_row(label, texts[i], fractions[i]), 1)

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

    def _on_chart_tab_clicked(self) -> None:
        btn = self._chart_tab_group.checkedButton()
        key = btn.property("chart_key")
        self._selected_chart_key = key
        tab = next(t for t in CHART_TABS if t["key"] == key)
        self._chart_description_label.setText(tab["description"])

        if key in self._chart_paths:
            self._pca_view.setUrl(QUrl.fromLocalFile(str(self._chart_paths[key])))
        else:
            self._pca_view.setHtml(CHART_PLACEHOLDER_HTML)

    def _on_run_clicked(self) -> None:
        self._run_btn.setEnabled(False)
        self._reset_btn.setEnabled(False)
        self._set_status("running", "Running...")

        self._worker = PCAWorker()
        self._worker.finished_pca.connect(self._on_pca_finished)
        self._worker.failed.connect(self._on_pca_failed)
        self._worker.start()

    def _on_pca_finished(self, result) -> None:
        self._result = result
        self._run_btn.setEnabled(True)
        self._reset_btn.setEnabled(True)
        self._set_status("done", "Done")

        pcts = result.explained_variance_ratio
        self._populate_rows(
            self._variance_body,
            result.component_labels,
            texts=[f"{p:.1%}" for p in pcts],
            fractions=list(pcts),
        )
        self._variance_stack.setCurrentIndex(1)

        bps = result.current_contributions * 10000
        max_abs = max(abs(b) for b in bps) or 1.0
        self._populate_rows(
            self._contrib_body,
            result.component_labels,
            texts=[f"{b:+.1f} bps" for b in bps],
            fractions=[abs(b) / max_abs for b in bps],
        )
        self._contrib_stack.setCurrentIndex(1)

        self._chart_paths = {}
        for tab in CHART_TABS:
            html = tab["build"](result)
            path = Path(tempfile.gettempdir()) / f"argus_yield_pca_{tab['key']}_{id(self)}.html"
            path.write_text(html, encoding="utf-8")
            self._chart_paths[tab["key"]] = path

        self._pca_view.setUrl(QUrl.fromLocalFile(str(self._chart_paths[self._selected_chart_key])))

    def _on_pca_failed(self, message: str) -> None:
        self._run_btn.setEnabled(True)
        self._reset_btn.setEnabled(self._result is not None)
        self._set_status("failed", f"Failed: {message}")

    def _on_reset_clicked(self) -> None:
        self._result = None
        self._chart_paths = {}
        self._reset_btn.setEnabled(False)
        self._set_status("not_run", "Not Run")
        self._variance_stack.setCurrentIndex(0)
        self._contrib_stack.setCurrentIndex(0)
        self._pca_view.setHtml(CHART_PLACEHOLDER_HTML)
