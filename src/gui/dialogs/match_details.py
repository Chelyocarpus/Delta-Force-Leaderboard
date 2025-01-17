from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QTableWidget, QTableWidgetItem,
                           QPushButton, QLabel, QHeaderView)
from PyQt5.QtCore import Qt

class NumericTableItem(QTableWidgetItem):
    def __lt__(self, other):
        try:
            return float(self.data(Qt.UserRole)) < float(other.data(Qt.UserRole))
        except (ValueError, TypeError):
            return super().__lt__(other)

class MatchDetailsDialog(QDialog):
    def __init__(self, parent, match_id):
        super().__init__(parent)
        self.parent = parent
        self.match_id = match_id
        
        self.setWindowTitle(f"Match Details")
        self.setMinimumSize(900, 600)
        self.setModal(True)
        self.init_ui()
        self.load_match_data()

    def init_ui(self):
        layout = QVBoxLayout()

        # Match info header
        header = QLabel(f"Match Details")
        header.setAlignment(Qt.AlignCenter)
        layout.addWidget(header)

        # Create table for player details
        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "Player", "Class", "Rank", "Score", "Kills", "Deaths", "K/D",
            "Assists", "Revives", "Captures", "Medals"
        ])
        
        # Set table properties
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSortingEnabled(False)  # Disable sorting temporarily
        
        # Set column stretch
        header = self.table.horizontalHeader()
        for i in range(self.table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        
        layout.addWidget(self.table)

        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)

        self.setLayout(layout)

    def load_match_data(self):
        print(f"Debug - Loading match data for: {self.match_id}")
        # Split match_id into components (order: outcome - map - date - team)
        parts = self.match_id.split(' - ')
        
        if len(parts) >= 4:
            outcome = parts[0]
            map_name = parts[1]
            match_date = parts[2]
            team = parts[3]
            
            print(f"Debug - parsed values:")
            print(f"Outcome: {outcome}")
            print(f"Map: {map_name}")
            print(f"Date: {match_date}")
            print(f"Team: {team}")
            
            # Construct snapshot_name in same format as database
            snapshot_name = self.match_id
            
            with self.parent.parent.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT player_name, class, rank, score, kills, deaths,
                           CAST(ROUND(CAST(kills AS FLOAT) / 
                                CASE WHEN deaths = 0 THEN 1 ELSE deaths END, 2) AS TEXT) as kd_ratio,
                           assists, revives, captures,
                           CASE 
                               WHEN combat_medal IS NOT NULL OR capture_medal IS NOT NULL OR 
                                    logistics_medal IS NOT NULL OR intelligence_medal IS NOT NULL
                               THEN COALESCE(combat_medal, '') || ' ' || 
                                    COALESCE(capture_medal, '') || ' ' ||
                                    COALESCE(logistics_medal, '') || ' ' ||
                                    COALESCE(intelligence_medal, '')
                               ELSE ''
                           END as medals
                    FROM matches
                    WHERE snapshot_name = ?
                    ORDER BY score DESC, kills DESC, deaths ASC
                """, (snapshot_name,))
            
                for row_idx, row_data in enumerate(cursor.fetchall()):
                    self.table.insertRow(row_idx)
                    
                    for col_idx, value in enumerate(row_data):
                        if col_idx in [2, 3, 4, 5, 7, 8, 9]:  # Numeric columns (except K/D)
                            try:
                                numeric_value = float(str(value).replace(',', '')) if value else 0
                                item = NumericTableItem(f"{int(numeric_value):,}")  # Format as integer
                                item.setData(Qt.UserRole, numeric_value)
                            except ValueError:
                                item = NumericTableItem(str(value))
                                item.setData(Qt.UserRole, 0)
                            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        elif col_idx == 6:  # K/D ratio column
                            try:
                                numeric_value = float(str(value)) if value else 0
                                item = NumericTableItem(f"{numeric_value:.2f}")  # Keep 2 decimal places
                                item.setData(Qt.UserRole, numeric_value)
                            except ValueError:
                                item = NumericTableItem(str(value))
                                item.setData(Qt.UserRole, 0)
                            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        else:
                            item = QTableWidgetItem(str(value))
                            item.setTextAlignment(Qt.AlignLeft | Qt.AlignVCenter)
                        self.table.setItem(row_idx, col_idx, item)
            
            # Enable sorting after data is loaded
            self.table.setSortingEnabled(True)
            # Set initial sort order by Score column (index 3) descending
            self.table.sortItems(3, Qt.DescendingOrder)

def on_row_double_clicked(self, row):
    match_data = {
        'id': self.table.item(row, 0).data(Qt.UserRole)  # Store match ID in UserRole
    }
    dialog = MatchDetailsDialog(self, match_data)
    dialog.exec_()