from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
                           QPushButton, QLabel, QHeaderView, QHBoxLayout, QWidget,
                           QStackedWidget)
from PyQt5.QtCore import Qt
import sqlite3

class NumericTableItem(QTableWidgetItem):
    def __lt__(self, other):
        try:
            return float(self.data(Qt.UserRole)) < float(other.data(Qt.UserRole))
        except (ValueError, TypeError):
            return super().__lt__(other)

class MatchDetailsDialog(QDialog):
    def __init__(self, parent, snapshot_name):
        super().__init__(parent)
        self.parent = parent
        self.snapshot_name = snapshot_name
        
        # Get match info for title
        with sqlite3.connect(self.parent.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT data, map FROM matches WHERE snapshot_name = ? LIMIT 1", 
                           (self.snapshot_name,))
            result = cursor.fetchone()
            match_date, match_map = result if result else ("Unknown", "Unknown")
            
        self.setWindowTitle(f"Match Details: {match_date} on {match_map}")
        self.setMinimumSize(1200, 800)  # Increased minimum size
        self.setModal(True)
        self.view_mode = "unified"  # Default view mode
        self.init_ui()
        self.load_match_data()

    def init_ui(self):
        layout = QVBoxLayout()

        # Match info header
        header = QLabel(f"Match Details")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # Add view toggle button
        self.toggle_button = QPushButton("Switch to Split View")
        self.toggle_button.clicked.connect(self.toggle_view)
        layout.addWidget(self.toggle_button)

        # Create stacked widget to hold both views
        self.stack = QStackedWidget()

        # Create unified view
        unified_widget = QWidget()
        unified_layout = QVBoxLayout(unified_widget)
        self.unified_table = self._create_team_table("All Players")
        unified_layout.addWidget(self.unified_table)

        # Create split view
        split_widget = QWidget()
        split_layout = QHBoxLayout(split_widget)
        
        # Create layouts for each side
        left_layout = QVBoxLayout()
        right_layout = QVBoxLayout()
        
        self.left_table = self._create_team_table("Team 1")
        self.right_table = self._create_team_table("Team 2")
        
        left_team_header = QLabel("Team 1")
        right_team_header = QLabel("Team 2")
        left_team_header.setAlignment(Qt.AlignCenter)
        right_team_header.setAlignment(Qt.AlignCenter)
        
        left_layout.addWidget(left_team_header)
        left_layout.addWidget(self.left_table)
        right_layout.addWidget(right_team_header)
        right_layout.addWidget(self.right_table)
        
        split_layout.addLayout(left_layout)
        split_layout.addLayout(right_layout)

        # Add both views to stack
        self.stack.addWidget(unified_widget)
        self.stack.addWidget(split_widget)
        layout.addWidget(self.stack)

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.setLayout(layout)

    def toggle_view(self):
        if self.view_mode == "unified":
            self.view_mode = "split"
            self.stack.setCurrentIndex(1)
            self.toggle_button.setText("Switch to Unified View")
            self.load_match_data()  # Reload data for split view
        else:
            self.view_mode = "unified"
            self.stack.setCurrentIndex(0)
            self.toggle_button.setText("Switch to Split View")
            self.load_match_data()  # Reload data for unified view

    def _create_team_table(self, team_name):
        table = QTableWidget()
        table.setColumnCount(11)
        table.setHorizontalHeaderLabels([
            "Player", "Class", "Rank", "Score", "Kills", "Deaths", 
            "Assists", "Revives", "Captures", "Vehicle Damage", "Tactical Respawns"
        ])
        
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        table.setSortingEnabled(False)
        
        header = table.horizontalHeader()
        
        # Set specific column widths
        # Player name gets more space
        header.setSectionResizeMode(0, QHeaderView.Interactive)
        table.setColumnWidth(0, 200)  # Player name column
        
        # Class and Rank get less space
        header.setSectionResizeMode(1, QHeaderView.Interactive)
        header.setSectionResizeMode(2, QHeaderView.Interactive)
        table.setColumnWidth(1, 80)   # Class column
        table.setColumnWidth(2, 60)   # Rank column
        
        # Rest of columns stretch
        for i in range(3, table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        
        return table

    def _add_placeholder_row(self, table, row_idx, rank):
        """Add a placeholder row for missing rank position"""
        table.insertRow(row_idx)
        placeholder = QTableWidgetItem("---")
        placeholder.setFlags(Qt.ItemIsEnabled)  # Make it non-selectable
        placeholder.setTextAlignment(Qt.AlignCenter)
        table.setItem(row_idx, 0, placeholder)  # Name column
        
        # Add placeholder for class
        class_placeholder = QTableWidgetItem("---")
        class_placeholder.setFlags(Qt.ItemIsEnabled)
        class_placeholder.setTextAlignment(Qt.AlignCenter)
        table.setItem(row_idx, 1, class_placeholder)
        
        # Add rank number
        rank_item = NumericTableItem(str(rank))
        rank_item.setFlags(Qt.ItemIsEnabled)
        rank_item.setTextAlignment(Qt.AlignCenter)
        table.setItem(row_idx, 2, rank_item)
        
        # Fill remaining columns with dashes
        for col in range(3, table.columnCount()):
            item = QTableWidgetItem("---")
            item.setFlags(Qt.ItemIsEnabled)
            item.setTextAlignment(Qt.AlignCenter)
            table.setItem(row_idx, col, item)

    def load_match_data(self):
        with sqlite3.connect(self.parent.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name, class, rank, score, kills, deaths,
                       assists, revives, captures, vehicle_damage, tactical_respawn
                FROM matches
                WHERE snapshot_name = ?
                ORDER BY CAST(rank AS INTEGER), score DESC
            """, (self.snapshot_name,))
            
            all_players = cursor.fetchall()
            
            if self.view_mode == "unified":
                # Clear and load unified table
                self.unified_table.setRowCount(0)
                self.unified_table.setSortingEnabled(False)  # Disable sorting while loading
                
                for row_idx, player in enumerate(all_players):
                    self._add_player_to_table(self.unified_table, row_idx, player)
                
                self.unified_table.setSortingEnabled(True)
                # Initial sort by rank column (index 2)
                self.unified_table.sortItems(2, Qt.AscendingOrder)
                
            else:
                # Clear split tables
                self.left_table.setRowCount(0)
                self.right_table.setRowCount(0)
                
                # Group players by rank
                rank_groups = {}
                max_rank = 1
                for player in all_players:
                    rank = player[2]
                    max_rank = max(max_rank, int(rank))
                    if rank not in rank_groups:
                        rank_groups[rank] = []
                    rank_groups[rank].append(player)

                left_row = right_row = 0
                
                # Process each rank in order
                for rank in range(1, max_rank + 1):
                    str_rank = str(rank)
                    players = sorted(rank_groups.get(str_rank, []), 
                                  key=lambda x: x[3], reverse=True)  # Sort by score
                    
                    # Handle cases where rank has 0, 1, or 2+ players
                    if not players:
                        # Add placeholder to both teams for missing rank
                        self._add_placeholder_row(self.left_table, left_row, rank)
                        self._add_placeholder_row(self.right_table, right_row, rank)
                        left_row += 1
                        right_row += 1
                    elif len(players) == 1:
                        # Single player goes to left team, placeholder for right
                        self._add_player_to_table(self.left_table, left_row, players[0])
                        self._add_placeholder_row(self.right_table, right_row, rank)
                        left_row += 1
                        right_row += 1
                    else:
                        # Distribute players between teams
                        for i, player in enumerate(players):
                            if i % 2 == 0:
                                self._add_player_to_table(self.left_table, left_row, player)
                                left_row += 1
                            else:
                                self._add_player_to_table(self.right_table, right_row, player)
                                right_row += 1
                
                self.left_table.setSortingEnabled(True)
                self.right_table.setSortingEnabled(True)
                # Sort both tables by rank
                self.left_table.sortItems(2, Qt.AscendingOrder)
                self.right_table.sortItems(2, Qt.AscendingOrder)

    def _add_player_to_table(self, table, row_idx, player_data):
        table.insertRow(row_idx)
        for col_idx, value in enumerate(player_data):
            if col_idx in [2, 3, 4, 5, 6, 7, 8, 9, 10]:
                try:
                    numeric_value = float(str(value).replace(',', '')) if value else 0
                    item = NumericTableItem(f"{int(numeric_value):,}")
                    item.setData(Qt.UserRole, numeric_value)
                except ValueError:
                    item = NumericTableItem(str(value))
                    item.setData(Qt.UserRole, 0)
                item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
            else:
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            table.setItem(row_idx, col_idx, item)

def on_row_double_clicked(self, row):
    match_data = {
        'id': self.table.item(row, 0).data(Qt.UserRole)  # Store match ID in UserRole
    }
    dialog = MatchDetailsDialog(self, match_data)
    dialog.exec_()