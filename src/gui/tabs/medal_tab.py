from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QGroupBox, QGridLayout, QLabel
)
from PyQt5.QtCore import Qt
import sqlite3
from ..widgets.numeric_sort import NumericSortItem
from ...utils.constants import MEDAL_TABLE_COLUMNS

class MedalTab(QWidget):
    def __init__(self, parent, player_name, db_path):
        super().__init__(parent)
        self.parent = parent
        self.player_name = player_name
        self.db_path = db_path
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Query to get direct medal counts from snapshots table
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT snapshot_name) as total_games,
                    SUM(CASE WHEN combat_medal IS NOT NULL THEN 1 ELSE 0 END) as combat_count,
                    SUM(CASE WHEN capture_medal IS NOT NULL THEN 1 ELSE 0 END) as capture_count,
                    SUM(CASE WHEN logistics_medal IS NOT NULL THEN 1 ELSE 0 END) as logistics_count,
                    SUM(CASE WHEN intelligence_medal IS NOT NULL THEN 1 ELSE 0 END) as intel_count,
                    COUNT(DISTINCT CASE WHEN combat_medal IS NOT NULL 
                        OR capture_medal IS NOT NULL 
                        OR logistics_medal IS NOT NULL 
                        OR intelligence_medal IS NOT NULL 
                        THEN snapshot_name END) as games_with_medals
                FROM snapshots
                WHERE name = ?
            """, (self.player_name,))
            
            stats = cursor.fetchone()
            total_games = stats[0] or 0
            games_with_medals = stats[5] or 0
            medal_rate = (games_with_medals/total_games*100 if total_games > 0 else 0)
            
            # Create medal overview section
            summary_group = QGroupBox("Medal Overview")
            summary_layout = QGridLayout()
            
            # Get detailed medal counts by type and rank
            cursor.execute("""
                SELECT 
                    SUM(CASE WHEN combat_medal = 'Gold' THEN 1 ELSE 0 END) as combat_gold,
                    SUM(CASE WHEN combat_medal = 'Silver' THEN 1 ELSE 0 END) as combat_silver,
                    SUM(CASE WHEN combat_medal = 'Bronze' THEN 1 ELSE 0 END) as combat_bronze,
                    SUM(CASE WHEN capture_medal = 'Gold' THEN 1 ELSE 0 END) as capture_gold,
                    SUM(CASE WHEN capture_medal = 'Silver' THEN 1 ELSE 0 END) as capture_silver,
                    SUM(CASE WHEN capture_medal = 'Bronze' THEN 1 ELSE 0 END) as capture_bronze,
                    SUM(CASE WHEN logistics_medal = 'Gold' THEN 1 ELSE 0 END) as logistics_gold,
                    SUM(CASE WHEN logistics_medal = 'Silver' THEN 1 ELSE 0 END) as logistics_silver,
                    SUM(CASE WHEN logistics_medal = 'Bronze' THEN 1 ELSE 0 END) as logistics_bronze,
                    SUM(CASE WHEN intelligence_medal = 'Gold' THEN 1 ELSE 0 END) as intel_gold,
                    SUM(CASE WHEN intelligence_medal = 'Silver' THEN 1 ELSE 0 END) as intel_silver,
                    SUM(CASE WHEN intelligence_medal = 'Bronze' THEN 1 ELSE 0 END) as intel_bronze
                FROM snapshots
                WHERE name = ?
            """, (self.player_name,))
            medal_counts = cursor.fetchone()

            # Organize stats in a more logical way
            summary_stats = [
                ("Performance Stats", [
                    ("Total Games:", total_games),
                    ("Games with Medals:", games_with_medals),
                    ("Medal Rate:", f"{medal_rate:.1f}%"),
                    ("Medal Frequency:", f"1 every {total_games/games_with_medals:.1f} games" 
                                      if games_with_medals > 0 else "N/A"),
                ]),
                ("Medal Totals", [
                    ("Gold Medals:", sum(medal_counts[i] or 0 for i in (0,3,6,9))),
                    ("Silver Medals:", sum(medal_counts[i] or 0 for i in (1,4,7,10))),
                    ("Bronze Medals:", sum(medal_counts[i] or 0 for i in (2,5,8,11))),
                    ("Total Medals:", sum(x or 0 for x in medal_counts)),
                ]),
                ("Category Distribution", [
                    ("Combat:", f"{stats[1]} ({stats[1]/total_games*100:.1f}% of games)" if total_games else "0"),
                    ("Capture:", f"{stats[2]} ({stats[2]/total_games*100:.1f}% of games)" if total_games else "0"),
                    ("Logistics:", f"{stats[3]} ({stats[3]/total_games*100:.1f}% of games)" if total_games else "0"),
                    ("Intelligence:", f"{stats[4]} ({stats[4]/total_games*100:.1f}% of games)" if total_games else "0"),
                ])
            ]
            
            # Create subgroups for better organization
            row = 0
            for group_name, group_stats in summary_stats:
                sub_group = QGroupBox(group_name)
                sub_layout = QGridLayout()
                
                for i, (label, value) in enumerate(group_stats):
                    sub_layout.addWidget(QLabel(label), i, 0)
                    sub_layout.addWidget(QLabel(str(value)), i, 1)
                    
                sub_group.setLayout(sub_layout)
                summary_layout.addWidget(sub_group, row // 3, row % 3)
                row += 1
            
            summary_group.setLayout(summary_layout)
            layout.addWidget(summary_group)

            # Create medal category grid with percentages
            medals_grid = QWidget()
            grid_layout = QGridLayout()

            categories = ['Combat', 'Capture', 'Logistics', 'Intelligence']
            ranks = ['Gold', 'Silver', 'Bronze']
            
            for i, category in enumerate(categories):
                row = i // 2
                col = i % 2
                
                category_group = QGroupBox(f"{category} Medals")
                category_layout = QVBoxLayout()
                
                table = QTableWidget()
                table.setColumnCount(3)
                table.setHorizontalHeaderLabels(["Rank", "Count", "Rate"])
                table.setRowCount(3)
                
                base_idx = i * 3
                for row_idx, rank in enumerate(ranks):
                    count = medal_counts[base_idx + row_idx] or 0
                    rate = (count / total_games * 100) if total_games > 0 else 0
                    
                    table.setItem(row_idx, 0, QTableWidgetItem(rank))
                    table.setItem(row_idx, 1, NumericSortItem(count))
                    
                    percent_item = QTableWidgetItem(f"{rate:.1f}%")
                    percent_item.setData(Qt.UserRole, rate)
                    percent_item.setTextAlignment(Qt.AlignCenter)
                    table.setItem(row_idx, 2, percent_item)
                
                table.setSortingEnabled(True)
                table.resizeColumnsToContents()
                category_layout.addWidget(table)
                category_group.setLayout(category_layout)
                grid_layout.addWidget(category_group, row, col)
            
            medals_grid.setLayout(grid_layout)
            layout.addWidget(medals_grid)
            
        self.setLayout(layout)

    def create_medal_grid(self, stats, medal_processor):
        medals_grid = QWidget()
        grid_layout = QGridLayout()
        
        for i, category in enumerate(medal_processor.categories):
            row = i // 2
            col = i % 2
            
            category_group = QGroupBox(f"{category} Medals")
            category_layout = QVBoxLayout()
            
            table = QTableWidget()
            table.setColumnCount(3)
            table.setHorizontalHeaderLabels(["Rank", "Count", "Rate"])
            table.setRowCount(3)
            
            category_data = stats['detailed_stats'][category]
            for row_idx, rank in enumerate(medal_processor.ranks):
                table.setItem(row_idx, 0, QTableWidgetItem(rank))
                
                if rank in category_data:
                    count, _ = category_data[rank]
                    count_item = NumericSortItem(count)
                    table.setItem(row_idx, 1, count_item)
                    
                    percentage = (count / stats['total_games'] * 100) if stats['total_games'] > 0 else 0
                    percent_item = QTableWidgetItem(f"{percentage:.1f}%")
                    percent_item.setData(Qt.UserRole, percentage)
                    percent_item.setTextAlignment(Qt.AlignCenter)
                    table.setItem(row_idx, 2, percent_item)
                else:
                    table.setItem(row_idx, 1, NumericSortItem(0))
                    percent_item = QTableWidgetItem("0.0%")
                    percent_item.setData(Qt.UserRole, 0.0)
                    percent_item.setTextAlignment(Qt.AlignCenter)
                    table.setItem(row_idx, 2, percent_item)
            
            table.setSortingEnabled(True)
            table.resizeColumnsToContents()
            category_layout.addWidget(table)
            category_group.setLayout(category_layout)
            grid_layout.addWidget(category_group, row, col)
        
        medals_grid.setLayout(grid_layout)
        return medals_grid
