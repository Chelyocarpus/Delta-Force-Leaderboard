from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
    QComboBox, QGroupBox, QGridLayout
)
import sqlite3

class MapTab(QWidget):
    def __init__(self, parent=None, player_name=None, db_path=None):
        super().__init__(parent)
        self.player_name = player_name
        self.db_path = db_path
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        # Create map selector
        selector_layout = QHBoxLayout()
        self.map_combo = QComboBox()
        selector_layout.addWidget(QLabel("Select Map:"))
        selector_layout.addWidget(self.map_combo)
        layout.addLayout(selector_layout)
        
        # Create stats group
        self.map_stats_group = QGroupBox("Map Statistics")
        self.map_stats_layout = QGridLayout()
        self.map_stats_group.setLayout(self.map_stats_layout)
        layout.addWidget(self.map_stats_group)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT SUBSTR(snapshot_name, INSTR(snapshot_name, ' - ') + 3, 
                    INSTR(snapshot_name, ' (') - INSTR(snapshot_name, ' - ') - 3) as map_name
                FROM snapshots
                WHERE name = ?
                ORDER BY map_name
            """, (self.player_name,))
            maps = cursor.fetchall()
            
            for map_name in maps:
                self.map_combo.addItem(map_name[0])
        
        # Connect map selection change event
        self.map_combo.currentTextChanged.connect(self.load_map_stats)
        
        # Load initial map stats if any maps exist
        if self.map_combo.count() > 0:
            self.load_map_stats(self.map_combo.currentText())
        
        self.setLayout(layout)

    def format_value(self, value, label):
        """Helper method to format values consistently"""
        if isinstance(value, float):
            if "Ratio" in label:
                return f"{value:.2f}"
            elif "%" in label:
                return f"{value:.1f}%"
            else:
                return f"{int(value)}"
        return str(value)

    def load_map_stats(self, map_name):
        # Clear existing stats
        while self.map_stats_layout.count():
            child = self.map_stats_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
                
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    COUNT(*) as games,
                    ROUND(AVG(score)) as avg_score,
                    MAX(score) as best_score,
                    SUM(kills) as total_kills,
                    ROUND(AVG(kills), 1) as avg_kills,
                    SUM(deaths) as total_deaths,
                    ROUND(AVG(deaths), 1) as avg_deaths,
                    ROUND(CAST(SUM(kills) AS FLOAT) / 
                          CASE WHEN SUM(deaths) = 0 THEN 1 
                          ELSE SUM(deaths) END, 2) as kd_ratio,
                    SUM(assists) as total_assists,
                    ROUND(AVG(assists), 1) as avg_assists,
                    SUM(revives) as total_revives,
                    ROUND(AVG(revives), 1) as avg_revives,
                    SUM(captures) as total_captures,
                    ROUND(AVG(captures), 1) as avg_captures,
                    ROUND(AVG(rank)) as avg_rank,
                    SUM(CASE WHEN snapshot_name LIKE '%(VICTORY)%' THEN 1 ELSE 0 END) as victories,
                    SUM(CASE WHEN snapshot_name LIKE '%(DEFEAT)%' THEN 1 ELSE 0 END) as defeats,
                    ROUND(CAST(SUM(CASE WHEN snapshot_name LIKE '%(VICTORY)%' THEN 1 ELSE 0 END) AS FLOAT) * 100 /
                        (SUM(CASE WHEN snapshot_name LIKE '%(VICTORY)%' THEN 1 ELSE 0 END) + 
                         SUM(CASE WHEN snapshot_name LIKE '%(DEFEAT)%' THEN 1 ELSE 0 END)), 1) as win_rate
                FROM snapshots
                WHERE name = ? AND snapshot_name LIKE ? || ' (%'
            """, (self.player_name, f"% - {map_name}"))
            stats = cursor.fetchone()
            
            # Organize stats into groups
            stat_groups = {
                "General": [
                    ("Games Played:", stats[0]),
                    ("Average Rank:", stats[14]),
                    ("Victories:", stats[15]),
                    ("Defeats:", stats[16]),
                    ("Win Rate:", f"{stats[17]}%")
                ],
                "Score": [
                    ("Average Score:", stats[1]),
                    ("Best Score:", stats[2])
                ],
                "Combat": [
                    ("Total Kills:", stats[3]),
                    ("Average Kills:", stats[4]),
                    ("Total Deaths:", stats[5]),
                    ("Average Deaths:", stats[6]),
                    ("K/D Ratio:", stats[7])
                ],
                "Support": [
                    ("Total Assists:", stats[8]),
                    ("Average Assists:", stats[9]),
                    ("Total Revives:", stats[10]),
                    ("Average Revives:", stats[11])
                ],
                "Objectives": [
                    ("Total Captures:", stats[12]),
                    ("Average Captures:", stats[13])
                ]
            }
            
            # Create group boxes for each category
            row = 0
            for group_name, group_stats in stat_groups.items():
                group_box = QGroupBox(group_name)
                group_layout = QGridLayout()
                
                for i, (label, value) in enumerate(group_stats):
                    group_layout.addWidget(QLabel(label), i, 0)
                    formatted_value = self.format_value(value, label)
                    group_layout.addWidget(QLabel(formatted_value), i, 1)
                
                group_box.setLayout(group_layout)
                self.map_stats_layout.addWidget(group_box, row // 2, row % 2)
                row += 1
