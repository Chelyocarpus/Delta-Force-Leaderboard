from typing import Dict, Any
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QStatusBar,
    QLineEdit, QTableWidgetItem, QWidget, QVBoxLayout,
    QHBoxLayout, QShortcut
)
from PyQt5.QtCore import QSettings, Qt
from PyQt5.QtGui import QIcon, QKeySequence
import os

from ..data.database import Database
from ..data.medals import MedalProcessor
from ..utils.constants import (
    MAIN_WINDOW_SIZE, APP_TITLE, MAIN_TABLE_COLUMNS,
    RESOURCES_DIR
)

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.settings: QSettings = QSettings('DeltaForce', 'Leaderboard')
        self._cached_settings: Dict[str, Any] = {}
        
        # Initialize core components
        self._init_database()
        self._init_window()
        self._init_ui()
        self._load_cached_settings()
        self.setCentralWidget(QWidget())
        self.layout = QVBoxLayout(self.centralWidget())
        
    def showEvent(self, event):
        """Run import check after window is shown"""
        super().showEvent(event)
        from .dialogs.import_on_startup import run_import_check
        run_import_check()
        self.load_data_from_db()  # Refresh the table after potential imports
        
    def _init_database(self) -> None:
        """Initialize database connection and medal processor"""
        self.db = Database()
        self.db_path = self.db.db_path
        self.medal_processor = MedalProcessor(self.db)

    def _init_window(self) -> None:
        """Setup main window properties"""
        self.setWindowTitle(APP_TITLE)
        self.setGeometry(100, 100, *MAIN_WINDOW_SIZE)
        
        # Set window icon
        icon_path = os.path.join(RESOURCES_DIR, "favicon.png")
        if os.path.exists(icon_path):
            app_icon = QIcon(icon_path)
            self.setWindowIcon(app_icon)
            QApplication.setWindowIcon(app_icon)

        self.restore_window_state()

    def _init_ui(self) -> None:
        """Initialize UI components"""
        # Initialize search
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search players...")
        search_layout.addWidget(self.search_input)
        
        # Setup search shortcut
        self.search_shortcut = QShortcut(QKeySequence("Ctrl+F"), self)
        self.search_shortcut.activated.connect(lambda: self.search_input.setFocus())
        
        # Add layouts
        self.layout.addLayout(search_layout)
        
        # Initialize table
        self.table = QTableWidget()
        self.layout.addWidget(self.table)
        self.table.setColumnCount(len(MAIN_TABLE_COLUMNS))
        self.table.setHorizontalHeaderLabels(MAIN_TABLE_COLUMNS)
        self.table.setUpdatesEnabled(False)
        self.table.horizontalHeader().setHighlightSections(False)
        self.table.verticalHeader().setHighlightSections(False)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.ExtendedSelection)

        # Initialize status bar
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

    def _load_cached_settings(self) -> None:
        """Cache frequently accessed settings"""
        common_settings = ['window_state', 'geometry', 'column_widths']
        self._cached_settings = {
            setting: self.settings.value(setting)
            for setting in common_settings
        }

    def closeEvent(self, event) -> None:
        """Save window state before closing"""
        self.settings.setValue('windowGeometry', self.saveGeometry())
        self.settings.setValue('windowState', self.saveState())
        super().closeEvent(event)

    def restore_window_state(self) -> None:
        """Restore window geometry and state"""
        geometry = self.settings.value('windowGeometry')
        state = self.settings.value('windowState')
        
        if geometry is not None:
            self.restoreGeometry(geometry)
        if state is not None:
            self.restoreState(state)
        else:
            # Fallback to default size if no saved state
            self.resize(*MAIN_WINDOW_SIZE)
            self.move(100, 100)  # Default position

    # ...existing code for other methods...
