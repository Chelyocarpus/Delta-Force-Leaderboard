import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QMenu, QAction, QMenuBar, QFileDialog, QMessageBox, QHBoxLayout, QLabel, QHeaderView, QLineEdit, QDialog
)
from PyQt5.QtCore import Qt, QSettings, QTimer
from PyQt5.QtGui import QIcon
import csv, sqlite3, os

from src.data.database import Database
from src.data.medals import MedalProcessor
from src.gui.dialogs.snapshot_viewer import SnapshotViewerDialog
from src.gui.dialogs.player_details import PlayerDetailsDialog
from src.gui.widgets.numeric_sort import NumericSortItem

from src.utils.constants import RESOURCES_DIR
from src.gui.dialogs.import_on_startup import ImportOnStartupDialog
from src.utils.constants import IMPORT_DIR
import glob

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Leaderboard")
        self.setGeometry(100, 100, 1000, 600)
        self.settings = QSettings('DeltaForce', 'Leaderboard')
        
        self.restore_window_state()

        # Set window icon
        icon_path = icon_path = os.path.join(RESOURCES_DIR, "favicon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            app_icon = QIcon(icon_path)
            QApplication.setWindowIcon(app_icon)

        # Initialize database
        self.db = Database()
        self.db_path = self.db.db_path  # Keep reference for compatibility
        self.medal_processor = MedalProcessor(self.db)
        
        # Create menu bar
        self.create_menu_bar()
        
        # Create the main widget
        widget = QWidget()
        layout = QVBoxLayout()
        widget.setLayout(layout)
        self.setCentralWidget(widget)

        # Create search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name...")
        self.search_input.textChanged.connect(self.on_search)
        search_layout.addWidget(self.search_input)
        layout.addLayout(search_layout)

        # Create the table widget
        self.table = QTableWidget()
        self.table.setColumnCount(7)  # Removed rank and class columns
        self.table.setHorizontalHeaderLabels([
            "Name", "Score", "Kills", "Deaths", 
            "Assists", "Revives", "Captures"
        ])
        self.table.setSortingEnabled(True)  # Enable sorting

        # Set column stretch behavior
        header = self.table.horizontalHeader()
        for i in range(self.table.columnCount()):
                header.setSectionResizeMode(i, QHeaderView.Stretch)

        # Load data from database
        self.load_data_from_db()

        # Adjust column widths and other properties
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setContextMenuPolicy(Qt.DefaultContextMenu)
        self.table.contextMenuEvent = self.tableContextMenuEvent
        self.table.installEventFilter(self)  # Install event filter
        layout.addWidget(self.table)
        self.current_snapshot = None  # Track current snapshot
        self.column_widths = []  # Add this to store column widths
        self.table.cellDoubleClicked.connect(self.on_row_double_clicked)
        self.NumericSortItem = NumericSortItem  # Make NumericSortItem available to dialogs

        self.table.setSelectionBehavior(QTableWidget.SelectRows)  # Select entire rows
        self.table.setSelectionMode(QTableWidget.SingleSelection)  # Allow only single row selection
        self.table.itemClicked.connect(self.on_item_clicked)

        # Setup auto-backup
        self.backup_timer = QTimer(self)
        self.backup_timer.timeout.connect(self.auto_backup)
        self.backup_timer.start(3600000)  # Backup every hour

    def closeEvent(self, event):
        self.save_window_state()
        super().closeEvent(event)

    def save_window_state(self):
        self.settings.setValue('window_geometry', self.saveGeometry())
        self.settings.setValue('window_state', self.saveState())

    def restore_window_state(self):
        if self.settings.value('window_geometry'):
            self.restoreGeometry(self.settings.value('window_geometry'))
        if self.settings.value('window_state'):
            self.restoreState(self.settings.value('window_state'))

    def create_menu_bar(self):
        menubar = self.menuBar()
        file_menu = menubar.addMenu("File")
        
        # Add export functionality
        export_action = QAction("Export Stats", self)
        export_action.triggered.connect(self.export_stats)
        export_action.setToolTip("Export current view to CSV")
        file_menu.addAction(export_action)
        
        import_action = QAction("Import CSV", self)
        import_action.triggered.connect(self.import_csv)
        file_menu.addAction(import_action)
        
        view_snapshots_action = QAction("View Snapshots", self)
        view_snapshots_action.triggered.connect(self.view_snapshots)
        file_menu.addAction(view_snapshots_action)

        # Add backup/restore menu
        backup_menu = menubar.addMenu("Backup")
        
        backup_action = QAction("Create Backup", self)
        backup_action.triggered.connect(self.auto_backup)
        backup_menu.addAction(backup_action)
        
        restore_action = QAction("Restore Backup", self)
        restore_action.triggered.connect(self.restore_from_backup)
        backup_menu.addAction(restore_action)

    def export_stats(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Export Stats", "", "CSV Files (*.csv)")
        if file_name:
            try:
                with open(file_name, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    # Write headers
                    headers = [self.table.horizontalHeaderItem(i).text() 
                             for i in range(self.table.columnCount())]
                    writer.writerow(headers)
                    # Write data
                    for row in range(self.table.rowCount()):
                        row_data = [self.table.item(row, col).text() 
                                  for col in range(self.table.columnCount())]
                        writer.writerow(row_data)
                QMessageBox.information(self, "Export Complete", 
                    "Statistics exported successfully!")
            except Exception as e:
                QMessageBox.critical(self, "Export Error", str(e))

    def save_column_widths(self):
        """Save current column widths"""
        self.column_widths = [self.table.columnWidth(i) 
                             for i in range(self.table.columnCount())]
    
    def restore_column_widths(self):
        """Restore saved column widths"""
        if self.column_widths:
            for i, width in enumerate(self.column_widths):
                self.table.setColumnWidth(i, width)

    def load_data_from_db(self):
        self.table.setSortingEnabled(False)  # Temporarily disable sorting
        self.save_column_widths()  # Save widths before refresh
        self.table.setRowCount(0)  # Clear existing rows
        
        search_text = self.search_input.text().lower()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            # Modified query to aggregate data across snapshots
            cursor.execute("""
                SELECT 
                    name,
                    SUM(score) as total_score,
                    SUM(kills) as total_kills,
                    SUM(deaths) as total_deaths,
                    SUM(assists) as total_assists,
                    SUM(revives) as total_revives,
                    SUM(captures) as total_captures
                FROM snapshots
                GROUP BY name
                HAVING LOWER(name) LIKE ?
                ORDER BY total_score DESC
            """, (f'%{search_text}%',))
            data = cursor.fetchall()
            
            if data:
                self.table.setRowCount(len(data))
                for row, rowData in enumerate(data):
                    for col, value in enumerate(rowData):
                        if col == 0:  # Name column
                            item = QTableWidgetItem(str(value))
                        else:  # Numeric columns
                            item = NumericSortItem(value)
                            item.setTextAlignment(Qt.AlignCenter)
                        self.table.setItem(row, col, item)
        
        if not self.column_widths:  # Only resize if no saved widths
            self.table.resizeColumnsToContents()
        else:
            self.restore_column_widths()
            
        self.table.setSortingEnabled(True)  # Re-enable sorting
        self.table.horizontalHeader().setSortIndicator(1, Qt.DescendingOrder)  # Default sort by score
        
        # Add tooltips to column headers
        tooltips = [
            "Player Name",
            "Total Score Across All Games",
            "Total Kills Across All Games",
            "Total Deaths Across All Games",
            "Total Assists Across All Games",
            "Total Revives Across All Games",
            "Total Captures Across All Games"
        ]
        for col, tooltip in enumerate(tooltips):
            self.table.horizontalHeaderItem(col).setToolTip(tooltip)

    def on_search(self, text):
        """Handler for search input changes"""
        self.load_data_from_db()

    def check_duplicate_data(self, cursor, rows):
        # Get a hash of the data by concatenating all values
        data_hash = []
        for row in rows:
            data_hash.append('|'.join(str(x) for x in row))
        data_hash = sorted(data_hash)  # Sort to ensure consistent comparison
        
        # Check existing snapshots
        cursor.execute("SELECT DISTINCT snapshot_name FROM snapshots")
        snapshots = cursor.fetchall()
        
        for snapshot in snapshots:
            cursor.execute("""
                SELECT rank, class, name, score, kills, deaths, assists, revives, captures 
                FROM snapshots 
                WHERE snapshot_name = ?
            """, (snapshot[0],))
            existing_data = cursor.fetchall()
            
            # Create hash of existing data
            existing_hash = []
            for row in existing_data:
                existing_hash.append('|'.join(str(x) for x in row))
            existing_hash = sorted(existing_hash)
            
            # Compare hashes
            if data_hash == existing_hash:
                return True, snapshot[0]
        
        return False, None

    def import_csv(self):
        file_names, _ = QFileDialog.getOpenFileNames(self, "Import CSV Files", "", "CSV Files (*.csv)")
        
        if file_names:
            imported_count = 0
            skipped_count = 0
            
            for file_name in file_names:
                try:
                    with open(file_name, newline='') as csvfile:
                        csvreader = csv.reader(csvfile)
                        headers = next(csvreader)  # Skip header row
                        rows = list(csvreader)
                    
                    if not rows:
                        continue
                        
                    # Get metadata from first row
                    first_row = rows[0]
                    snapshot_name = f"{first_row[2]} - {first_row[1]} ({first_row[0]})"
                    timestamp = first_row[2]  # Data column contains timestamp
                    
                    # Check for duplicate data
                    is_duplicate, existing_snapshot = self.db.check_duplicate_data(rows)
                    
                    if is_duplicate:
                        skipped_count += 1
                        self.statusBar().showMessage(
                            f"Skipped duplicate data (matches snapshot: {existing_snapshot})", 
                            3000
                        )
                        continue
                    
                    # Import the snapshot if not duplicate
                    self.db.import_snapshot(snapshot_name, timestamp, rows)
                    imported_count += 1
                    self.current_snapshot = snapshot_name
                    self.statusBar().showMessage(f"Imported: {snapshot_name}", 3000)

                except Exception as e:
                    QMessageBox.critical(self, "Error", 
                        f"Failed to import {os.path.basename(file_name)}: {str(e)}")
            
            self.load_data_from_db()
            
            # Show summary message
            summary = f"Successfully imported {imported_count} file(s)"
            if skipped_count > 0:
                summary += f"\nSkipped {skipped_count} duplicate file(s)"
            QMessageBox.information(self, "Import Complete", summary)

    def view_snapshots(self):
        dialog = SnapshotViewerDialog(self)
        dialog.exec_()

    def eventFilter(self, source, event):
        # Remove delete key handling
        return super().eventFilter(source, event)

    def tableContextMenuEvent(self, event):
        context_menu = QMenu(self)
        
        # Keep only the selection actions
        select_all_action = QAction("Select All", self)
        select_all_action.triggered.connect(self.table.selectAll)
        context_menu.addAction(select_all_action)
        
        clear_selection_action = QAction("Clear Selection", self)
        clear_selection_action.triggered.connect(self.table.clearSelection)
        context_menu.addAction(clear_selection_action)
        
        context_menu.exec_(event.globalPos())

    def on_snapshot_deleted(self, snapshot_name):
        """Handle snapshot deletion updates"""
        if snapshot_name == self.current_snapshot:
            self.load_data_from_db()  # Refresh main window if current snapshot was deleted
            self.current_snapshot = None

    def on_row_double_clicked(self, row, column):
        player_name = self.table.item(row, 0).text()
        dialog = PlayerDetailsDialog(self, player_name)
        dialog.exec_()

    def on_item_clicked(self, item):
        """Select the entire row when any cell is clicked"""
        self.table.selectRow(item.row())

    def auto_backup(self):
        """Perform automatic database backup"""
        try:
            backup_path = self.db.backup_database()
            self.statusBar().showMessage(f"Backup created: {backup_path}", 3000)
        except Exception as e:
            self.statusBar().showMessage(f"Backup failed: {str(e)}", 5000)

    def restore_from_backup(self):
        """Restore database from a backup file"""
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Select Backup File", "", "Database Backup (*.backup)")
        
        if file_name:
            reply = QMessageBox.warning(self, 'Restore Database',
                'This will overwrite the current database. Continue?',
                QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                try:
                    self.db.restore_backup(file_name)
                    self.load_data_from_db()
                    QMessageBox.information(self, "Success", 
                        "Database restored successfully!")
                except Exception as e:
                    QMessageBox.critical(self, "Error", 
                        f"Failed to restore database: {str(e)}")

    def check_for_new_files(self):
        """Check for new CSV files in the import directory"""
        # Create import directory if it doesn't exist
        if not os.path.exists(IMPORT_DIR):
            os.makedirs(IMPORT_DIR, exist_ok=True)
            return

        # Get all CSV files in the import directory using the correct path
        csv_files = glob.glob(os.path.join(IMPORT_DIR, "*_processed.csv"))
        if not csv_files:
            return

        new_files = []
        for file_path in csv_files:
            try:
                with open(file_path, newline='') as csvfile:
                    csvreader = csv.reader(csvfile)
                    headers = next(csvreader)  # Skip header row
                    rows = list(csvreader)
                    
                    if rows:
                        is_duplicate, _ = self.db.check_duplicate_data(rows)
                        if not is_duplicate:
                            new_files.append(file_path)
            except Exception as e:
                print(f"Error checking file {file_path}: {e}")

        if new_files:
            dialog = ImportOnStartupDialog(
                [os.path.basename(f) for f in new_files], 
                self
            )
            if dialog.exec_() == QDialog.Accepted:
                selected_files = dialog.get_selected_files()
                for filename in selected_files:
                    file_path = os.path.join(IMPORT_DIR, filename)
                    try:
                        with open(file_path, newline='') as csvfile:
                            csvreader = csv.reader(csvfile)
                            headers = next(csvreader)
                            rows = list(csvreader)
                            
                            if rows:
                                first_row = rows[0]
                                snapshot_name = f"{first_row[2]} - {first_row[1]} ({first_row[0]})"
                                timestamp = first_row[2]
                                
                                self.db.import_snapshot(snapshot_name, timestamp, rows)
                                self.statusBar().showMessage(f"Imported: {filename}", 3000)
                    except Exception as e:
                        QMessageBox.critical(self, "Error", 
                            f"Failed to import {filename}: {str(e)}")

                self.load_data_from_db()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.check_for_new_files()  # Add this line before showing the window
    window.show()
    sys.exit(app.exec_())
