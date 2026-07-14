from abc import ABC, abstractmethod
from PySide6.QtWidgets import QWidget

class ArgusModule(ABC):
    """Base class every Argus module subclasses"""

    @abstractmethod
    def get_sidebar_label(self) -> str:
        """Short name shown in the left sidebar"""
        
    @abstractmethod
    def get_status_preview(self) -> str:
        """One-line live status shown on sidebar and home page card"""

    @abstractmethod
    def build_widget(self) -> QWidget:
        """Construct and return the full QWidget for this module's page"""

    def shutdown(self) -> None:
        """Stop any background threads owned by this module. Default: nothing to stop."""

    def get_status_source(self) -> str | None:
        """Name of the status bar source this module drives, or None"""
        return None
    
    def get_status_signal(self):
        """Qt Signal(str) emitting live stale or disconnected or None if not applicable"""
        return None
    