from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                           QHeaderView, QGridLayout, QLabel, QFrame)
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtCore import Qt
import sqlite3

class MedalsTab(QWidget):
    MEDAL_TIERS = {
        'bronze': ("Bronze", QColor(205, 127, 50)),
        'silver': ("Silver", QColor(192, 192, 192)),
        'gold': ("Gold", QColor(255, 215, 0)),
    }

    def __init__(self, parent, player_name, db_path):
        super().__init__(parent)
        self.player_name = player_name
        self.db_path = db_path
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Add stats summary at the top
        stats_frame = QFrame()
        stats_frame.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        stats_layout = QGridLayout()
        
        # Get medal statistics
        stats = self.get_medal_stats()
        
        # Create headers
        headers = ["Combat", "Capture", "Logistics", "Intelligence"]
        for col, header in enumerate(headers):
            label = QLabel(header)
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("font-weight: bold;")
            stats_layout.addWidget(label, 0, col + 1)

        # Add tier labels
        tiers = ["Gold", "Silver", "Bronze"]
        for row, tier in enumerate(tiers):
            label = QLabel(tier)
            #label.setStyleSheet(f"color: {self.MEDAL_TIERS[tier.lower()][1].name()};")
            stats_layout.addWidget(label, row + 1, 0)

        # Fill in stats
        for row, tier in enumerate(tiers):
            for col, medal in enumerate(headers):
                count = stats.get(f"{medal.lower()}_{tier.lower()}", 0)
                label = QLabel(str(count))
                label.setAlignment(Qt.AlignCenter)
                stats_layout.addWidget(label, row + 1, col + 1)

        stats_frame.setLayout(stats_layout)
        layout.addWidget(stats_frame)
        
        table = QTableWidget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels([
            "Match", "Combat", "Capture", "Logistics", "Intelligence"
        ])
        
        # Get medal data from database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                map || ' - ' || outcome as match_info,
                combat_medal,
                capture_medal,
                logistics_medal,
                intelligence_medal
            FROM matches 
            WHERE player_name = ?
            ORDER BY match_date DESC
        """, (self.player_name,))
        
        data = cursor.fetchall()
        conn.close()
        
        if data:
            table.setRowCount(len(data))
            for row, match_data in enumerate(data):
                # Set match info
                table.setItem(row, 0, QTableWidgetItem(str(match_data[0])))
                
                # Set medal tiers with colors
                for col in range(1, 5):
                    medal_tier = match_data[col]
                    if medal_tier and medal_tier.lower() in self.MEDAL_TIERS:
                        tier_name, color = self.MEDAL_TIERS[medal_tier.lower()]
                        item = QTableWidgetItem(tier_name)
                        item.setBackground(QBrush(color))
                    else:
                        item = QTableWidgetItem("None")
                    table.setItem(row, col, item)
        
        # Set column widths
        header = table.horizontalHeader()
        for i in range(5):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        
        layout.addWidget(table)
        self.setLayout(layout)

    def get_medal_stats(self):
        stats = {}
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for medal in ['combat', 'capture', 'logistics', 'intelligence']:
            for tier in ['gold', 'silver', 'bronze']:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM matches 
                    WHERE player_name = ? 
                    AND LOWER({medal}_medal) = ?
                """, (self.player_name, tier))
                count = cursor.fetchone()[0]
                stats[f"{medal}_{tier}"] = count
                
        conn.close()
        return stats
