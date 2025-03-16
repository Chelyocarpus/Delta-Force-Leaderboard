from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QGroupBox, QGridLayout, 
    QLabel, QScrollArea, QHBoxLayout
)
from PyQt5.QtCore import Qt
import sqlite3


class ClassTab(QWidget):
    def __init__(self, parent=None, player_name=None, db_path=None):
        super().__init__(parent)
        self.player_name = player_name
        self.db_path = db_path
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    class,
                    COUNT(*) as games,
                    SUM(CAST(CASE 
                        WHEN score GLOB '*[0-9]*' AND score NOT GLOB '*[A-Za-z]*'
                        THEN score 
                        ELSE '0' 
                    END AS INTEGER)) as total_score,
                    MAX(CAST(CASE 
                        WHEN score GLOB '*[0-9]*' AND score NOT GLOB '*[A-Za-z]*'
                        THEN score 
                        ELSE '0' 
                    END AS INTEGER)) as best_score,
                    SUM(kills) as total_kills,
                    AVG(kills) as avg_kills,
                    SUM(deaths) as total_deaths,
                    AVG(deaths) as avg_deaths,
                    CAST(SUM(kills) AS FLOAT) / NULLIF(SUM(deaths), 0) as kd_ratio,
                    SUM(assists) as total_assists,
                    AVG(assists) as avg_assists,
                    SUM(revives) as total_revives,
                    AVG(revives) as avg_revives,
                    SUM(captures) as total_captures,
                    AVG(captures) as avg_captures,
                    AVG(rank) as avg_rank,
                    SUM(CASE WHEN outcome LIKE '%VICTORY%' THEN 1 ELSE 0 END) as victories,
                    SUM(CASE WHEN outcome LIKE '%DEFEAT%' THEN 1 ELSE 0 END) as defeats,
                    CAST(
                        SUM(CASE WHEN outcome LIKE '%VICTORY%' THEN 1 ELSE 0 END) * 100.0 / 
                        NULLIF(COUNT(*), 0) AS FLOAT
                    ) as win_rate,
                    SUM(CAST(vehicle_damage as INTEGER)) as total_vehicle_damage,
                    AVG(CAST(vehicle_damage as INTEGER)) as avg_vehicle_damage,
                    SUM(CAST(tactical_respawn as INTEGER)) as total_tactical_respawn,
                    AVG(CAST(tactical_respawn as INTEGER)) as avg_tactical_respawn
                FROM matches
                WHERE name = ? AND class != ''
                GROUP BY class
            """, (self.player_name,))

            # Debug print to check what's being returned
            print(f"Class stats for {self.player_name}:")
            results = cursor.fetchall()
            for row in results:
                print(row)
                
            class_stats_dict = {row[0]: row for row in results}
            
            from ...utils.constants import PLAYER_CLASSES
            # Create class groups in the specified order
            for class_name in PLAYER_CLASSES:
                # Show all classes even with no data
                class_data = class_stats_dict.get(class_name, [0] * 23)  # Updated for new fields
                class_group = QGroupBox(class_name)
                class_layout = QGridLayout()
                class_layout.setAlignment(Qt.AlignTop)  # Align contents to top
                
                # Reorganized stat groups to match overall tab
                stat_groups = {
                    "Match Performance": [
                        ("Games Played:", class_data[1]),
                        ("Victories:", class_data[16]),
                        ("Defeats:", class_data[17]),
                        ("Win Rate:", f"{class_data[18]:.1f}%"),
                        ("Average Rank:", int(class_data[15]))
                    ],
                    "Combat Performance": [
                        ("Total Score:", class_data[2]),  # This is now total_score
                        ("Average Score:", int(class_data[2] / class_data[1]) if class_data[1] > 0 else 0),  # Calculate average from total
                        ("Best Score:", class_data[3])  # This is now best_score
                    ],
                    "Combat Performance": [
                        ("Total Kills:", class_data[4]),
                        ("Average Kills:", int(class_data[5])),
                        ("Total Deaths:", class_data[6]),
                        ("Average Deaths:", int(class_data[7])),
                        ("K/D Ratio:", f"{class_data[8]:.2f}"),
                        ("Total Vehicle Damage:", class_data[19]),
                        ("Average Vehicle Damage:", int(class_data[20]))
                    ],
                    "Support Performance": [
                        ("Total Assists:", class_data[9]),
                        ("Average Assists:", int(class_data[10])),
                        ("Total Revives:", class_data[11]),
                        ("Average Revives:", int(class_data[12])),
                        ("Total Tactical Respawns:", class_data[21]),
                        ("Average Tactical Respawns:", int(class_data[22]))
                    ],
                    "Objective Performance": [
                        ("Total Captures:", class_data[13]),
                        ("Average Captures:", int(class_data[14]))
                    ]
                }
                
                # Create stat boxes with improved layout
                for idx, (group_name, stats) in enumerate(stat_groups.items()):
                    sub_group = QGroupBox(group_name)
                    sub_layout = QGridLayout()
                    sub_layout.setAlignment(Qt.AlignTop)
                    
                    for i, (label, value) in enumerate(stats):
                        sub_layout.addWidget(QLabel(label), i, 0)
                        formatted_value = self.format_value(value, label)
                        value_label = QLabel(formatted_value)
                        value_label.setAlignment(Qt.AlignLeft)
                        sub_layout.addWidget(value_label, i, 1)
                    
                    sub_group.setLayout(sub_layout)
                    class_layout.addWidget(sub_group, idx // 3, idx % 3)
                
                class_group.setLayout(class_layout)
                layout.addWidget(class_group)
        
        # Create a scroll area to handle overflow
        scroll = QScrollArea()
        scroll_widget = QWidget()
        scroll_widget.setLayout(layout)
        scroll.setWidget(scroll_widget)
        scroll.setWidgetResizable(True)
        
        # Create a container layout for the scroll area
        container_layout = QVBoxLayout()
        container_layout.addWidget(scroll)
        self.setLayout(container_layout)

    def format_value(self, value, label):
        """Helper method to format values consistently"""
        if isinstance(value, float):
            if "K/D Ratio" in label:
                return f"{value:.2f}"
            elif "Win Rate" in label:
                return f"{value:.1f}%"
            return f"{int(value)}"  # Round all other floats to integers
        return str(value)
