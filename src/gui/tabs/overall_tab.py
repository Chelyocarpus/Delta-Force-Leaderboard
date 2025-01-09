from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QGroupBox, QGridLayout, 
                           QLabel, QTableWidget, QTableWidgetItem)
from PyQt5.QtCore import Qt
from ..widgets.numeric_sort import NumericSortItem
from ...utils.constants import (HISTORY_TABLE_COLUMNS, QUERY_PLAYER_STATS,
                              QUERY_FAVORITE_CLASS, QUERY_VICTORY_STATS,
                              PLAYER_CLASSES)
import sqlite3

def setup_overall_tab(dialog):
    layout = QVBoxLayout()
    
    # Add the chart first
    dialog.setup_stats_chart(layout)
    
    summary_group = QGroupBox("Overall Statistics")
    summary_layout = QGridLayout()
    
    db = dialog.parent.db
    with sqlite3.connect(db.db_path) as conn:
        cursor = conn.cursor()
        # Add favorite class query
        cursor.execute(QUERY_FAVORITE_CLASS, (dialog.player_name,))
        favorite_class = cursor.fetchone()
        
        # Get class distribution
        cursor.execute("""
            SELECT 
                class,
                COUNT(*) as count,
                ROUND(CAST(COUNT(*) AS FLOAT) * 100 / 
                    (SELECT COUNT(*) FROM snapshots WHERE name = ?), 1) as percentage
            FROM snapshots
            WHERE name = ?
            GROUP BY class
        """, (dialog.player_name, dialog.player_name))
        raw_class_stats = {cls: (count, pct) for cls, count, pct in cursor.fetchall()}
        
        # Create full class stats including zeros for missing classes
        class_stats = []
        for class_name in PLAYER_CLASSES:
            if class_name in raw_class_stats:
                count, pct = raw_class_stats[class_name]
                class_stats.append((class_name, count, pct))
            else:
                class_stats.append((class_name, 0, 0.0))
        
        # Add victory/defeat count query
        cursor.execute(QUERY_VICTORY_STATS, (dialog.player_name,))
        victory_stats = cursor.fetchone()
        
        # Get overall stats
        cursor.execute(QUERY_PLAYER_STATS, (dialog.player_name,))
        stats = cursor.fetchone()
        
        # Create stat groups dictionary with proper null handling
        stat_groups = {
            "Player Info": [
                ("Favorite Class:", favorite_class[0] if favorite_class else "N/A"),
                ("Total Games:", stats[0] if stats else 0),
                *[(f"{class_name} Games:", f"{count} ({pct}%)")
                  for class_name, count, pct in class_stats],
            ],
            "Match Results": [
                ("Victories:", victory_stats[0] if victory_stats else 0),
                ("Defeats:", victory_stats[1] if victory_stats else 0),
                ("Win Rate:", f"{(victory_stats[0]/(victory_stats[0] + victory_stats[1])*100):.1f}%" if victory_stats and (victory_stats[0] + victory_stats[1]) > 0 else "0%"),
                ("Average Rank:", stats[15] if stats else 0),
            ],
            "Combat Stats": [
                ("Total Score:", stats[1] if stats else 0),
                ("Average Score:", stats[2] if stats else 0),
                ("Best Score:", stats[3] if stats else 0),
            ],
            "Combat Performance": [
                ("Total Kills:", stats[4] if stats else 0),
                ("Average Kills:", stats[5] if stats else 0),
                ("Total Deaths:", stats[6] if stats else 0),
                ("Average Deaths:", stats[7] if stats else 0),
                ("K/D Ratio:", stats[8] if stats else "0.00"),
            ],
            "Support Stats": [
                ("Total Assists:", stats[9] if stats else 0),
                ("Average Assists:", stats[10] if stats else 0),
                ("Total Revives:", stats[11] if stats else 0),
                ("Average Revives:", stats[12] if stats else 0),
            ],
            "Objective Stats": [
                ("Total Captures:", stats[13] if stats else 0),
                ("Average Captures:", stats[14] if stats else 0),
            ]
        }

        # Create stat boxes
        row = 0
        for group_name, group_stats in stat_groups.items():
            group_box = QGroupBox(group_name)
            group_layout = QGridLayout()
            
            for i, (label, value) in enumerate(group_stats):
                group_layout.addWidget(QLabel(label), i, 0)
                formatted_value = dialog.format_value(value, label)
                group_layout.addWidget(QLabel(formatted_value), i, 1)
            
            group_box.setLayout(group_layout)
            summary_layout.addWidget(group_box, row // 2, row % 2)
            row += 1

    summary_group.setLayout(summary_layout)
    layout.addWidget(summary_group)

    # Add history table
    history_group = QGroupBox("Match History")
    history_layout = QVBoxLayout()
    
    dialog.history_table = QTableWidget()
    dialog.history_table.setColumnCount(10)
    dialog.history_table.setHorizontalHeaderLabels(HISTORY_TABLE_COLUMNS)
    dialog.history_table.setSortingEnabled(True)
    
    cursor.execute("""
        SELECT 
            timestamp,
            snapshot_name,
            rank,
            class,
            score,
            kills,
            deaths,
            assists,
            revives,
            captures
        FROM snapshots
        WHERE name = ?
        ORDER BY timestamp DESC
    """, (dialog.player_name,))
    
    history = cursor.fetchall()
    dialog.history_table.setRowCount(len(history))
    
    for row, data in enumerate(history):
        for col, value in enumerate(data):
            if col in [0, 1, 3]:  # Date, Snapshot, and Class columns
                item = QTableWidgetItem(str(value))
            else:
                item = NumericSortItem(value)
            item.setTextAlignment(Qt.AlignCenter)
            dialog.history_table.setItem(row, col, item)
    
    dialog.history_table.resizeColumnsToContents()
    history_layout.addWidget(dialog.history_table)
    history_group.setLayout(history_layout)
    layout.addWidget(history_group)
    
    dialog.history_table.horizontalHeader().setSortIndicator(0, Qt.DescendingOrder)
    # Add tooltips to column headers
    for col, tooltip in enumerate([
        "Match Date", "Match Details", "Player Rank", "Class Used",
        "Total Score", "Total Kills", "Total Deaths", 
        "Total Assists", "Total Revives", "Total Captures"
    ]):
        dialog.history_table.horizontalHeaderItem(col).setToolTip(tooltip)
    
    dialog.overall_tab.setLayout(layout)
