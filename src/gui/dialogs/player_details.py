from PyQt5.QtWidgets import (
    QDialog, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QHBoxLayout, QLabel, QComboBox, QGroupBox, QGridLayout, 
    QTabWidget, QScrollArea, QToolTip
)
from PyQt5.QtGui import QPainter, QCursor  # Added QCursor here
from PyQt5.QtCore import Qt, QSettings, QPoint
import sqlite3
from ..widgets.numeric_sort import NumericSortItem
from ...utils.constants import MEDAL_USERS
from PyQt5.QtChart import (QChart, QChartView, QBarSeries, QBarSet, QValueAxis, 
                          QBarCategoryAxis, QLineSeries)
import numpy as np
from ..tabs.class_tab import ClassTab
from ..tabs.map_tab import MapTab
from ..tabs.medal_tab import MedalTab  # Fixed import path
from ..tabs.overall_tab import setup_overall_tab

class PlayerDetailsDialog(QDialog):
    CHUNK_SIZE = 100  # Number of records to load at once

    def __init__(self, parent=None, player_name=None):
        super().__init__(parent)
        self.parent = parent
        self.player_name = player_name
        self.setWindowTitle(f"Player Details - {player_name}")
        self.settings = QSettings('DeltaForce', 'Leaderboard')
        self.restore_window_state()
        self.init_ui()  # This now includes setting up the chart

    def restore_window_state(self):
        geometry = self.settings.value('player_details_geometry')
        if (geometry):
            self.restoreGeometry(geometry)
        else:
            self.setGeometry(200, 200, 900, 500)

    def init_ui(self):
        layout = QVBoxLayout()
        self.tabs = QTabWidget()
        
        # Create and add tabs
        self.overall_tab = QWidget()
        self.class_tab = ClassTab(self, self.player_name, self.parent.db.db_path)
        self.attacker_tab = QWidget()  # Initialize here
        self.defender_tab = QWidget()  # Initialize here
        self.map_tab = MapTab(self, self.player_name, self.parent.db.db_path)
        
        # Add base tabs that everyone can see
        self.tabs.addTab(self.overall_tab, "Overall Statistics")
        self.tabs.addTab(self.class_tab, "Class Statistics") 
        self.tabs.addTab(self.map_tab, "Map Performance")
        
        # Add special tabs only for specific players
        if self.player_name.lower() == "adwdaa":  # Case-insensitive check
            self.tabs.addTab(self.attacker_tab, "Attacker")
            self.tabs.addTab(self.defender_tab, "Defender")
            # Set up the attacker and defender tabs immediately
            self.setup_attacker_tab()
            self.setup_defender_tab()
        
        # Only add medal tab for users in MEDAL_USERS
        if self.player_name in MEDAL_USERS:
            self.medal_tab = MedalTab(self, self.player_name, self.parent.db.db_path)
            self.tabs.addTab(self.medal_tab, "Medals")
        
        # Setup remaining tabs
        setup_overall_tab(self)
        
        layout.addWidget(self.tabs)
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

    def create_map_filter(self, layout, role):
        """Create map filter dropdown"""
        filter_layout = QHBoxLayout()
        
        map_combo = QComboBox()
        map_combo.addItem("All Maps")
        
        # Get unique map names using the same logic as MapTab
        with sqlite3.connect(self.parent.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT SUBSTR(snapshot_name, INSTR(snapshot_name, ' - ') + 3, 
                    INSTR(snapshot_name, ' (') - INSTR(snapshot_name, ' - ') - 3) as map_name
                FROM snapshots
                WHERE name = ? 
                    AND team LIKE ? 
                    AND snapshot_name IS NOT NULL
                    AND snapshot_name != ''
                ORDER BY map_name
            """, (self.player_name, f'%{role}%'))
            
            for row in cursor.fetchall():
                if row[0]:  # Only add non-empty map names
                    map_name = row[0].strip()
                    if map_name:  # Additional check to avoid empty strings
                        map_combo.addItem(map_name)
        
        filter_widget = QWidget()
        filter_layout.addWidget(QLabel("Filter by Map:"))
        filter_layout.addWidget(map_combo)
        filter_layout.addStretch()
        filter_widget.setLayout(filter_layout)
        
        # Add filter at the top of the grid (row 0)
        layout.addWidget(filter_widget, 0, 0, 1, 2)  # span 1 row, 2 columns
        
        return map_combo

    def setup_attacker_tab(self):
        layout = QGridLayout()
        self.attacker_tab.setLayout(layout)
        
        # Create filter widget container that won't be deleted
        self.attacker_filter_container = QWidget()
        filter_layout = QHBoxLayout()
        self.attacker_filter_container.setLayout(filter_layout)
        
        # Create map combo box once
        self.attacker_map_combo = QComboBox()
        self.attacker_map_combo.addItem("All Maps")
        
        # Get unique map names
        with sqlite3.connect(self.parent.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT SUBSTR(snapshot_name, INSTR(snapshot_name, ' - ') + 3, 
                    INSTR(snapshot_name, ' (') - INSTR(snapshot_name, ' - ') - 3) as map_name
                FROM snapshots
                WHERE name = ? 
                    AND team LIKE ? 
                    AND snapshot_name IS NOT NULL
                    AND snapshot_name != ''
                ORDER BY map_name
            """, (self.player_name, '%ATTACK%'))
            
            for row in cursor.fetchall():
                if row[0]:
                    map_name = row[0].strip()
                    if map_name:
                        self.attacker_map_combo.addItem(map_name)
        
        filter_layout.addWidget(QLabel("Filter by Map:"))
        filter_layout.addWidget(self.attacker_map_combo)
        filter_layout.addStretch()
        
        # Add filter container at the top
        layout.addWidget(self.attacker_filter_container, 0, 0, 1, 2)
        
        def update_stats(map_name=None):
            # Clear existing widgets except filter container
            for i in reversed(range(layout.count())):
                item = layout.itemAt(i)
                if item.widget() != self.attacker_filter_container:
                    item.widget().deleteLater()
            
            # Rest of the function remains the same, but remove these lines:
            # map_combo = self.create_map_filter(layout, "ATTACK")
            # map_combo.currentTextChanged.connect(update_stats)
            # if map_name:
            #     map_combo.setCurrentText(map_name)
            
            with sqlite3.connect(self.parent.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Modify query to use the correct map extraction
                query = """
                    SELECT 
                        COUNT(DISTINCT snapshot_name) as total_games,
                        SUM(score) as total_score,
                        ROUND(AVG(score)) as avg_score,
                        MAX(score) as best_score,
                        SUM(kills) as total_kills,
                        ROUND(AVG(kills), 1) as avg_kills,
                        SUM(deaths) as total_deaths,
                        ROUND(AVG(deaths), 1) as avg_deaths,
                        ROUND(CAST(SUM(kills) AS FLOAT) / NULLIF(SUM(deaths), 0), 2) as kd_ratio,
                        SUM(assists) as total_assists,
                        ROUND(AVG(assists), 1) as avg_assists,
                        SUM(revives) as total_revives,
                        ROUND(AVG(revives), 1) as avg_revives,
                        SUM(captures) as total_captures,
                        ROUND(AVG(captures), 1) as avg_captures,
                        ROUND(AVG(rank)) as avg_rank,
                        SUM(CASE WHEN snapshot_name LIKE '%VICTORY%' THEN 1 ELSE 0 END) as victories,
                        COUNT(*) as matches
                    FROM snapshots
                    WHERE name = ? 
                    AND (team = 'ATTACK' OR team = 'Attack' OR team = 'attack')
                """
                
                params = [self.player_name]
                if map_name and map_name != "All Maps":
                    query += """ 
                    AND SUBSTR(snapshot_name, 
                        INSTR(snapshot_name, ' - ') + 3, 
                        INSTR(snapshot_name, ' (') - INSTR(snapshot_name, ' - ') - 3
                    ) = ?
                    """
                    params.append(map_name)
                
                query += " GROUP BY name"
                cursor.execute(query, params)
                
                stats = cursor.fetchone()
                if not stats or stats[0] == 0:
                    layout.addWidget(QLabel("No attacker data available"))
                    return

                victories = stats[16] or 0
                total_matches = stats[17] or 0
                
                stat_groups = {
                    "Overview": [
                        ("Total Games:", stats[0] or 0),
                        ("Victories:", victories),
                        ("Defeats:", total_matches - victories),
                        ("Win Rate:", f"{(victories/total_matches*100):.1f}%" if total_matches > 0 else "0%"),
                        ("Average Rank:", stats[15] or 0),
                    ],
                    "Combat Stats": [
                        ("Total Score:", stats[1] or 0),
                        ("Average Score:", stats[2] or 0),
                        ("Best Score:", stats[3] or 0),
                    ],
                    "Combat Performance": [
                        ("Total Kills:", stats[4] or 0),
                        ("Average Kills:", stats[5] or 0),
                        ("Total Deaths:", stats[6] or 0),
                        ("Average Deaths:", stats[7] or 0),
                        ("K/D Ratio:", stats[8] or "0.00"),
                    ],
                    "Support Stats": [
                        ("Total Assists:", stats[9] or 0),
                        ("Average Assists:", stats[10] or 0),
                        ("Total Revives:", stats[11] or 0),
                        ("Average Revives:", stats[12] or 0),
                    ],
                    "Objective Stats": [
                        ("Total Captures:", stats[13] or 0),
                        ("Average Captures:", stats[14] or 0),
                    ]
                }

                # Update grid positions to start from row 1 (after filter)
                grid_positions = {
                    "Overview": (1, 0),
                    "Combat Stats": (1, 1),
                    "Combat Performance": (2, 0),
                    "Support Stats": (2, 1),
                    "Objective Stats": (3, 0),
                }

                for group_name, group_stats in stat_groups.items():
                    group = QGroupBox(group_name)
                    group_layout = QGridLayout()
                    
                    for row, (label, value) in enumerate(group_stats):
                        group_layout.addWidget(QLabel(label), row, 0)
                        formatted_value = self.format_value(value, label)
                        group_layout.addWidget(QLabel(formatted_value), row, 1)
                    
                    group.setLayout(group_layout)
                    row, col = grid_positions[group_name]
                    layout.addWidget(group, row, col)

        # Connect map filter change to stats update
        self.attacker_map_combo.currentTextChanged.connect(update_stats)
        
        # Initial stats load
        update_stats()

    def setup_defender_tab(self):
        # Same changes as attacker tab but for defender
        layout = QGridLayout()
        self.defender_tab.setLayout(layout)
        
        self.defender_filter_container = QWidget()
        filter_layout = QHBoxLayout()
        self.defender_filter_container.setLayout(filter_layout)
        
        self.defender_map_combo = QComboBox()
        self.defender_map_combo.addItem("All Maps")
        
        with sqlite3.connect(self.parent.db.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT SUBSTR(snapshot_name, INSTR(snapshot_name, ' - ') + 3, 
                    INSTR(snapshot_name, ' (') - INSTR(snapshot_name, ' - ') - 3) as map_name
                FROM snapshots
                WHERE name = ? 
                    AND team LIKE ? 
                    AND snapshot_name IS NOT NULL
                    AND snapshot_name != ''
                ORDER BY map_name
            """, (self.player_name, '%DEFENSE%'))
            
            for row in cursor.fetchall():
                if row[0]:
                    map_name = row[0].strip()
                    if map_name:
                        self.defender_map_combo.addItem(map_name)
        
        filter_layout.addWidget(QLabel("Filter by Map:"))
        filter_layout.addWidget(self.defender_map_combo)
        filter_layout.addStretch()
        
        layout.addWidget(self.defender_filter_container, 0, 0, 1, 2)
        
        def update_stats(map_name=None):
            for i in reversed(range(layout.count())):
                item = layout.itemAt(i)
                if item.widget() != self.defender_filter_container:
                    item.widget().deleteLater()
            
            with sqlite3.connect(self.parent.db.db_path) as conn:
                cursor = conn.cursor()
                
                # Modify query to use the correct map extraction
                query = """
                    SELECT 
                        COUNT(DISTINCT snapshot_name) as total_games,
                        SUM(score) as total_score,
                        ROUND(AVG(score)) as avg_score,
                        MAX(score) as best_score,
                        SUM(kills) as total_kills,
                        ROUND(AVG(kills), 1) as avg_kills,
                        SUM(deaths) as total_deaths,
                        ROUND(AVG(deaths), 1) as avg_deaths,
                        ROUND(CAST(SUM(kills) AS FLOAT) / NULLIF(SUM(deaths), 0), 2) as kd_ratio,
                        SUM(assists) as total_assists,
                        ROUND(AVG(assists), 1) as avg_assists,
                        SUM(revives) as total_revives,
                        ROUND(AVG(revives), 1) as avg_revives,
                        SUM(captures) as total_captures,
                        ROUND(AVG(captures), 1) as avg_captures,
                        ROUND(AVG(rank)) as avg_rank,
                        SUM(CASE WHEN snapshot_name LIKE '%VICTORY%' THEN 1 ELSE 0 END) as victories,
                        COUNT(*) as matches
                    FROM snapshots
                    WHERE name = ? 
                    AND (team = 'DEFENSE' OR team = 'Defense' OR team = 'defense')
                """
                
                params = [self.player_name]
                if map_name and map_name != "All Maps":
                    query += """ 
                    AND SUBSTR(snapshot_name, 
                        INSTR(snapshot_name, ' - ') + 3, 
                        INSTR(snapshot_name, ' (') - INSTR(snapshot_name, ' - ') - 3
                    ) = ?
                    """
                    params.append(map_name)
                
                query += " GROUP BY name"
                cursor.execute(query, params)
                
                stats = cursor.fetchone()
                if not stats or stats[0] == 0:
                    layout.addWidget(QLabel("No defender data available"))
                    return

                victories = stats[16] or 0
                total_matches = stats[17] or 0

                stat_groups = {
                    "Overview": [
                        ("Total Games:", stats[0] or 0),
                        ("Victories:", victories),
                        ("Defeats:", total_matches - victories),
                        ("Win Rate:", f"{(victories/total_matches*100):.1f}%" if total_matches > 0 else "0%"),
                        ("Average Rank:", stats[15] or 0),
                    ],
                    "Combat Stats": [
                        ("Total Score:", stats[1] or 0),
                        ("Average Score:", stats[2] or 0),
                        ("Best Score:", stats[3] or 0),
                    ],
                    "Combat Performance": [
                        ("Total Kills:", stats[4] or 0),
                        ("Average Kills:", stats[5] or 0),
                        ("Total Deaths:", stats[6] or 0),
                        ("Average Deaths:", stats[7] or 0),
                        ("K/D Ratio:", stats[8] or "0.00"),
                    ],
                    "Support Stats": [
                        ("Total Assists:", stats[9] or 0),
                        ("Average Assists:", stats[10] or 0),
                        ("Total Revives:", stats[11] or 0),
                        ("Average Revives:", stats[12] or 0),
                    ],
                    "Objective Stats": [
                        ("Total Captures:", stats[13] or 0),
                        ("Average Captures:", stats[14] or 0),
                    ]
                }

                # Use same grid layout as attacker tab
                grid_positions = {
                    "Overview": (1, 0),
                    "Combat Stats": (1, 1),
                    "Combat Performance": (2, 0),
                    "Support Stats": (2, 1),
                    "Objective Stats": (3, 0),
                }

                for group_name, group_stats in stat_groups.items():
                    group = QGroupBox(group_name)
                    group_layout = QGridLayout()
                    
                    for row, (label, value) in enumerate(group_stats):
                        group_layout.addWidget(QLabel(label), row, 0)
                        formatted_value = self.format_value(value, label)
                        group_layout.addWidget(QLabel(formatted_value), row, 1)
                    
                    group.setLayout(group_layout)
                    row, col = grid_positions[group_name]
                    layout.addWidget(group, row, col)

        self.defender_map_combo.currentTextChanged.connect(update_stats)
        update_stats()

    def setup_stats_chart(self, layout):
        """Add a chart showing player performance trends"""
        try:
            chart = QChart()
            chart.setTitle("Monthly Performance Trends")
            
            with sqlite3.connect(self.parent.db.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    WITH parsed_dates AS (
                        SELECT 
                            substr(timestamp, 4, 3) || ' ' || substr(timestamp, 9, 4) as month_year,
                            AVG(kills) as avg_kills,
                            AVG(deaths) as avg_deaths,
                            AVG(assists) as avg_assists,
                            AVG(revives) as avg_revives,
                            COUNT(*) as games
                        FROM snapshots 
                        WHERE name = ?
                        GROUP BY month_year
                        ORDER BY substr(timestamp, 9, 4),
                            CASE substr(timestamp, 4, 3)
                                WHEN 'Jan' THEN '01'
                                WHEN 'Feb' THEN '02'
                                WHEN 'Mar' THEN '03'
                                WHEN 'Apr' THEN '04'
                                WHEN 'May' THEN '05'
                                WHEN 'Jun' THEN '06'
                                WHEN 'Jul' THEN '07'
                                WHEN 'Aug' THEN '08'
                                WHEN 'Sep' THEN '09'
                                WHEN 'Oct' THEN '10'
                                WHEN 'Nov' THEN '11'
                                WHEN 'Dec' THEN '12'
                            END ASC
                        LIMIT 12
                    )
                    SELECT * FROM parsed_dates
                """, (self.player_name,))

                data = cursor.fetchall()
                if not data:
                    layout.addWidget(QLabel("No performance data available"))
                    return

                combat_series = QBarSeries()
                kills = QBarSet("Avg Kills")
                deaths = QBarSet("Avg Deaths")
                assists = QBarSet("Avg Assists")
                revives = QBarSet("Avg Revives")
                
                categories = []
                max_value = 0
                month_labels = []
                
                # Process data in reverse order to show most recent months on the right
                for row in reversed(data):
                    month_year = row[0]
                    games = row[5]
                    month_labels.insert(0, f"{month_year} ({games} games)")  # Insert at beginning
                    categories.insert(0, f"{month_year} ({games})")  # Insert at beginning
                    
                    # Add values to sets at beginning
                    for i, barset in enumerate([kills, deaths, assists, revives], 1):
                        value = round(float(row[i] or 0))
                        barset.insert(0, value)  # Insert at beginning
                        max_value = max(max_value, value)

                # Rest of the chart setup remains the same
                combat_series.hovered.connect(lambda status, index, barset: 
                    QToolTip.showText(
                        QCursor.pos(),
                        f"{month_labels[index]}\n{barset.label()}: {barset.at(index)}"
                    ) if status else QToolTip.hideText()
                )

                # Add series
                for series in [kills, deaths, assists, revives]:
                    combat_series.append(series)
                combat_series.setLabelsVisible(True)

                # Setup axes
                axis_x = QBarCategoryAxis()
                axis_x.append(categories)
                axis_y = QValueAxis()
                axis_y.setRange(0, max_value * 1.2)
                axis_y.setTitleText("Average per Game")

                chart.addSeries(combat_series)
                chart.setAxisX(axis_x, combat_series)
                chart.setAxisY(axis_y, combat_series)
                chart.legend().setAlignment(Qt.AlignBottom)

                # Create view
                chart_view = QChartView(chart)
                chart_view.setMinimumHeight(220)
                chart_view.setRenderHint(QPainter.Antialiasing)
                chart_view.setMouseTracking(True)
                layout.addWidget(chart_view)

        except Exception as e:
            print(f"Error creating performance chart: {str(e)}")
            print(f"Data: {data if 'data' in locals() else 'No data'}")
            layout.addWidget(QLabel("Failed to load performance chart"))

    def setup_history_tab(self):
        # ...existing code...
        
        def load_chunk(cursor, offset):
            cursor.execute("""
                SELECT timestamp, snapshot_name, rank, class, score, 
                       kills, deaths, assists, revives, captures
                FROM snapshots 
                WHERE name = ? 
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, (self.player_name, self.CHUNK_SIZE, offset))
            return cursor.fetchall()
            
        # Load data in chunks
        offset = 0
        with sqlite3.connect(self.parent.db.db_path) as conn:
            cursor = conn.cursor()
            while True:
                chunk = load_chunk(cursor, offset)
                if not chunk:
                    break
                # Process chunk...
                offset += self.CHUNK_SIZE

    def closeEvent(self, event):
        self.settings.setValue('player_details_geometry', self.saveGeometry())
        super().closeEvent(event)
