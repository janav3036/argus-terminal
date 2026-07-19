from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import Signal, QTimer
from core.base_module import ArgusModule

class Sidebar(QListWidget):
    """Left handed module navigation list"""

    module_selected = Signal(ArgusModule)

    def __init__(self, modules: list[ArgusModule], parent: QWidget | None = None):
        super().__init__(parent)
        self._modules = modules
        self._preview_labels: list[QLabel] = []
        self._populate()
        self.itemClicked.connect(self._on_item_clicked)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_previews)
        self._refresh_timer.start(2000)

    def _build_row_widget(self, module: ArgusModule) -> tuple[QWidget, QLabel]:
        row = QWidget()
        layout = QVBoxLayout(row)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.setSpacing(2)

        name_label = QLabel(module.get_sidebar_label())
        name_label.setStyleSheet("font-size: 13px; font-weight: 600; color: #E8E8E8;")
        layout.addWidget(name_label)

        preview_label = QLabel(module.get_status_preview())
        preview_label.setStyleSheet("font-size: 11px; color: #888888;")
        layout.addWidget(preview_label)

        return row, preview_label

    def _populate(self) -> None:
        for module in self._modules:
            item = QListWidgetItem()
            row_widget, preview_label = self._build_row_widget(module)
            item.setSizeHint(row_widget.sizeHint())
            self.addItem(item)
            self.setItemWidget(item, row_widget)
            self._preview_labels.append(preview_label)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        row = self.row(item)
        self.module_selected.emit(self._modules[row])

    def _refresh_previews(self) -> None:
        for row, module in enumerate(self._modules):
            self._preview_labels[row].setText(module.get_status_preview())