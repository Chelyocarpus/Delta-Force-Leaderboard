from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                           QGridLayout, QLabel, QComboBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor, QFont
from PyQt5.QtChart import (QPieSeries, QChart, QChartView, QPieSlice)
import sqlite3
import logging

logger = logging.getLogger(__name__)

class AttackerTab(QWidget):
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
        self.map_combo.addItem("All Maps")  # Add default option
        self.load_maps()  # Load available maps
        self.map_combo.currentTextChanged.connect(self.update_stats)
        filter_layout.addWidget(self.map_combo)
        filter_layout.addStretch()
        layout.addLayout(filter_layout)

        # Create combat efficiency chart
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

        # Create pie series with hole to make it a donut
        self.efficiency_series = QPieSeries()
        self.efficiency_series.setHoleSize(0.45)  # Set hole size for donut chart
        kills_slice = self.efficiency_series.append("Kills", 0)
        deaths_slice = self.efficiency_series.append("Deaths", 0)

        # Enhanced styling with better colors
        kills_slice.setBrush(QColor(76, 175, 80))  # Vibrant green for kills
        deaths_slice.setBrush(QColor(244, 67, 54))  # Vibrant red for deaths
        
        # Style all slices consistently
        for slice in self.efficiency_series.slices():
            slice.setLabelVisible(True)
            slice.setExploded(False)  # Disable explosion for cleaner donut look
            slice.setLabelPosition(QPieSlice.LabelOutside)  # Place labels outside
            slice.setLabelArmLengthFactor(0.15)  # Shorter arm length for cleaner appearance
            slice.setLabelFont(QFont("Arial", 9, QFont.Bold))  # Bold font for labels
            slice.setPen(QColor(240, 240, 240))  # Light border between slices

        # Create and configure chart
        chart = QChart()
        chart.addSeries(self.efficiency_series)
        chart.setAnimationOptions(QChart.SeriesAnimations)
        chart.legend().setVisible(False)  # Hide legend as we have labels
        chart.setBackgroundVisible(False)
        chart.setMinimumSize(300, 200)

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
                ("K/D Ratio", "kd_ratio"),
                ("Total Vehicle Damage", "vehicle_damage_total"),    # Added
                ("Average Vehicle Damage", "vehicle_damage_avg"),    # Added
            ],
            "Match Performance": [
                ("Total Games", "games_total"),
                ("Victories", "victories"),
                ("Win Rate", "win_rate", "%"),
                ("Average Rank", "avg_rank"),
            ],
            "Score Performance": [
                ("Total Score", "score_total"),
                ("Average Score", "score_avg"),
                ("Best Score", "score_best"),
            ],
            "Support Performance": [
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
            ],
            "Ticket Performance": [                    # Moved to last position
                ("Tickets Lost", "tickets_lost"),     
                ("Tickets Saved", "tickets_saved"),   
                ("Net Ticket Impact", "tickets_net"), 
                ("Ticket Save Ratio", "tickets_ratio"),
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
        # Disable UI updates temporarily
        self.setUpdatesEnabled(False)
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            map_filter = "AND map = ?" if map_name and map_name != "All Maps" else ""
            query_params = [self.player_name]
            if map_filter:
                query_params.append(map_name)

            cursor.execute(f"""
                WITH attacker_stats AS (
                    SELECT * FROM matches 
                    WHERE name = ? 
                     AND LOWER(team) = LOWER('Attack')
                    {map_filter}
                )
                SELECT 
                    -- Combat Performance
                    SUM(kills) as kills_total,
                    ROUND(AVG(CAST(kills AS FLOAT)), 1) as kills_avg,
                    MAX(kills) as kills_best,
                    SUM(deaths) as deaths_total,
                    ROUND(AVG(CAST(deaths AS FLOAT)), 1) as deaths_avg,
                    ROUND(CAST(SUM(kills) AS FLOAT) / NULLIF(SUM(deaths), 0), 2) as kd_ratio,
                    SUM(COALESCE(vehicle_damage, 0)) as vehicle_damage_total,
                    ROUND(AVG(COALESCE(vehicle_damage, 0)), 1) as vehicle_damage_avg,
                    
                    -- Match Stats
                    COUNT(*) as games_total,
                    SUM(CASE WHEN outcome = 'VICTORY' THEN 1 ELSE 0 END) as victories,
                    ROUND(CAST(SUM(CASE WHEN outcome = 'VICTORY' THEN 1 ELSE 0 END) AS FLOAT) * 100.0 / NULLIF(COUNT(*), 0), 1) as win_rate,
                    ROUND(AVG(CAST(rank AS FLOAT)), 1) as avg_rank,
                    
                    -- Score Analysis
                    SUM(score) as score_total,
                    ROUND(AVG(CAST(score AS FLOAT)), 1) as score_avg,
                    MAX(score) as score_best,
                    
                    -- Support Activities
                    SUM(assists) as assists_total,
                    ROUND(AVG(CAST(assists AS FLOAT)), 1) as assists_avg,
                    SUM(revives) as revives_total,
                    ROUND(AVG(CAST(revives AS FLOAT)), 1) as revives_avg,
                    SUM(COALESCE(tactical_respawn, 0)) as tactical_respawn_total,
                    ROUND(AVG(COALESCE(tactical_respawn, 0)), 1) as tactical_respawn_avg,
                    
                    -- Objective Performance
                    SUM(captures) as captures_total,
                    ROUND(AVG(CAST(captures AS FLOAT)), 1) as captures_avg,
                    MAX(captures) as captures_best,
                    
                    -- Ticket Management
                    SUM(deaths) as tickets_lost,
                    SUM(revives) as tickets_saved,
                    SUM(revives) - SUM(deaths) as tickets_net,
                    ROUND(CAST(SUM(revives) AS FLOAT) / NULLIF(SUM(deaths), 0), 3) as tickets_ratio,
                    
                    -- For pie chart
                    SUM(kills) as total_k,
                    SUM(deaths) as total_d
                FROM attacker_stats
            """, query_params)
            
            stats = cursor.fetchone()
            
            if stats:
                # Collect all stats updates first
                stat_updates = {}
                for i, key in enumerate(self.stat_labels.keys()):
                    value = stats[i] if stats[i] is not None else "--"
                    
                    if isinstance(value, (int, float)):
                        if key == "win_rate":
                            formatted_value = f"{value:.1f}"
                        elif key in ["kd_ratio", "tickets_ratio"]:
                            formatted_value = f"{value:.2f}"
                        else:
                            formatted_value = f"{int(value):,}"
                    else:
                        formatted_value = str(value)
                        
                    if key == "win_rate":
                        formatted_value += "%"
                        
                    stat_updates[key] = formatted_value

                # Apply all stat updates at once
                for key, value in stat_updates.items():
                    self.stat_labels[key].setText(value)

                # Update chart values with improved handling of null values
                total_kills = stats[-2] or 0
                total_deaths = stats[-1] or 0
                
                # Update pie slices with values and formatted labels
                self.efficiency_series.slices()[0].setValue(total_kills)
                self.efficiency_series.slices()[1].setValue(total_deaths)
                self.efficiency_series.slices()[0].setLabel(f"Kills ({total_kills:,})")
                self.efficiency_series.slices()[1].setLabel(f"Deaths ({total_deaths:,})")
                
                # If both values are zero, set some minimum values to avoid empty chart
                if total_kills == 0 and total_deaths == 0:
                    self.efficiency_series.slices()[0].setValue(1)
                    self.efficiency_series.slices()[1].setValue(1)

        # Re-enable UI updates
        self.setUpdatesEnabled(True)

def setup_attacker_tab(dialog):
    dialog.attacker_tab = AttackerTab(dialog, dialog.player_name, dialog.parent.db.db_path)
