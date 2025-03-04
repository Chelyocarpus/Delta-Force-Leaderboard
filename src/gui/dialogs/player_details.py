from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QTabWidget,
                           QLabel, QPushButton, QWidget)
from PyQt5.QtCore import QSettings
from ..tabs.overall_tab import setup_overall_tab
from ..tabs.achievement_tab import setup_achievement_tab  # Import the new tab
from ..tabs.class_tab import ClassTab
from ..tabs.map_tab import MapTab
from ..tabs.medals_tab import MedalsTab
from ..tabs.match_history_tab import MatchHistoryTab  # Add this import
from ..tabs.attacker_tab import AttackerTab  # Add this import
from ..tabs.defender_tab import DefenderTab  # Add this import

class PlayerDetailsDialog(QDialog):
    def __init__(self, parent, player_name):
        super().__init__(parent)
        self.settings = QSettings('DeltaForce', 'Leaderboard')
        self.parent = parent
        self.player_name = player_name  # Store the player name but use 'name' in queries
        self.overall_tab = QWidget()
        self.table = None  # Will be set by overall_tab
        self.db = parent.db  # Add reference to database
        
        self.setWindowTitle(f"Player Details - {player_name}")
        self.setMinimumSize(600, 500)  # Reduced from 800 to 600
        self.setModal(True)
        self.init_ui()
        self.restore_dialog_state()

    def format_value(self, value, label):
        """Format display values based on their type"""
        if isinstance(value, (int, float)):
            if "Rate" in label or "Ratio" in label:
                return f"{value:.2f}"
            if any(word in label for word in ["Percentage", "Rate", "%"]):
                return f"{value:.1f}%"
            return f"{int(value):,}"
        return str(value)

    def init_ui(self):
        layout = QVBoxLayout()
        tabs = QTabWidget()
        
        # Define base tab configurations with consistent argument format
        tab_configs = [
            ("Overall Stats", setup_overall_tab, self),  # Pass dialog directly
            ("Classes", ClassTab, [self, self.player_name, self.parent.db.db_path]),
            ("Map Performance", MapTab, [self, self.player_name, self.parent.db.db_path])  # Fixed map tab args
        ]

        # Add special tabs for specific users
        from src.utils.constants import USER
        if self.player_name in USER:
            tab_configs.extend([
                ("Attacker", AttackerTab, [self, self.player_name, self.parent.db.db_path]),
                ("Defender", DefenderTab, [self, self.player_name, self.parent.db.db_path]),
                ("Medals", MedalsTab, [self, self.player_name, self.parent.db.db_path])
            ])
        
        # Add match history tab
        tab_configs.append(
            ("Match History", MatchHistoryTab, [self, self.player_name, self.parent.db.db_path])
        )

        # Add the new achievements tab
        tab_configs.append(
            ("Achievements", setup_achievement_tab, self)
        )

        # Create and add tabs
        for tab_name, tab_class, args in tab_configs:
            if tab_name == "Overall Stats" or tab_name == "Achievements":
                tab = tab_class(args)  # Special handling for setup_overall_tab and setup_achievement_tab
            else:
                tab = tab_class(*args)  # All other tabs use positional args
            
            tabs.addTab(tab, tab_name)

        layout.addWidget(tabs)

        # Add close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.setLayout(layout)

    def closeEvent(self, event):
        """Save dialog geometry before closing"""
        self.settings.setValue('playerDetailsGeometry', self.saveGeometry())
        super().closeEvent(event)

    def restore_dialog_state(self):
        """Restore dialog geometry"""
        geometry = self.settings.value('playerDetailsGeometry')
        if geometry is not None:
            self.restoreGeometry(geometry)
        else:
            # Use smaller default size
            self.resize(700, 500)  # Reduced from 900 to 700
