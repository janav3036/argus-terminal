from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget
from PySide6.QtCore import Signal, QTimer
from core.base_module import ArgusModule

class Sidebar(QListWidget):
    """Left handed module navigation list"""

    module_selected = Signal(ArgusModule)

    def __init__(self, modules: list[ArgusModule], parent: QWidget | None = None):
        super().__init__(parent)
        self._modules = modules
        self._populate()
        self.itemClicked.connect(self._on_item_clicked)

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_previews)
        self._refresh_timer.start(2000)
    
    def _populate(self) -> None:
        for module in self._modules:
            label = module.get_sidebar_label()
            preview = module.get_status_preview()
            item = QListWidgetItem(f"{label}\n{preview}")
            self.addItem(item)

    def _on_item_clicked(self, item: QListWidgetItem) -> None:
        row = self.row(item)
        self.module_selected.emit(self._modules[row])
        
    def _refresh_previews(self) -> None:
        for row, module in enumerate(self._modules):
            label = module.get_sidebar_label()
            preview = module.get_status_preview()
            self.item(row).setText(f"{label}\n{preview}")