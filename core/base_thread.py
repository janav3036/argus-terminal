from PySide6.QtCore import QThread, Signal

class ArgusDataThread(QThread):
    """Base class for background data feeds. Runs off the UI Thread and pushes updates via QT signals."""
    data_updated = Signal(dict)
    status_changed = Signal(str)

    def run(self) -> None:
        """Fetch/stream data in a loop, emitting data_updated / status_changed"""
        raise NotImplementedError(
            f"{type(self).__name__} must override run()"
        )