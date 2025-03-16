import sqlite3
import re
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, 
                           QTableWidgetItem, QPushButton, QLineEdit, QLabel,
                           QHeaderView, QMessageBox, QComboBox, QApplication, QMenu)
from PyQt5.QtCore import Qt
from .match_details import MatchDetailsDialog
from .purge_confirm import PurgeConfirmDialog
from .edit_snapshot import EditSnapshotDialog

class SnapshotViewerDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Match Database Manager")
        self.setModal(True)
        self.setMinimumSize(800, 600)
        self.init_ui()
        self.refresh_snapshots()
        
        # Add double-click handler
        self.table.cellDoubleClicked.connect(self.on_row_double_clicked)

    def init_ui(self):
        layout = QVBoxLayout()

        # Simple search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search matches...")
        self.search_input.textChanged.connect(self.refresh_snapshots)
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Create table with modified columns (date/time split, no players/score)
        self.table = QTableWidget()
        self.table.setColumnCount(5)  # Reduced to 5 columns
        self.table.setHorizontalHeaderLabels([
            "Date", "Time", "Map", "Outcome", "Team"
        ])
        
        # Set table properties
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        
        # Set column properties
        header = self.table.horizontalHeader()
        for i in range(self.table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        
        layout.addWidget(self.table)

        # Add context menu to table
        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        # Enhanced filter options with date filter
        filter_layout = QHBoxLayout()
        
        # Date filter
        self.date_filter = QComboBox()
        self.date_filter.addItem("All Dates")
        self.date_filter.currentTextChanged.connect(self.refresh_snapshots)
        filter_layout.addWidget(QLabel("Date:"))
        filter_layout.addWidget(self.date_filter)
        
        # Map filter
        self.map_filter = QComboBox()
        self.map_filter.addItem("All Maps")
        self.map_filter.currentTextChanged.connect(self.refresh_snapshots)
        filter_layout.addWidget(QLabel("Map:"))
        filter_layout.addWidget(self.map_filter)
        
        layout.addLayout(filter_layout)

        # Button row
        button_layout = QHBoxLayout()
        
        # Database management buttons
        edit_button = QPushButton("Edit Selected")
        edit_button.clicked.connect(self.edit_selected_snapshot)
        button_layout.addWidget(edit_button)
        
        view_button = QPushButton("View Details")
        view_button.clicked.connect(self.view_selected_snapshot)
        button_layout.addWidget(view_button)
        
        delete_button = QPushButton("Delete Selected")
        delete_button.clicked.connect(self.delete_selected_snapshot)
        button_layout.addWidget(delete_button)
        
        # Add purge button with warning styling
        purge_button = QPushButton("Purge Database")
        purge_button.setStyleSheet("background-color: #ff4444; color: white; font-weight: bold;")
        purge_button.clicked.connect(self.purge_database)
        button_layout.addWidget(purge_button)
        
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)
        
        layout.addLayout(button_layout)
        
        # Status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        self.load_filters()

    def load_filters(self):
        """Load filter options from database (maps and dates)"""
        try:
            with self.parent.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Check if table has data first
                cursor.execute("SELECT COUNT(*) FROM matches")
                if cursor.fetchone()[0] == 0:
                    return
                
                # First detect the date column
                cursor.execute("PRAGMA table_info(matches)")
                columns = [col[1] for col in cursor.fetchall()]
                date_column = 'data'  # Default column name
                
                # Load unique dates (just the date part, not time)
                query = f"""
                    SELECT DISTINCT 
                        CASE 
                            WHEN instr({date_column}, ':') > 0 
                            THEN TRIM(substr({date_column}, 1, instr({date_column}, ':') - 3))
                            ELSE {date_column} 
                        END as date_part
                    FROM matches
                    ORDER BY {date_column} DESC
                """
                cursor.execute(query)
                dates = [row[0] for row in cursor.fetchall()]
                
                # Handle case where SQL splitting failed
                unique_dates = set()
                for date_str in dates:
                    if ':' in date_str:  # SQL splitting failed
                        date_part, _ = self._split_datetime(date_str)
                        unique_dates.add(date_part)
                    else:
                        unique_dates.add(date_str)
                
                # Update the date filter
                self.date_filter.clear()
                self.date_filter.addItem("All Dates")
                self.date_filter.addItems(sorted(list(unique_dates), reverse=True))
                
                # Load maps
                cursor.execute("SELECT DISTINCT map FROM matches ORDER BY map")
                maps = cursor.fetchall()
                if maps:
                    self.map_filter.clear()
                    self.map_filter.addItem("All Maps")
                    self.map_filter.addItems([row[0] for row in maps])
        except Exception as e:
            self.status_label.setText(f"Error loading filters: {str(e)}")

    def refresh_snapshots(self):
        self.table.setRowCount(0)  # Clear table first
        self.status_label.setText("Loading data...")
        
        try:
            search_text = self.search_input.text().lower()
            map_filter = self.map_filter.currentText()
            date_filter = self.date_filter.currentText()
            
            with self.parent.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # First detect the date column
                cursor.execute("PRAGMA table_info(matches)")
                columns = [col[1] for col in cursor.fetchall()]
                date_column = 'data'  # Default column name
                
                # Modified query to properly split date and time and support filtering
                query = f"""
                    SELECT 
                        CASE 
                            WHEN instr({date_column}, ':') > 0 
                            THEN TRIM(substr({date_column}, 1, instr({date_column}, ':') - 3))
                            ELSE {date_column} 
                        END as date_part,
                        CASE 
                            WHEN instr({date_column}, ':') > 0 
                            THEN TRIM(substr({date_column}, instr({date_column}, ':') - 2))
                            ELSE ''
                        END as time_part,
                        map,
                        outcome,
                        team,
                        {date_column} as full_date,
                        outcome || ' - ' || map || ' - ' || {date_column} || ' - ' || team as snapshot_name
                    FROM matches m1
                    WHERE (LOWER(map) LIKE ? OR LOWER(outcome) LIKE ? OR LOWER({date_column}) LIKE ?)
                        AND (? = 'All Maps' OR map = ?)
                        AND (? = 'All Dates' OR 
                             CASE 
                                WHEN instr({date_column}, ':') > 0 
                                THEN TRIM(substr({date_column}, 1, instr({date_column}, ':') - 3))
                                ELSE {date_column} 
                             END = ?)
                    GROUP BY {date_column}, map, outcome, team
                    ORDER BY {date_column} DESC, map ASC
                """
                
                cursor.execute(query, (
                    f'%{search_text}%', f'%{search_text}%', f'%{search_text}%',
                    map_filter, map_filter,
                    date_filter, date_filter
                ))
                
                row_count = 0
                for row_idx, row_data in enumerate(cursor.fetchall()):
                    self.table.insertRow(row_idx)
                    date_part, time_part, map_name, outcome, team, full_date, match_id = row_data
                    
                    # If SQL couldn't split correctly, try to do it in Python
                    if ':' in date_part:  # This means SQL splitting failed
                        date_part, time_part = self._split_datetime(full_date)
                    
                    # Format the date and time for display
                    date_display = date_part.strip() if date_part else "Unknown"
                    time_display = time_part.strip() if time_part else ""
                    
                    items = [
                        (date_display, Qt.AlignCenter),
                        (time_display, Qt.AlignCenter),
                        (map_name, Qt.AlignLeft),
                        (outcome, Qt.AlignCenter),
                        (team, Qt.AlignCenter)
                    ]
                    
                    for col, (value, alignment) in enumerate(items):
                        item = QTableWidgetItem(str(value))
                        item.setTextAlignment(alignment)
                        if col == 0:  # Store match_id in first column
                            item.setData(Qt.UserRole, match_id)
                            # Also store full date for editing purposes
                            item.setData(Qt.UserRole + 1, full_date)
                        self.table.setItem(row_idx, col, item)
                    row_count += 1
                
                self.status_label.setText(f"Showing {row_count} matches")
        
        except sqlite3.Error as e:
            self.status_label.setText(f"Database error: {str(e)}")
            QMessageBox.critical(self, "Database Error", 
                f"Failed to access the database: {str(e)}")
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            QMessageBox.critical(self, "Error",
                f"An unexpected error occurred: {str(e)}")
    
    def _split_datetime(self, datetime_str):
        """Split a datetime string into date and time parts
        Handles formats like '20 Jan 2025 00:15:11'"""
        if not datetime_str:
            return "", ""
        
        # Try to match time pattern HH:MM:SS
        time_match = re.search(r'(\d{1,2}:\d{2}(?::\d{2})?)', datetime_str)
        if time_match:
            time_part = time_match.group(1)
            # Date is everything before the time
            date_part = datetime_str[:time_match.start()].strip()
            return date_part, time_part
        
        # If no time pattern found, return the full string as date
        return datetime_str, ""

    def view_selected_snapshot(self):
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            self.status_label.setText("No match selected")
            return
            
        row = selected_rows[0].row()
        snapshot_name = self.table.item(row, 0).data(Qt.UserRole)
        if snapshot_name:
            self.on_row_double_clicked(row, 0)
        else:
            self.status_label.setText("Cannot view details: missing snapshot ID")

    def delete_selected_snapshot(self):
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            self.status_label.setText("No match selected")
            return
            
        row = selected_rows[0].row()
        match_id = self.table.item(row, 0).data(Qt.UserRole)
        date_display = self.table.item(row, 0).text()
        time_display = self.table.item(row, 1).text()
        map_name = self.table.item(row, 2).text()
        outcome = self.table.item(row, 3).text()
        team = self.table.item(row, 4).text()
        
        # Create a readable description for the confirmation dialog
        match_desc = f"{date_display}"
        if time_display:
            match_desc += f" {time_display}"
        match_desc += f" - {map_name}"
        
        reply = QMessageBox.question(self, 'Delete Match',
            f'Are you sure you want to delete:\n{match_desc}?',
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            
        if reply == QMessageBox.Yes:
            try:
                with self.parent.db.get_connection() as conn:
                    cursor = conn.cursor()
                    # Delete using the values directly from the table
                    full_date = self.table.item(row, 0).data(Qt.UserRole + 1)
                    cursor.execute("""
                        DELETE FROM matches 
                        WHERE data = ? 
                        AND map = ? 
                        AND outcome = ? 
                        AND team = ?
                    """, (full_date, map_name, outcome, team))
                    
                    deleted_rows = cursor.rowcount
                    conn.commit()
                    
                self.refresh_snapshots()
                if hasattr(self.parent, 'on_snapshot_deleted'):
                    self.parent.on_snapshot_deleted(match_id)
                self.status_label.setText(f"Deleted {deleted_rows} match entries")
                
            except sqlite3.Error as e:
                self.status_label.setText(f"Delete failed: {str(e)}")
                QMessageBox.critical(self, "Database Error",
                    f"Failed to delete match: {str(e)}")
            except Exception as e:
                self.status_label.setText(f"Error: {str(e)}")
                QMessageBox.critical(self, "Error",
                    f"An unexpected error occurred: {str(e)}")

    def on_row_double_clicked(self, row, _):
        snapshot_name = self.table.item(row, 0).data(Qt.UserRole)
        self.status_label.setText(f"Viewing match details...")
        try:
            # Create a connection that the MatchDetailsDialog can use
            if not hasattr(self, 'db_path'):
                self.db_path = self.parent.db.db_path
                
            dialog = MatchDetailsDialog(self, snapshot_name)
            dialog.exec_()
            self.status_label.setText("Ready")
        except Exception as e:
            self.status_label.setText(f"Error showing match details: {str(e)}")
            QMessageBox.critical(self, "Error", 
                f"Failed to display match details: {str(e)}")

    def purge_database(self):
        """Purge all data from database after confirmation"""
        dialog = PurgeConfirmDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            try:
                self.status_label.setText("Purging database...")
                # Clear the table first
                self.table.clearContents()
                self.table.setRowCount(0)
                
                # Clear filters
                self.date_filter.clear()
                self.date_filter.addItem("All Dates")
                self.map_filter.clear()
                self.map_filter.addItem("All Maps")
                
                # Process events to ensure UI updates
                QApplication.processEvents()
                
                if self.parent.db.purge_database():
                    # Clear import tracking if available
                    if hasattr(self.parent, 'import_manager'):
                        self.parent.import_manager.clear_tracking()
                    
                    # Refresh displays
                    self.refresh_snapshots()
                    if hasattr(self.parent, 'load_data_from_db'):
                        self.parent.load_data_from_db()
                    
                    self.status_label.setText("Database purged successfully")
                    QMessageBox.information(self, "Success", 
                        "Database has been purged. A backup was created.")
                else:
                    self.status_label.setText("Database purge failed")
                    raise RuntimeError("Database purge operation failed")
                    
            except Exception as e:
                self.status_label.setText(f"Purge error: {str(e)}")
                QMessageBox.critical(self, "Error",
                    f"An error occurred during database purge: {str(e)}")

    def show_context_menu(self, position):
        if not self.table.selectedItems():
            return
            
        menu = QMenu()
        view_action = menu.addAction("View Details")
        edit_action = menu.addAction("Edit Entry")
        delete_action = menu.addAction("Delete")
        
        action = menu.exec_(self.table.mapToGlobal(position))
        
        row = self.table.selectedItems()[0].row()
        snapshot_name = self.table.item(row, 0).data(Qt.UserRole)
        
        if action == view_action:
            self.on_row_double_clicked(row, 0)
        elif action == edit_action:
            self.edit_selected_snapshot()
        elif action == delete_action:
            self.delete_selected_snapshot()

    def edit_selected_snapshot(self):
        """Open edit dialog for the selected snapshot"""
        selected_rows = self.table.selectedItems()
        if not selected_rows:
            self.status_label.setText("No match selected")
            return
            
        row = selected_rows[0].row()
        snapshot_name = self.table.item(row, 0).data(Qt.UserRole)
        full_date = self.table.item(row, 0).data(Qt.UserRole + 1)
        
        # Get the individual field values
        date_display = self.table.item(row, 0).text()
        time_display = self.table.item(row, 1).text()
        map_name = self.table.item(row, 2).text()
        outcome = self.table.item(row, 3).text()
        team = self.table.item(row, 4).text()
        
        # Original values for update query
        original_values = {
            'snapshot_name': snapshot_name,
            'full_date': full_date,
            'date': date_display,
            'time': time_display,
            'map': map_name,
            'outcome': outcome, 
            'team': team
        }
        
        try:
            dialog = EditSnapshotDialog(self, original_values)
            if dialog.exec_() == QDialog.Accepted:
                self.status_label.setText("Match updated successfully")
                self.refresh_snapshots()
                # Update parent if needed
                if hasattr(self.parent, 'load_data_from_db'):
                    self.parent.load_data_from_db()
        except Exception as e:
            self.status_label.setText(f"Edit error: {str(e)}")
            QMessageBox.critical(self, "Error", 
                f"Failed to edit match: {str(e)}")
