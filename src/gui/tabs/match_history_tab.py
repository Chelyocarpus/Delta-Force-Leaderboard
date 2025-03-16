from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem
from PyQt5.QtCore import Qt
import sqlite3
from ..widgets.numeric_sort import NumericSortItem
from ..dialogs.match_details import MatchDetailsDialog

class MatchHistoryTab(QWidget):
    def __init__(self, parent, player_name, db_path):
        super().__init__(parent)
        self.player_name = player_name
        self.db_path = db_path
        self.parent = parent
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    data,
                    map,
                    outcome,
                    class,
                    team,
                    rank,
                    score,
                    kills,
                    deaths,
                    assists,
                    revives,
                    captures,
                    vehicle_damage,
                    tactical_respawn,
                    snapshot_name
                FROM matches
                WHERE name = ?
                ORDER BY data DESC
            """, (self.player_name,))

            # Create table
            self.matches_table = QTableWidget()
            self.matches_table.setColumnCount(14)  # Keep visible columns same
            self.matches_table.setHorizontalHeaderLabels([
                "Date", "Map", "Outcome", "Class", "Team", "Rank",
                "Score", "Kills", "Deaths", "Assists", "Revives",
                "Captures", "Vehicle Damage", "Tactical Respawns"
            ])
            
            history = cursor.fetchall()
            self.matches_table.setRowCount(len(history))
            
            for row, data in enumerate(history):
                for col, value in enumerate(data[:-1]):  # Exclude snapshot_name from visible columns
                    if col in [0, 1, 2, 3, 4]:  # Date, Map, Outcome, Class, and Team columns
                        item = QTableWidgetItem(str(value))
                    else:
                        item = NumericSortItem(value)
                    item.setTextAlignment(Qt.AlignCenter)
                    
                    # Store snapshot_name as user data in the first column
                    if col == 0:
                        item.setData(Qt.UserRole, data[-1])  # Store snapshot_name
                        
                    self.matches_table.setItem(row, col, item)
        
        self.matches_table.resizeColumnsToContents()
        self.matches_table.horizontalHeader().setSortIndicator(0, Qt.DescendingOrder)
        
        # Add tooltips to column headers
        for col, tooltip in enumerate([
            "Match Date", "Map", "Outcome", "Class Used", "Team",
            "Player Rank", "Total Score", "Total Kills", "Total Deaths", 
            "Total Assists", "Total Revives", "Total Captures",
            "Vehicle Damage", "Tactical Respawns"
        ]):
            self.matches_table.horizontalHeaderItem(col).setToolTip(tooltip)
        
        # Connect double-click signal
        self.matches_table.doubleClicked.connect(self.on_row_double_clicked)
        
        layout.addWidget(self.matches_table)
        self.setLayout(layout)
        
    def on_row_double_clicked(self, index):
        row = index.row()
        snapshot_name = self.matches_table.item(row, 0).data(Qt.UserRole)
        if snapshot_name:
            dialog = MatchDetailsDialog(self, snapshot_name)
            dialog.exec_()
