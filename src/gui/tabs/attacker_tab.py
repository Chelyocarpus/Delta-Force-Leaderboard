from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                           QGridLayout, QLabel, QComboBox)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPainter, QColor
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
                ("K/D Ratio", "kd_ratio"),
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
            ],
            "Objective Performance": [
                ("Total Captures", "captures_total"),
                ("Average Captures", "captures_avg"),
                ("Best Captures", "captures_best"),
            ],
            "Ticket Management": [                    # Moved to last position
                ("Tickets Lost", "tickets_lost"),     
                ("Tickets Saved", "tickets_saved"),   
                ("Net Ticket Impact", "tickets_net"), 
                ("Ticket Save Ratio", "tickets_ratio"),
            ]
        }

        row = 0
        col = 0
        for group_name, stats in groups.items():
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
            stats_layout.addWidget(group, row, col)
            
            col += 1
            if col > 1:
                col = 0
                row += 1

        parent_layout.addLayout(stats_layout)

    def load_maps(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT map 
                FROM matches 
                WHERE player_name = ? 
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

            cursor.execute(f"""
                WITH attacker_stats AS (
                    SELECT * FROM matches 
                    WHERE player_name = ? 
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
                # Update efficiency chart
                total_kills, total_deaths = stats[-2], stats[-1]
                self.efficiency_series.slices()[0].setValue(total_kills or 0)
                self.efficiency_series.slices()[1].setValue(total_deaths or 0)
                self.efficiency_series.slices()[0].setLabel(f"Kills ({total_kills or 0})")
                self.efficiency_series.slices()[1].setLabel(f"Deaths ({total_deaths or 0})")
                
                # Update stat labels
                for i, key in enumerate(self.stat_labels.keys()):
                    value = stats[i] if stats[i] is not None else "--"
                    
                    if isinstance(value, (int, float)):
                        if key == "win_rate":
                            formatted_value = f"{value:.1f}"
                        elif key in ["kd_ratio", "tickets_ratio"]:  # Added tickets_ratio to 2 decimal format
                            formatted_value = f"{value:.2f}"
                        else:
                            formatted_value = f"{int(value):,}"
                    else:
                        formatted_value = str(value)
                        
                    if key == "win_rate":
                        formatted_value += "%"
                        
                    self.stat_labels[key].setText(formatted_value)

def setup_attacker_tab(dialog):
    dialog.attacker_tab = AttackerTab(dialog, dialog.player_name, dialog.parent.db.db_path)
