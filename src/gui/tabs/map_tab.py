from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
                           QGroupBox, QGridLayout, QLabel, QFrame)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QPainter, QColor
from PyQt5.QtChart import (QPieSeries, QChart, QChartView, QPieSlice)
import sqlite3

class MapTab(QWidget):
    def __init__(self, parent=None, player_name=None, db_path=None):
        super().__init__(parent)
        self.player_name = player_name
        self.db_path = db_path
        self.stat_labels = {}  # Store labels for updating
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Create map selector
        selector_layout = QHBoxLayout()
        selector_layout.addWidget(QLabel("Select Map:"))
        self.map_combo = QComboBox()
        self.map_combo.currentTextChanged.connect(self.update_stats)
        selector_layout.addWidget(self.map_combo)
        selector_layout.addStretch()
        layout.addLayout(selector_layout)

        # Add win/loss chart section
        self.wins_chart = self.create_wins_chart()
        layout.addWidget(self.wins_chart)

        # Create stat groups
        self.create_stat_groups(layout)
        
        # Load maps and initial stats
        self.load_maps()
        
        self.setLayout(layout)

    def create_stat_groups(self, parent_layout):
        stats_layout = QGridLayout()
        stats_layout.setSpacing(10)
        
        # Define stat groups
        groups = {
            "General": [
                ("Total Games", "games_played"),
                ("Win Rate", "win_rate", "%"),
                ("Average Rank", "avg_rank"),
            ],
            "Combat": [
                ("Average Score", "avg_score"),
                ("Best Score", "best_score"),
                ("Average Kills", "avg_kills"),
                ("Best Kills", "best_kills"),
                ("Average Deaths", "avg_deaths"),
                ("K/D Ratio", "kd_ratio"),
                ("Total Vehicle Damage", "total_vehicle_damage"),
                ("Average Vehicle Damage", "avg_vehicle_damage"),
            ],
            "Support": [
                ("Average Assists", "avg_assists"),
                ("Best Assists", "best_assists"),
                ("Average Revives", "avg_revives"),
                ("Best Revives", "best_revives"),
                ("Total Tactical Respawns", "total_tactical_respawn"),
                ("Average Tactical Respawns", "avg_tactical_respawn"),
            ],
            "Objective": [
                ("Average Captures", "avg_captures"),
                ("Best Captures", "best_captures")
            ]
        }

        # Create group boxes
        row = 0
        col = 0
        for group_name, stats in groups.items():
            group = QGroupBox(group_name)
            group_layout = QGridLayout()
            group_layout.setSpacing(2)  # Reduce space between stats
            group_layout.setContentsMargins(10, 10, 10, 10)  # Reduce margins
            group_layout.setAlignment(Qt.AlignTop)  # Align contents to top

            for i, stat in enumerate(stats):
                label = QLabel(stat[0] + ":")
                value_label = QLabel("--")
                value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                
                # Set alignment for individual labels
                label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
                value_label.setAlignment(Qt.AlignRight | Qt.AlignTop)
                
                # Store reference to value label
                self.stat_labels[stat[1]] = value_label
                
                group_layout.addWidget(label, i, 0)
                group_layout.addWidget(value_label, i, 1)

            group.setLayout(group_layout)
            stats_layout.addWidget(group, row, col)
            
            col += 1
            if col > 1:  # 2 columns
                col = 0
                row += 1

        parent_layout.addLayout(stats_layout)

    def create_wins_chart(self):
        # Create chart container
        chart_group = QGroupBox("Victory Distribution")
        chart_layout = QHBoxLayout()
        chart_layout.setContentsMargins(5, 5, 5, 5)

        # Create pie series and set hole size for donut
        self.pie_series = QPieSeries()
        self.pie_series.setHoleSize(0.35)
        victory_slice = self.pie_series.append("Victories", 0)
        defeat_slice = self.pie_series.append("Defeats", 0)

        # Style the donut slices
        victory_slice.setBrush(QColor(100, 200, 100))
        defeat_slice.setBrush(QColor(200, 100, 100))
        
        # Set new label properties for each slice
        for slice in self.pie_series.slices():
            slice.setLabelVisible(True)
            slice.setExploded(True)
            slice.setExplodeDistanceFactor(0.1)
            # Changed label arm behavior
            slice.setLabelArmLengthFactor(0.2)  # Shorter arms
            slice.setLabelPosition(QPieSlice.LabelInsideNormal)  # Start labels inside
            # Use horizontal arms instead of angled
            slice.setLabelPosition(QPieSlice.LabelInsideHorizontal)

        chart = QChart()
        chart.addSeries(self.pie_series)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.legend().setVisible(False)
        chart.setBackgroundVisible(False)
        chart.setMinimumSize(300, 200)  # Set minimum size to prevent squishing

        # Create chart view
        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)
        chart_view.setMinimumHeight(200)

        chart_layout.addWidget(chart_view)
        chart_group.setLayout(chart_layout)
        return chart_group

    def load_maps(self):
        """Load map data from database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Get list of maps played by player
            cursor.execute("""
                SELECT DISTINCT map
                FROM matches
                WHERE name = ?
                ORDER BY map
            """, (self.player_name,))
            
            maps = [row[0] for row in cursor.fetchall()]
            
        self.map_combo.addItems(maps)

    def update_stats(self, map_name):
        if not map_name:
            return

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get win/loss stats first
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN outcome LIKE '%VICTORY%' THEN 1 ELSE 0 END) as victories,
                    SUM(CASE WHEN outcome LIKE '%DEFEAT%' THEN 1 ELSE 0 END) as defeats
                FROM matches
                WHERE name = ? AND map = ?
            """, (self.player_name, map_name))
            
            wins_data = cursor.fetchone()
            if wins_data:
                victories, defeats = wins_data
                # Update pie chart
                self.pie_series.slices()[0].setValue(victories or 0)
                self.pie_series.slices()[1].setValue(defeats or 0)
                
                # Update labels to show counts
                self.pie_series.slices()[0].setLabel(f"Victories ({victories or 0})")
                self.pie_series.slices()[1].setLabel(f"Defeats ({defeats or 0})")

            # Rest of the stats query
            cursor.execute("""
                SELECT 
                    COUNT(*) as games_played,
                    ROUND(SUM(CASE WHEN outcome LIKE '%VICTORY%' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as win_rate,
                    ROUND(AVG(CAST(rank AS FLOAT)), 1) as avg_rank,
                    ROUND(AVG(score), 1) as avg_score,
                    MAX(score) as best_score,
                    ROUND(AVG(kills), 1) as avg_kills,
                    MAX(kills) as best_kills,
                    ROUND(AVG(deaths), 1) as avg_deaths,
                    ROUND(CAST(SUM(kills) AS FLOAT) / CASE WHEN SUM(deaths) = 0 THEN 1 ELSE SUM(deaths) END, 2) as kd_ratio,
                    SUM(COALESCE(vehicle_damage, 0)) as total_vehicle_damage,
                    ROUND(AVG(COALESCE(vehicle_damage, 0)), 1) as avg_vehicle_damage,
                    ROUND(AVG(assists), 1) as avg_assists,
                    MAX(assists) as best_assists,
                    ROUND(AVG(revives), 1) as avg_revives,
                    MAX(revives) as best_revives,
                    SUM(COALESCE(tactical_respawn, 0)) as total_tactical_respawn,
                    ROUND(AVG(COALESCE(tactical_respawn, 0)), 1) as avg_tactical_respawn,
                    ROUND(AVG(captures), 1) as avg_captures,
                    MAX(captures) as best_captures
                FROM matches
                WHERE name = ? AND map = ?
            """, (self.player_name, map_name))
            
            stats = cursor.fetchone()
            
            # Update all stat labels
            for i, key in enumerate(self.stat_labels.keys()):
                value = stats[i] if stats else "--"
                
                # Format numbers based on stat type
                if isinstance(value, (int, float)):
                    if key in ["win_rate", "kd_ratio"]:
                        formatted_value = f"{value:.1f}"
                    else:
                        formatted_value = f"{int(value):,}"
                else:
                    formatted_value = str(value)
                    
                # Add % to win rate
                if key == "win_rate":
                    formatted_value += "%"
                    
                self.stat_labels[key].setText(formatted_value)
