from PyQt5.QtWidgets import (
    QDialog, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox, QInputDialog, QApplication
)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from ..widgets.numeric_sort import NumericSortItem
from ...utils.constants import (
    SNAPSHOT_WINDOW_SIZE, SNAPSHOT_TABLE_COLUMNS
)

class SnapshotViewerDialog(QDialog):
    snapshot_deleted = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Snapshot Viewer")
        self.setGeometry(200, 200, 1200, 600)
        
        self.init_ui()
        self.refresh_snapshots()

    def init_ui(self):
        main_layout = QHBoxLayout()
        
        # Left panel
        left_panel = QVBoxLayout()
        
        # Search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search snapshots...")
        self.search_input.textChanged.connect(self.refresh_snapshots)
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_input)
        left_panel.addLayout(search_layout)
        
        # Overview table
        self.overview_table = QTableWidget()
        self.overview_table.setColumnCount(3)
        self.overview_table.setHorizontalHeaderLabels(["Date", "Map", "Outcome"])
        self.overview_table.setSortingEnabled(True)
        self.overview_table.selectionModel().selectionChanged.connect(self.on_overview_selection)
        left_panel.addWidget(self.overview_table)
        
        # Control buttons
        buttons_layout = QHBoxLayout()
        delete_btn = QPushButton("Delete Selected")
        delete_btn.clicked.connect(self.delete_selected_snapshot)
        buttons_layout.addWidget(delete_btn)
        
        purge_btn = QPushButton("Purge Database")
        purge_btn.setStyleSheet("background-color: #ff6b6b;")
        purge_btn.clicked.connect(self.purge_database)
        buttons_layout.addWidget(purge_btn)
        
        left_panel.addLayout(buttons_layout)
        
        left_widget = QWidget()
        left_widget.setLayout(left_panel)
        main_layout.addWidget(left_widget, 1)
        
        # Right panel
        right_panel = QVBoxLayout()
        
        self.table = QTableWidget()
        self.table.setColumnCount(len(SNAPSHOT_TABLE_COLUMNS))
        self.table.setHorizontalHeaderLabels(SNAPSHOT_TABLE_COLUMNS)
        self.table.setSortingEnabled(True)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemClicked.connect(self.on_item_clicked)
        right_panel.addWidget(self.table)
        
        right_widget = QWidget()
        right_widget.setLayout(right_panel)
        main_layout.addWidget(right_widget, 2)
        
        self.setLayout(main_layout)
        self.snapshot_deleted.connect(self.parent.on_snapshot_deleted)

    def refresh_snapshots(self):
        self.overview_table.setSortingEnabled(False)
        search_text = self.search_input.text().lower()
        
        with self.parent.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT timestamp,
                    SUBSTR(snapshot_name, INSTR(snapshot_name, ' - ') + 3, 
                        INSTR(snapshot_name, ' (') - INSTR(snapshot_name, ' - ') - 3) as map_name,
                    SUBSTR(snapshot_name, INSTR(snapshot_name, '('), 
                        LENGTH(snapshot_name) - INSTR(snapshot_name, '(') + 1) as outcome,
                    snapshot_name
                FROM snapshots 
                WHERE LOWER(snapshot_name) LIKE ?
                ORDER BY timestamp DESC
            """, (f'%{search_text}%',))
            snapshots = cursor.fetchall()
            
            self.overview_table.setRowCount(len(snapshots))
            for row, data in enumerate(snapshots):
                self.overview_table.setItem(row, 0, QTableWidgetItem(data[0]))
                self.overview_table.setItem(row, 1, QTableWidgetItem(data[1]))
                self.overview_table.setItem(row, 2, QTableWidgetItem(data[2]))
                self.overview_table.item(row, 0).setData(Qt.UserRole, data[3])
        
        self.overview_table.resizeColumnsToContents()
        self.overview_table.setSortingEnabled(True)
    
    def on_overview_selection(self, selected, deselected):
        try:
            # Ignore selection while loading
            if not selected.indexes() or getattr(self, '_loading', False):
                return

            self._loading = True  # Set loading flag
            self.overview_table.setEnabled(False)  # Disable overview table
            QApplication.processEvents()  # Let UI update

            row = selected.indexes()[0].row()
            snapshot_name = self.overview_table.item(row, 0).data(Qt.UserRole)
            print(f"\nSelected snapshot row {row}, name: {snapshot_name}")
            
            if snapshot_name:
                # Use shorter delay for better responsiveness
                QTimer.singleShot(50, lambda: self.delayed_load_snapshot(snapshot_name))
            else:
                print("No snapshot name found for row")
                self._loading = False
                self.overview_table.setEnabled(True)
                
        except Exception as e:
            print(f"Error in snapshot selection: {str(e)}")
            self._loading = False
            self.overview_table.setEnabled(True)

    def delayed_load_snapshot(self, snapshot_name):
        """Load snapshot data with UI updates between chunks"""
        try:
            # Clear current data first
            self.table.clearContents()
            self.table.setRowCount(0)
            self.table.setSortingEnabled(False)
            QApplication.processEvents()

            self.load_selected_snapshot(snapshot_name)

        finally:
            self._loading = False
            self.overview_table.setEnabled(True)
            self.table.setSortingEnabled(True)
            QApplication.processEvents()

    def load_selected_snapshot(self, snapshot_name):
        if not snapshot_name:
            return
            
        try:
            with self.parent.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Get row count first
                cursor.execute("SELECT COUNT(*) FROM snapshots WHERE snapshot_name = ?", (snapshot_name,))
                total_rows = cursor.fetchone()[0]
                if not total_rows:
                    return
                    
                print(f"Loading {total_rows} rows for snapshot: {snapshot_name}")
                self.table.setRowCount(total_rows)
                
                # Load data in smaller chunks with more frequent UI updates
                CHUNK_SIZE = 5  # Reduced chunk size
                for offset in range(0, total_rows, CHUNK_SIZE):
                    cursor.execute("""
                        SELECT 
                            SUBSTR(snapshot_name, INSTR(snapshot_name, '('), 
                                LENGTH(snapshot_name) - INSTR(snapshot_name, '(') + 1) as outcome,
                            SUBSTR(snapshot_name, INSTR(snapshot_name, ' - ') + 3, 
                                INSTR(snapshot_name, ' (') - INSTR(snapshot_name, ' - ') - 3) as map_name,
                            timestamp as date,
                            team, rank, class, name, score,
                            kills, deaths, assists, revives, captures,
                            combat_medal, capture_medal, logistics_medal, intelligence_medal
                        FROM snapshots 
                        WHERE snapshot_name = ?
                        ORDER BY score DESC
                        LIMIT ? OFFSET ?
                    """, (snapshot_name, CHUNK_SIZE, offset))
                    
                    chunk_data = cursor.fetchall()
                    self.populate_chunk(chunk_data, offset)
                    QApplication.processEvents()  # Process events after each chunk
                
                # Final UI update
                self.table.resizeColumnsToContents()
                print("Finished loading snapshot data")
                
        except Exception as e:
            print(f"Error loading snapshot: {str(e)}")
            self.table.setRowCount(0)

    def populate_chunk(self, chunk_data, start_row):
        """Populate a chunk of data into the table"""
        for i, row in enumerate(chunk_data):
            table_row = start_row + i
            try:
                row_list = list(row)
                row_list = ['' if v is None else v for v in row_list]
                reordered = tuple(row_list[:3] + [row_list[3], row_list[4]] + row_list[5:])
                
                for col, value in enumerate(reordered):
                    if col in (0, 1, 2, 3, 5, 6) or col >= 13:
                        item = QTableWidgetItem(str(value))
                    else:
                        item = NumericSortItem(value if value != '' else 0)
                        item.setTextAlignment(Qt.AlignCenter)
                    self.table.setItem(table_row, col, item)
                    
            except Exception as e:
                print(f"Error processing row {table_row}: {str(e)}")
                continue

    def populate_table(self, data):
        try:
            self.table.setRowCount(len(data))
            for row, record in enumerate(data):
                for col, value in enumerate(record):
                    try:
                        if col in (0, 1, 2, 3, 5, 6) or col >= 13:  # Text columns including medals
                            item = QTableWidgetItem(str(value) if value is not None else "")
                        else:  # Numeric columns
                            if value is not None and value != '':
                                item = NumericSortItem(value)
                            else:
                                item = NumericSortItem(0)
                            item.setTextAlignment(Qt.AlignCenter)
                        self.table.setItem(row, col, item)
                    except Exception as e:
                        print(f"Error setting cell [{row}][{col}] = {value}: {str(e)}")
                        self.table.setItem(row, col, QTableWidgetItem("Error"))
        except Exception as e:
            print(f"Error populating table: {str(e)}")
            self.table.setRowCount(0)
            QMessageBox.warning(self, "Error", 
                f"Failed to display snapshot data: {str(e)}")

    def delete_selected_snapshot(self):
        selected_items = self.overview_table.selectedItems()
        if not selected_items:
            return
            
        row = selected_items[0].row()
        snapshot_name = self.overview_table.item(row, 0).data(Qt.UserRole)
        
        reply = QMessageBox.question(self, 'Delete Snapshot',
                                   f'Are you sure you want to delete "{snapshot_name}"?',
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                self.parent.db.delete_snapshot(snapshot_name)
                self.refresh_snapshots()
                self.parent.load_data_from_db()
                self.snapshot_deleted.emit(snapshot_name)
                
                if self.overview_table.rowCount() > 0:
                    first_snapshot = self.overview_table.item(0, 0).data(Qt.UserRole)
                    self.load_selected_snapshot(first_snapshot)
                else:
                    self.table.setRowCount(0)
                
                QMessageBox.information(self, "Success", 
                    f"Snapshot '{snapshot_name}' deleted successfully")
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", 
                    f"Failed to delete snapshot: {str(e)}")

    def purge_database(self):
        reply = QMessageBox.warning(
            self,
            "Purge Database",
            "WARNING: This will permanently delete ALL snapshots!\n\n"
            "Are you absolutely sure you want to continue?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            confirm = QMessageBox.warning(
                self,
                "Confirm Purge",
                "This action CANNOT be undone!\n\n"
                "Type 'PURGE' to confirm:",
                QMessageBox.Ok
            )
            
            if confirm == QMessageBox.Ok:
                text, ok = QInputDialog.getText(self, "Final Confirmation", "Type 'PURGE' to confirm:")
                if ok and text == "PURGE":
                    try:
                        self.parent.db.purge_database()
                        self.refresh_snapshots()
                        self.table.setRowCount(0)
                        self.parent.load_data_from_db()
                        QMessageBox.information(self, "Success", "Database purged successfully")
                    except Exception as e:
                        QMessageBox.critical(self, "Error", f"Failed to purge database: {str(e)}")

    def on_item_clicked(self, item):
        """Select the entire row when any cell is clicked"""
        self.table.selectRow(item.row())
