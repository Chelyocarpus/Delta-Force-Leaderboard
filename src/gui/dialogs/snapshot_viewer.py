from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                           QTableWidgetItem, QPushButton, QLineEdit, QLabel,
                           QHeaderView, QMessageBox, QComboBox, QApplication)
from PyQt5.QtCore import Qt
from .match_details import MatchDetailsDialog
from .purge_confirm import PurgeConfirmDialog

class SnapshotViewerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Match History")
        self.setModal(True)
        self.setMinimumSize(800, 600)
        self.init_ui()
        self.refresh_snapshots()
        
        # Add double-click handler
        self.table.cellDoubleClicked.connect(self.on_row_double_clicked)

    def init_ui(self):
        layout = QVBoxLayout()

        # Search bar setup
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search matches...")
        self.search_input.textChanged.connect(self.refresh_snapshots)
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Create enhanced table
        self.table = QTableWidget()
        self.table.setColumnCount(8)  # Reduced column count
        self.table.setHorizontalHeaderLabels([
            "Date", "Map", "Outcome", "Team", "Players",
            "Total Score", "Top Player", "Top Score"
        ])
        
        # Set table properties
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        
        # Set column properties with stretch mode
        header = self.table.horizontalHeader()
        for i in range(self.table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        
        layout.addWidget(self.table)

        # Add filter options
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("Filters:"))
        
        # Date filter
        self.date_filter = QComboBox()
        self.date_filter.addItem("All Dates")
        filter_layout.addWidget(QLabel("Date:"))
        filter_layout.addWidget(self.date_filter)
        
        # Map filter
        self.map_filter = QComboBox()
        self.map_filter.addItem("All Maps")
        filter_layout.addWidget(QLabel("Map:"))
        filter_layout.addWidget(self.map_filter)
        
        # Outcome filter
        self.outcome_filter = QComboBox()
        self.outcome_filter.addItems(["All Outcomes", "Victory", "Defeat"])
        filter_layout.addWidget(QLabel("Outcome:"))
        filter_layout.addWidget(self.outcome_filter)
        
        # Connect filter signals
        self.date_filter.currentTextChanged.connect(self.refresh_snapshots)
        self.map_filter.currentTextChanged.connect(self.refresh_snapshots)
        self.outcome_filter.currentTextChanged.connect(self.refresh_snapshots)
        
        layout.addLayout(filter_layout)

        # Buttons
        button_layout = QHBoxLayout()
        
        # Add purge button with red styling
        purge_button = QPushButton("Purge Database")
        purge_button.setStyleSheet("background-color: #ff4444; color: white; font-weight: bold;")
        purge_button.clicked.connect(self.purge_database)
        button_layout.addWidget(purge_button)
        
        view_button = QPushButton("View Details")
        view_button.clicked.connect(self.view_selected_snapshot)
        button_layout.addWidget(view_button)
        
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(self.delete_selected_snapshot)
        button_layout.addWidget(delete_button)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
        self.load_filters()

    def load_filters(self):
        """Load filter options from database"""
        with self.parent.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # Check if table has data first
            cursor.execute("SELECT COUNT(*) FROM matches")
            if cursor.fetchone()[0] == 0:
                return  # Don't load filters if there's no data
            
            # Try to detect the correct column name
            cursor.execute("PRAGMA table_info(matches)")
            columns = [col[1] for col in cursor.fetchall()]
            
            date_column = 'data'
            
            # Use the correct column name
            cursor.execute(f"SELECT DISTINCT {date_column} FROM matches ORDER BY {date_column} DESC")
            dates = cursor.fetchall()
            if dates:  # Only add items if there are dates
                self.date_filter.addItems([row[0] for row in dates])
            
            # Load maps
            cursor.execute("SELECT DISTINCT map FROM matches ORDER BY map")
            maps = cursor.fetchall()
            if maps:  # Only add items if there are maps
                self.map_filter.addItems([row[0] for row in maps])

    def refresh_snapshots(self):
        self.table.setRowCount(0)  # Clear table first
        
        # Check if table has data
        with self.parent.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM matches")
            if cursor.fetchone()[0] == 0:
                return  # Don't try to load data if table is empty
        
        search_text = self.search_input.text().lower()
        map_filter = self.map_filter.currentText()
        outcome_filter = self.outcome_filter.currentText()
        date_filter = self.date_filter.currentText()
        
        with self.parent.db.get_connection() as conn:
            cursor = conn.cursor()
            
            # First detect the date column
            cursor.execute("PRAGMA table_info(matches)")
            columns = [col[1] for col in cursor.fetchall()]
            date_column = 'data'
            
            query = f"""
                SELECT 
                    {date_column},
                    map,
                    outcome,
                    team,
                    COUNT(DISTINCT name) as player_count,
                    SUM(CAST(score as INTEGER)) as total_score,
                    (SELECT name FROM matches m2 
                     WHERE m2.{date_column} = m1.{date_column} 
                     AND m2.map = m1.map 
                     AND m2.team = m1.team 
                     ORDER BY CAST(score as INTEGER) DESC LIMIT 1) as top_player,
                    MAX(CAST(score as INTEGER)) as top_score,
                    outcome || ' - ' || map || ' - ' || {date_column} || ' - ' || team as snapshot_name
                FROM matches m1
                WHERE (LOWER(map) LIKE ? OR LOWER(outcome) LIKE ?)
                    AND (? = 'All Maps' OR map = ?)
                    AND (? = 'All Outcomes' OR 
                         (? = 'Victory' AND outcome LIKE '%VICTORY%') OR 
                         (? = 'Defeat' AND outcome LIKE '%DEFEAT%'))
                    AND (? = 'All Dates' OR {date_column} = ?)
                GROUP BY {date_column}, map, outcome, team
                ORDER BY {date_column} DESC, map ASC
            """
            
            cursor.execute(query, (
                f'%{search_text}%', f'%{search_text}%',
                map_filter, map_filter,
                outcome_filter, outcome_filter, outcome_filter,
                date_filter, date_filter
            ))
            
            for row_idx, row_data in enumerate(cursor.fetchall()):
                self.table.insertRow(row_idx)
                date, map_name, outcome, team, player_count, total_score, top_player, top_score, match_id = row_data
                
                # Format scores safely
                try:
                    formatted_total = f"{int(total_score):,}" if total_score else "0"
                    formatted_top = f"{int(top_score):,}" if top_score else "0"
                except (ValueError, TypeError):
                    formatted_total = str(total_score)
                    formatted_top = str(top_score)
                
                items = [
                    (date, Qt.AlignCenter),
                    (map_name, Qt.AlignLeft),
                    (outcome, Qt.AlignCenter),
                    (team, Qt.AlignCenter),
                    (str(player_count), Qt.AlignCenter),
                    (formatted_total, Qt.AlignRight),
                    (top_player or "Unknown", Qt.AlignLeft),
                    (formatted_top, Qt.AlignRight)
                ]
                
                for col, (value, alignment) in enumerate(items):
                    item = QTableWidgetItem(str(value))
                    item.setTextAlignment(alignment)
                    if col == 0:  # Store match_id in first column
                        item.setData(Qt.UserRole, match_id)
                    self.table.setItem(row_idx, col, item)

    def view_selected_snapshot(self):
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return
            
        snapshot_name = self.table.item(selected_rows[0].row(), 0).data(Qt.UserRole)
        # Add your snapshot detail viewing logic here
        QMessageBox.information(self, "Match Details", f"Viewing match: {snapshot_name}")

    def delete_selected_snapshot(self):
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            return
            
        match_id = self.table.item(selected_rows[0].row(), 0).data(Qt.UserRole)
        
        reply = QMessageBox.question(self, 'Delete Match',
            f'Are you sure you want to delete this match?\n{match_id}',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
        if reply == QMessageBox.Yes:
            try:
                with self.parent.db.get_connection() as conn:
                    cursor = conn.cursor()
                    # Use the match_id directly as snapshot_name
                    cursor.execute("DELETE FROM matches WHERE snapshot_name = ?", (match_id,))
                    conn.commit()
                    
                self.refresh_snapshots()  # Refresh the view
                self.parent.on_snapshot_deleted(match_id)  # Notify parent
                QMessageBox.information(self, "Success", "Match deleted successfully")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete match: {str(e)}")

    def on_row_double_clicked(self, row, _):  # Use underscore for unused parameter
        snapshot_name = self.table.item(row, 0).data(Qt.UserRole)  # Get match_id from UserRole data of first column
        print(f"Debug - Opening match details for: {snapshot_name}")
        dialog = MatchDetailsDialog(self, snapshot_name)
        dialog.exec_()

    def purge_database(self):
        """Purge all data from database after confirmation"""
        dialog = PurgeConfirmDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            try:
                # Clear the table first to release any connections
                self.table.clearContents()
                self.table.setRowCount(0)
                
                # Clear filters
                self.date_filter.clear()
                self.date_filter.addItem("All Dates")
                self.map_filter.clear()
                self.map_filter.addItem("All Maps")
                
                # Process events to ensure UI updates are complete
                QApplication.processEvents()
                
                if self.parent.db.purge_database():
                    # Clear import tracking
                    self.parent.import_manager.clear_tracking()
                    
                    # Refresh displays
                    self.refresh_snapshots()
                    self.parent.load_data_from_db()
                    
                    QMessageBox.information(self, "Success", 
                        "Database has been purged successfully.\nA backup was created before purging.")
                else:
                    QMessageBox.critical(self, "Error", 
                        "Failed to purge database.")
            except Exception as e:
                QMessageBox.critical(self, "Error", 
                    f"Error during database purge: {str(e)}")
