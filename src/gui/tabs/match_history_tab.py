from PyQt5.QtWidgets import QWidget, QVBoxLayout, QTableWidget,QTableWidgetItem
from PyQt5.QtCore import Qt
import sqlite3
from ..widgets.numeric_sort import NumericSortItem
from ...utils.constants import HISTORY_TABLE_COLUMNS

class MatchHistoryTab(QWidget):
    def __init__(self, parent, player_name, db_path):
        super().__init__(parent)
        self.player_name = player_name
        self.db_path = db_path
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        history_table = QTableWidget()
        history_table.setColumnCount(10)
        history_table.setHorizontalHeaderLabels(HISTORY_TABLE_COLUMNS)
        history_table.setSortingEnabled(True)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    match_date,
                    snapshot_name,
                    rank,
                    class,
                    score,
                    kills,
                    deaths,
                    assists,
                    revives,
                    captures
                FROM matches
                WHERE player_name = ?
                ORDER BY match_date DESC
            """, (self.player_name,))
            
            history = cursor.fetchall()
            history_table.setRowCount(len(history))
            
            for row, data in enumerate(history):
                for col, value in enumerate(data):
                    if col in [0, 1, 3]:  # Date, Snapshot, and Class columns
                        item = QTableWidgetItem(str(value))
                    else:
                        item = NumericSortItem(value)
                    item.setTextAlignment(Qt.AlignCenter)
                    history_table.setItem(row, col, item)
        
        history_table.resizeColumnsToContents()
        history_table.horizontalHeader().setSortIndicator(0, Qt.DescendingOrder)
        
        # Add tooltips to column headers
        for col, tooltip in enumerate([
            "Match Date", "Match Details", "Player Rank", "Class Used",
            "Total Score", "Total Kills", "Total Deaths", 
            "Total Assists", "Total Revives", "Total Captures"
        ]):
            history_table.horizontalHeaderItem(col).setToolTip(tooltip)
        
        layout.addWidget(history_table)
        self.setLayout(layout)
