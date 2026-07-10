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

