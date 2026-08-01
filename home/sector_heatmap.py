import tempfile
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtWebEngineWidgets import QWebEngineView

from home.sector_heatmap_chart import build_heatmap_html

class SectorHeatmap(QWidget):
    def __init__(self, parent : QWidget | None = None):
        super().__init__(parent)

        self._view = QWebEngineView()
        layout = QVBoxLayout(self)
        layout.addWidget(self._view)

    def update_data(self, payload: dict) -> None:
        html = build_heatmap_html(payload)
        path = Path(tempfile.gettempdir()) / f"argus_sector_heatmap_{id(self)}.html"
        path.write_text(html, encoding="utf-8")
        self._view.setUrl(QUrl.fromLocalFile(str(path)))