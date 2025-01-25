from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                           QGridLayout, QLabel, QComboBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor
from PyQt5.QtChart import (QPieSeries, QChart, QChartView, QPieSlice)
import sqlite3
import logging

logger = logging.getLogger(__name__)

class DefenderTab(QWidget):
    def __init__(self, parent, player_name, db_path):
        super().__init__(parent)
        self.player_name = player_name
        self.db_path = db_path
        self.stat_labels = {}
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # Add map filter
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filter by Map:"))
        self.map_combo = QComboBox()
        self.map_combo.addItem("All Maps")
        self.load_maps()
        self.map_combo.currentTextChanged.connect(self.update_stats)
        filter_layout.addWidget(self.map_combo)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Create survival efficiency chart
        self.efficiency_chart = self.create_efficiency_chart()
        layout.addWidget(self.efficiency_chart)

        # Create detailed stats section
        self.create_stat_groups(layout)
        
        # Load initial stats
        self.update_stats()
        
        self.setLayout(layout)

    def create_efficiency_chart(self):
        group = QGroupBox("Combat Efficiency")
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)

        # Create pie chart for K/D ratio visualization
        self.efficiency_series = QPieSeries()
        kills_slice = self.efficiency_series.append("Kills", 0)
        deaths_slice = self.efficiency_series.append("Deaths", 0)

        # Style slices
        kills_slice.setBrush(QColor(100, 200, 100))
        deaths_slice.setBrush(QColor(200, 100, 100))
        
        for slice in self.efficiency_series.slices():
            slice.setLabelVisible(True)
            slice.setExploded(True)
            slice.setExplodeDistanceFactor(0.1)
            slice.setLabelPosition(QPieSlice.LabelOutside)

        chart = QChart()
        chart.addSeries(self.efficiency_series)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.legend().setVisible(False)
        chart.setBackgroundVisible(False)
        chart.setMinimumSize(300, 200)

        chart_view = QChartView(chart)
        chart_view.setRenderHint(QPainter.Antialiasing)
        chart_view.setMinimumHeight(200)

        layout.addWidget(chart_view)
        group.setLayout(layout)
        return group

    def create_stat_groups(self, parent_layout):
        stats_layout = QGridLayout()
        stats_layout.setSpacing(10)

        groups = {
            "Combat Performance": [
                ("Total Kills", "kills_total"),
                ("Average Kills", "kills_avg"),
                ("Best Kills", "kills_best"),
                ("Total Deaths", "deaths_total"),
                ("Average Deaths", "deaths_avg"),
                ("K/D Ratio", "kd_ratio"),  # Make sure this matches the SQL query column name
                ("Total Vehicle Damage", "vehicle_damage_total"),    # Added
                ("Average Vehicle Damage", "vehicle_damage_avg"),    # Added
            ],
            "Match Stats": [
                ("Total Games", "games_total"),
                ("Victories", "victories"),
                ("Win Rate", "win_rate", "%"),
                ("Average Rank", "avg_rank"),
            ],
            "Score Analysis": [
                ("Total Score", "score_total"),
                ("Average Score", "score_avg"),
                ("Best Score", "score_best"),
            ],
            "Support Activities": [
                ("Total Assists", "assists_total"),
                ("Average Assists", "assists_avg"),
                ("Total Revives", "revives_total"),
                ("Average Revives", "revives_avg"),
                ("Total Tactical Respawns", "tactical_respawn_total"),    # Added
                ("Average Tactical Respawns", "tactical_respawn_avg"),    # Added
            ],
            "Objective Performance": [
                ("Total Captures", "captures_total"),
                ("Average Captures", "captures_avg"),
                ("Best Captures", "captures_best"),
            ]
        }

        # Create group boxes with 3-column layout
        for idx, (group_name, stats) in enumerate(groups.items()):
            group = QGroupBox(group_name)
            group_layout = QGridLayout()
            group_layout.setSpacing(2)
            group_layout.setContentsMargins(10, 10, 10, 10)
            group_layout.setAlignment(Qt.AlignTop)

            for i, stat in enumerate(stats):
                label = QLabel(stat[0] + ":")
                value_label = QLabel("--")
                label.setAlignment(Qt.AlignLeft | Qt.AlignTop)
                value_label.setAlignment(Qt.AlignRight | Qt.AlignTop)
                
                self.stat_labels[stat[1]] = value_label
                
                group_layout.addWidget(label, i, 0)
                group_layout.addWidget(value_label, i, 1)

            group.setLayout(group_layout)
            
            # Arrange groups in a 2x3 grid
            row = idx // 3
            col = idx % 3
            stats_layout.addWidget(group, row, col)

        parent_layout.addLayout(stats_layout)

    def load_maps(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT map 
                FROM matches 
                WHERE name = ? 
                ORDER BY map
            """, (self.player_name,))
            maps = [row[0] for row in cursor.fetchall()]
            self.map_combo.addItems(maps)

    def update_stats(self, map_name=None):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            map_filter = "AND map = ?" if map_name and map_name != "All Maps" else ""
            query_params = [self.player_name]
            if map_filter:
                query_params.append(map_name)

            # Add debug logging
            logger.debug(f"Executing query for player: {self.player_name}")
            logger.debug(f"Map filter: {map_filter}")

            cursor.execute(f"""
                WITH defender_stats AS (
                    SELECT * FROM matches 
                    WHERE name = ? 
                    AND LOWER(team) = LOWER('Defense')
                    {map_filter}
                )
                SELECT 
                    SUM(kills) as kills_total,
                    ROUND(AVG(kills), 1) as kills_avg,
                    MAX(kills) as kills_best,
                    SUM(deaths) as deaths_total,
                    ROUND(AVG(deaths), 1) as deaths_avg,
                    ROUND(CAST(SUM(kills) AS FLOAT) / NULLIF(SUM(deaths), 0), 2) as kd_ratio,
                    SUM(COALESCE(vehicle_damage, 0)) as vehicle_damage_total,
                    ROUND(AVG(COALESCE(vehicle_damage, 0)), 1) as vehicle_damage_avg,
                    COUNT(*) as games_total,
                    SUM(CASE WHEN outcome LIKE '%VICTORY%' THEN 1 ELSE 0 END) as victories,
                    ROUND(SUM(CASE WHEN outcome LIKE '%VICTORY%' THEN 1 ELSE 0 END) * 100.0 / COUNT(*), 1) as win_rate,
                    ROUND(AVG(CAST(rank AS FLOAT)), 1) as avg_rank,
                    SUM(score) as score_total,
                    ROUND(AVG(score), 1) as score_avg,
                    MAX(score) as score_best,
                    SUM(assists) as assists_total,
                    ROUND(AVG(assists), 1) as assists_avg,
                    SUM(revives) as revives_total,
                    ROUND(AVG(revives), 1) as revives_avg,
                    SUM(COALESCE(tactical_respawn, 0)) as tactical_respawn_total,
                    ROUND(AVG(COALESCE(tactical_respawn, 0)), 1) as tactical_respawn_avg,
                    SUM(captures) as captures_total,
                    ROUND(AVG(captures), 1) as captures_avg,
                    MAX(captures) as captures_best,
                    SUM(kills) as total_k,
                    SUM(deaths) as total_d
                FROM defender_stats
            """, query_params)
            
            stats = cursor.fetchone()
            
            if stats:
                # Add debug logging for K/D ratio
                logger.debug(f"K/D Ratio value from query: {stats[5]}")  # Index 5 corresponds to kd_ratio in query

                # Update efficiency chart with kills/deaths
                total_kills, total_deaths = stats[-2], stats[-1]
                self.efficiency_series.slices()[0].setValue(total_kills or 0)
                self.efficiency_series.slices()[1].setValue(total_deaths or 0)
                self.efficiency_series.slices()[0].setLabel(f"Kills ({total_kills or 0})")
                self.efficiency_series.slices()[1].setLabel(f"Deaths ({total_deaths or 0})")
                
                # Update stat labels
                for i, key in enumerate(self.stat_labels.keys()):
                    value = stats[i] if stats[i] is not None else "--"
                    
                    if isinstance(value, (int, float)):
                        if key.endswith(('rate')) or key == 'kd_ratio':  # Add special handling for kd_ratio
                            formatted_value = f"{value:.2f}"  # Use 2 decimal places for K/D ratio
                        else:
                            formatted_value = f"{int(value):,}"
                    else:
                        formatted_value = str(value)
                        
                    if key.endswith('rate'):
                        formatted_value += "%"

                    self.stat_labels[key].setText(formatted_value)
