from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                           QGridLayout, QLabel, QComboBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor, QFont
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

        self.efficiency_series = QPieSeries()
        self.efficiency_series.setHoleSize(0.45)  # Set hole size to create donut chart
        kills_slice = self.efficiency_series.append("Kills", 0)
        deaths_slice = self.efficiency_series.append("Deaths", 0)

        # Enhanced styling with better colors
        kills_slice.setBrush(QColor(76, 175, 80))  # Vibrant green for kills
        deaths_slice.setBrush(QColor(244, 67, 54))  # Vibrant red for deaths
        
        # Style all slices
        for pie_slice in self.efficiency_series.slices():
            pie_slice.setLabelVisible(True)
            pie_slice.setExploded(False)  # Disable explosion for cleaner donut
            pie_slice.setLabelPosition(QPieSlice.LabelOutside)  # Place labels outside
            pie_slice.setLabelArmLengthFactor(0.15)  # Shorter arm length
            pie_slice.setLabelFont(QFont("Arial", 9, QFont.Bold))  # Bold font for better visibility
            pie_slice.setPen(QColor(240, 240, 240))  # Light border between slices

        # Create and configure chart
        chart = QChart()
        chart.addSeries(self.efficiency_series)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.legend().setVisible(False)  # Hide legend as we have labels
        chart.setBackgroundVisible(False)
        chart.setMinimumSize(300, 200)
        chart.setTitle("") # Remove title as we have the group box title

        # Create chart view with antialiasing
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

    def format_stat_value(self, value, key):
        if value is None:
            return "--"
        
        if isinstance(value, (int, float)):
            return (
                f"{value:.2f}" if key.endswith(('rate')) or key == 'kd_ratio'
                else f"{int(value):,}"
            )
        return str(value)

    def get_stats_query(self, map_name):
        map_filter = "AND map = ?" if map_name and map_name != "All Maps" else ""
        query_params = [self.player_name]
        if map_filter:
            query_params.append(map_name)
            
        query = f"""
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
        """
        return query, query_params

    def update_chart(self, kills, deaths):
        kills = kills or 0
        deaths = deaths or 0
        
        # Update pie slices with values and labels
        self.efficiency_series.slices()[0].setValue(kills)
        self.efficiency_series.slices()[1].setValue(deaths)
        
        # Update labels with count information
        self.efficiency_series.slices()[0].setLabel(f"Kills ({kills:,})")
        self.efficiency_series.slices()[1].setLabel(f"Deaths ({deaths:,})")
        
        # If both values are zero, set some minimum values to avoid empty chart
        if kills == 0 and deaths == 0:
            self.efficiency_series.slices()[0].setValue(1)
            self.efficiency_series.slices()[1].setValue(1)

    def update_stat_labels(self, stats):
        column_names = list(self.stat_labels.keys())
        for i, key in enumerate(column_names):
            value = self.format_stat_value(stats[i], key)
            value += "%" if key.endswith('rate') else ""
            self.stat_labels[key].setText(value)

    def update_stats(self, map_name=None):
        self.setUpdatesEnabled(False)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                query, params = self.get_stats_query(map_name)
                
                logger.debug(f"Executing query for player: {self.player_name}")
                logger.debug(f"Map filter: {map_name if map_name else 'None'}")

                cursor.execute(query, params)
                if stats := cursor.fetchone():
                    self.update_chart(stats[-2], stats[-1])
                    self.update_stat_labels(stats)

        except Exception as e:
            logger.error(f"Error updating stats: {str(e)}")
            raise
        finally:
            self.setUpdatesEnabled(True)
            self.update()
