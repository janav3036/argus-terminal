from PySide6.QtWidgets import QListWidget, QListWidgetItem, QWidget
from PySide6.QtCore import Signal
from core.base_module import ArgusModule

class Sidebar(QListWidget):
    """Left handed module navigation list"""

    module_selected = Signal(ArgusModule)

    def __init__(self, modules: list[ArgusModule], parent: QWidget | None = None):
        super().__init__(parent)
        self._modules = modules
        self._populate()
        self.currentRowChanged.connect(self._on_row_changed)
    
    def _populate(self) -> None:
        for module in self._modules:
            label = module.get_sidebar_label()
            preview = module.get_status_preview()
            item = QListWidgetItem(f"{label}\n{preview}")
            self.addItem(item)

    def _on_row_changed(self, row: int) -> None:
        if row<0:
            return
        self.module_selected.emit(self._modules[row])
        
    