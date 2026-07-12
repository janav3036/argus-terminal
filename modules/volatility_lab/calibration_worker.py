from PySide6.QtCore import QThread, Signal
from modules.volatility_lab.heston_bridge import load_snapshot, calibrate

class CalibrationWorker(QThread):
    """One shot bg calibration run - not a persistent feed"""

    finished_calibration = Signal(object, object)
    failed = Signal(str)

    def __init__(self, snapshot_dt: str, parent = None):
        super().__init__(parent)
        self._snapshot_dt = snapshot_dt

    def run(self) -> None:
        try:
            data = load_snapshot(self._snapshot_dt)
            result = calibrate(data)
        except Exception as exc:
            self.failed.emit(str(exc))
            return
        self.finished_calibration.emit(data, result)