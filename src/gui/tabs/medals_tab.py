from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem, 
                           QHeaderView, QGridLayout, QLabel, QFrame)
from PyQt5.QtGui import QColor, QBrush
from PyQt5.QtCore import Qt
import sqlite3

class MedalsTab(QWidget):
    MEDAL_TIERS = {
        'bronze': ("Bronze", QColor(205, 127, 50), "🥉"),
        'silver': ("Silver", QColor(192, 192, 192), "🥈"),
        'gold': ("Gold", QColor(255, 215, 0), "🏅"),
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
        
        # Create headers with emojis
        headers = [
            ("Combat", "⚔️"),
            ("Capture", "🎯"),
            ("Logistics", "🚛"),
            ("Intelligence", "🧠")
        ]
        
        for col, (header, emoji) in enumerate(headers):
            label = QLabel(f"{emoji} {header}")
            label.setAlignment(Qt.AlignCenter)
            label.setStyleSheet("""
                font-weight: bold;
                font-size: 14px;
                padding: 5px;
            """)
            stats_layout.addWidget(label, 0, col + 1)

        # Add tier labels with emojis
        tiers = ["Gold", "Silver", "Bronze"]
        for row, tier in enumerate(tiers):
            medal_emoji = self.MEDAL_TIERS[tier.lower()][2]
            label = QLabel(f"{medal_emoji} {tier}")
            label.setStyleSheet("""
                font-size: 13px;
                padding: 5px;
            """)
            stats_layout.addWidget(label, row + 1, 0)

        # Fill in stats with better formatting
        for row, tier in enumerate(tiers):
            for col, (medal, _) in enumerate(headers):
                count = stats.get(f"{medal.lower()}_{tier.lower()}", 0)
                medal_emoji = self.MEDAL_TIERS[tier.lower()][2]
                label = QLabel(f"{medal_emoji} × {count}" if count > 0 else "-")
                label.setAlignment(Qt.AlignCenter)
                label.setStyleSheet("""
                    font-size: 13px;
                    padding: 5px;
                """)
                stats_layout.addWidget(label, row + 1, col + 1)

        stats_frame.setLayout(stats_layout)
        layout.addWidget(stats_frame)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # First detect the date column
            cursor.execute("PRAGMA table_info(matches)")
            columns = [col[1] for col in cursor.fetchall()]
            date_column = 'match_date' if 'match_date' in columns else 'data'
            
            cursor.execute(f"""
                SELECT 
                    {date_column},
                    map,
                    combat_medal, 
                    capture_medal,
                    logistics_medal,
                    intelligence_medal
                FROM matches
                WHERE name = ?
                ORDER BY {date_column} DESC
            """, (self.player_name,))

            # Create medals table
            self.medals_table = QTableWidget()
            self.medals_table.setColumnCount(6)
            self.medals_table.setHorizontalHeaderLabels([
                "Date", "Map", "Combat", "Capture", 
                "Logistics", "Intelligence"
            ])
        
            data = cursor.fetchall()
        
        self.update_medals_table(data)
        
        # Set column widths
        header = self.medals_table.horizontalHeader()
        for i in range(6):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        
        layout.addWidget(self.medals_table)
        self.setLayout(layout)

    def get_medal_stats(self):
        stats = {}
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for medal in ['combat', 'capture', 'logistics', 'intelligence']:
            for tier in ['gold', 'silver', 'bronze']:
                cursor.execute(f"""
                    SELECT COUNT(*) FROM matches 
                    WHERE name = ? 
                    AND LOWER({medal}_medal) = ?
                """, (self.player_name, tier))
                count = cursor.fetchone()[0]
                stats[f"{medal}_{tier}"] = count
                
        conn.close()
        return stats

    def create_medal_item(self, medal_tier):
        """Create a table item with medal emoji"""
        if medal_tier and medal_tier.lower() in self.MEDAL_TIERS:
            tier_name, color, emoji = self.MEDAL_TIERS[medal_tier.lower()]
            item = QTableWidgetItem(f"{emoji} {tier_name}")
            item.setBackground(QBrush(color))
        else:
            item = QTableWidgetItem("❌")
        item.setTextAlignment(Qt.AlignCenter)
        return item

    def update_medals_table(self, data):
        if data:
            self.medals_table.setRowCount(len(data))
            for row, match_data in enumerate(data):
                # Set match info
                self.medals_table.setItem(row, 0, QTableWidgetItem(str(match_data[0])))
                self.medals_table.setItem(row, 1, QTableWidgetItem(str(match_data[1])))
                
                # Set medal tiers with emojis
                for col in range(2, 6):
                    medal_tier = match_data[col]
                    item = self.create_medal_item(medal_tier)
                    self.medals_table.setItem(row, col, item)
