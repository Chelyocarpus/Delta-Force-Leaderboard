import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QMenu, QAction, QMenuBar, QFileDialog, QMessageBox, QHBoxLayout, QLabel, QHeaderView, QLineEdit, QDialog
)
from PyQt5.QtCore import Qt, QSettings, QTimer
from PyQt5.QtGui import QIcon, QColor  # Add QColor import
import csv, sqlite3, os, shutil  # Added shutil import here

try:
    import markdown
except ImportError:
    print("Markdown package not found. Release notes will be displayed as plain text.")
    # Create a dummy markdown module to prevent errors
    class DummyMarkdown:
        @staticmethod
        def markdown(text, **kwargs):
            return f"<pre>{text}</pre>"
    markdown = DummyMarkdown()

from src.data.database import Database
from src.data.medals import MedalProcessor
from src.gui.dialogs.snapshot_viewer import SnapshotViewerDialog
from src.gui.dialogs.player_details import PlayerDetailsDialog
from src.gui.widgets.numeric_sort import NumericSortItem
from src.gui.dialogs.update_dialog import UpdateDialog
from src.gui.dialogs.onboarding_dialog import OnboardingDialog

from src.utils.constants import RESOURCES_DIR
from src.utils.constants import IMPORT_DIR
from src.utils.constants import APP_VERSION
from src.utils.constants import ROOT_DIR  # Added ROOT_DIR import
from src.utils.update_checker import UpdateChecker
import glob
from src.gui.dialogs.import_on_startup import ImportManager, ImportStartupDialog
from src.gui.dialogs.import_progress import ImportProgressDialog  # Add the new import

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        # Add this near the start of __init__
        self.current_snapshot = None
        self.setWindowTitle(f"Leaderboard {APP_VERSION}")
        self.setGeometry(100, 100, 1000, 600)
        self.settings = QSettings('DeltaForce', 'Leaderboard')
        
        # Check if this is the first run and show onboarding if needed
        self.player_name = self.settings.value('player_name', '')
        if not self.player_name:
            QTimer.singleShot(100, self.show_onboarding)
            
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
        
        # Create main widget and layout
        self.central_widget = QWidget()
        self.main_layout = QVBoxLayout()
        self.central_widget.setLayout(self.main_layout)
        self.setCentralWidget(self.central_widget)

        # Create search bar
        search_layout = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search by name...")
        self.search_input.textChanged.connect(self.on_search)
        search_layout.addWidget(self.search_input)
        
        self.main_layout.addLayout(search_layout)

        # Create table
        self.setup_table()
        
        # Load initial data
        self.load_data_from_db()
        
        # Setup other components
        self.setup_auto_backup()
        self.setup_import_manager()
        
        # Check for new files on startup
        QTimer.singleShot(0, self.check_new_files_on_startup)
        
        # Check for updates if enabled, but use a slightly longer delay
        if self.settings.value('check_updates_on_startup', True, type=bool):
            QTimer.singleShot(2000, lambda: self.check_for_updates(manual_check=False, force_check=True))

    def show_onboarding(self):
        """Show the onboarding dialog to set player name"""
        dialog = OnboardingDialog(self)
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            self.player_name = dialog.get_player_name()
            self.settings.setValue('player_name', self.player_name)
            
            # Refresh data to highlight player's row
            self.load_data_from_db()

    def show_player_name_dialog(self):
        """Show dialog to change player name"""
        dialog = OnboardingDialog(self)
        if self.player_name:
            dialog.name_input.setText(self.player_name)
            dialog.validate_input(self.player_name)
        
        if dialog.exec_() == QDialog.Accepted and dialog.get_player_name():
            old_name = self.player_name
            self.player_name = dialog.get_player_name()
            self.settings.setValue('player_name', self.player_name)
            
            self.load_data_from_db()

            # Close any existing player details dialogs without reopening
            for widget in QApplication.topLevelWidgets():
                if isinstance(widget, PlayerDetailsDialog):
                    widget.close()

    def setup_auto_backup(self):
        """Setup automatic backup timer"""
        self.backup_timer = QTimer(self)
        self.backup_timer.timeout.connect(self.create_backup)
        self.backup_timer.start(3600000)  # Backup every hour

    def create_backup(self):
        """Perform automatic database backup"""
        try:
            backup_path = self.db.backup_database()
            self.statusBar().showMessage(f"Backup created: {backup_path}", 3000)
        except Exception as e:
            self.statusBar().showMessage(f"Backup failed: {str(e)}", 5000)

    def setup_import_manager(self):
        """Setup import manager and run initial check"""
        self.import_manager = ImportManager()

    def setup_table(self):
        self.table = QTableWidget()
        
        # Define the column order we want to display
        ordered_columns = [
            'name',
            'score',
            'kills',
            'deaths',
            'assists',
            'revives',
            'captures',
            'vehicle_damage',
            'tactical_respawn'
        ]
        
        # Get table info and filter columns
        table_info = self.db.get_table_info()
        if 'matches' in table_info:
            excluded_columns = [
                'id', 'snapshot_name', 'rank', 'class', 'team', 'date',  # Changed match_date to date
                'combat_medal', 'capture_medal', 'logistics_medal', 'intelligence_medal',
                'outcome', 'map'
            ]
            
            # Keep only columns in our ordered list that exist in the database
            self.display_columns = [col for col in ordered_columns 
                                  if col in table_info['matches'] 
                                  and col not in excluded_columns]
            
            # Setup column headers with proper display names
            self.table.setColumnCount(len(self.display_columns))
            header_labels = []
            for col in self.display_columns:
                if col == 'name':
                    header_labels.append("Name")
                else:
                    header_labels.append(col.replace('_', ' ').title())
            self.table.setHorizontalHeaderLabels(header_labels)
        else:
            # Fallback to default columns if table info not available
            self.table.setColumnCount(7)
            self.table.setHorizontalHeaderLabels([
                "Name", "Score", "Kills", "Deaths", 
                "Assists", "Revives", "Captures"
            ])

        # Set column properties with stretch mode
        header = self.table.horizontalHeader()
        for i in range(self.table.columnCount()):
            header.setSectionResizeMode(i, QHeaderView.Stretch)

        # Set table properties
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.itemClicked.connect(self.on_item_clicked)
        self.table.cellDoubleClicked.connect(self.on_row_double_clicked)

        self.main_layout.addWidget(self.table)

    def resizeEvent(self, event):
        """Handle window resize events"""
        super().resizeEvent(event)
        # No need to update columns as they stretch automatically

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
        
        # Add player name setting action
        set_player_action = QAction("Set Player Name", self)
        set_player_action.triggered.connect(self.show_player_name_dialog)
        file_menu.addAction(set_player_action)

        # Add backup/restore menu
        backup_menu = menubar.addMenu("Backup")
        
        backup_action = QAction("Create Backup", self)
        backup_action.triggered.connect(self.create_backup)
        backup_menu.addAction(backup_action)
        
        restore_action = QAction("Restore Backup", self)
        restore_action.triggered.connect(self.restore_from_backup)
        backup_menu.addAction(restore_action)
        
        # Add Help menu with update options
        help_menu = menubar.addMenu("Help")
        
        check_updates_action = QAction("Check for Updates", self)
        check_updates_action.triggered.connect(lambda: self.check_for_updates(True))
        help_menu.addAction(check_updates_action)
        
        # Add about action
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about_dialog)
        help_menu.addAction(about_action)
        
        # Add update settings submenu
        update_settings_menu = help_menu.addMenu("Update Settings")
        
        self.auto_update_action = QAction("Check for Updates on Startup", self)
        self.auto_update_action.setCheckable(True)
        self.auto_update_action.setChecked(self.settings.value('check_updates_on_startup', True, type=bool))
        self.auto_update_action.triggered.connect(self.toggle_auto_updates)
        update_settings_menu.addAction(self.auto_update_action)
        
        # Add cache cleanup action
        clear_cache_action = QAction("Clear Update Cache", self)
        clear_cache_action.triggered.connect(self.clear_update_cache)
        update_settings_menu.addAction(clear_cache_action)

    def export_stats(self):
        file_name, _ = QFileDialog.getSaveFileName(
            self, "Export Stats", "", "CSV Files (*.csv)")
        if file_name:
            try:
                with open(file_name, 'w', newline='') as csvfile:
                    writer = csv.writer(csvfile)
                    # Write headers using actual column names
                    headers = []
                    for i in range(self.table.columnCount()):
                        header = self.table.horizontalHeaderItem(i).text()
                        headers.append(header)
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
        """Load and display data from database in the table view"""
        self.table.setSortingEnabled(False)
        self.save_column_widths()
        self.table.setRowCount(0)
        
        try:
            data = self._fetch_data_from_db()
            if data:
                self._populate_table(data)
            self._setup_column_display()
            self._setup_header_tooltips()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load data: {str(e)}")
            print(f"Database error: {str(e)}")
            return
            
        self.table.setSortingEnabled(True)
        self.table.horizontalHeader().setSortIndicator(1, Qt.DescendingOrder)

    def _fetch_data_from_db(self):
        """Fetch aggregated player data from database"""
        search_text = self.search_input.text().lower()
        
        try:
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM matches")
                if cursor.fetchone()[0] == 0:
                    return None

                query = self._build_query()
                cursor.execute(query, (f'%{search_text}%',))
                return cursor.fetchall()
        except Exception as e:
            print(f"Error fetching data: {e}")
            return None

    def _build_query(self):
        """Build the SQL query for fetching player statistics"""
        numeric_columns = {
            'score', 'kills', 'deaths', 'assists', 'revives', 'captures',
            'vehicle_damage', 'tactical_respawn'
        }
        
        select_parts = []
        for col in self.display_columns:
            if col == 'name':
                select_parts.append('"name"')
            elif col in numeric_columns:
                select_parts.append(self._build_numeric_column_query(col))
            else:
                select_parts.append(f'MAX("{col}") as {col}')
        
        return f"""
            SELECT {', '.join(select_parts)}
            FROM matches
            WHERE LOWER("name") LIKE ?
            GROUP BY "name"
            ORDER BY total_score DESC
        """

    def _build_numeric_column_query(self, column):
        """Build the SQL for a numeric column with proper casting and null handling"""
        return f"""
            CAST(SUM(CASE 
                WHEN "{column}" IS NOT NULL AND "{column}" != '' 
                THEN CAST("{column}" AS INTEGER) 
                ELSE 0 
            END) AS INTEGER) as total_{column}
        """.strip()

    def _populate_table(self, data):
        """Populate the table with the fetched data"""
        numeric_columns = {
            'score', 'kills', 'deaths', 'assists', 'revives', 'captures',
            'vehicle_damage', 'tactical_respawn'
        }
        
        # Define a more neutral highlight color (light blue-gray)
        highlight_color = QColor(220, 230, 240)  # Light blue-gray
        
        self.table.setRowCount(len(data))
        for row, row_data in enumerate(data):
            player_name = str(row_data[0])
            is_current_player = self.player_name and player_name.lower() == self.player_name.lower()
            
            for col, value in enumerate(row_data):
                if col == 0 or self.display_columns[col] not in numeric_columns:
                    item = QTableWidgetItem(str(value) if value is not None else "")
                else:
                    item = self._create_numeric_item(value)
                
                # Highlight current player's row with the neutral color
                if is_current_player:
                    item.setBackground(highlight_color)
                    
                self.table.setItem(row, col, item)

    def _create_numeric_item(self, value):
        """Create a properly formatted numeric table item"""
        try:
            num_value = int(value) if value is not None else 0
            item = NumericSortItem(num_value)
        except (ValueError, TypeError):
            item = QTableWidgetItem(str(value))
        item.setTextAlignment(Qt.AlignCenter)
        return item

    def _setup_column_display(self):
        """Setup column widths based on saved values or content"""
        if not self.column_widths:
            self.table.resizeColumnsToContents()
        else:
            self.restore_column_widths()

    def _setup_header_tooltips(self):
        """Setup tooltips for table headers"""
        numeric_columns = {
            'score', 'kills', 'deaths', 'assists', 'revives', 'captures',
            'vehicle_damage', 'tactical_respawn'
        }
        
        for col in range(self.table.columnCount()):
            header_item = self.table.horizontalHeaderItem(col)
            if header_item and col < len(self.display_columns):
                column_name = self.display_columns[col]
                tooltip = (f"Total {column_name.replace('_', ' ').title()} Across All Games"
                          if column_name in numeric_columns
                          else column_name.replace('_', ' ').title())
                header_item.setToolTip(tooltip)

    def on_search(self, text):
        """Handler for search input changes"""
        self.load_data_from_db()

    def import_csv(self):
        file_names, _ = QFileDialog.getOpenFileNames(self, "Import CSV Files", "", "CSV Files (*.csv)")
        
        if file_names:
            # Show the import progress dialog
            progress_dialog = ImportProgressDialog(self.db, file_names, self)
            result = progress_dialog.exec_()
            
            # Refresh the data view after import is complete
            if result == QDialog.Accepted and (progress_dialog.successful_imports > 0 or progress_dialog.skipped_files > 0):
                self.load_data_from_db()
                
                # Show a summary message in the status bar
                summary = f"Import complete: {progress_dialog.successful_imports} imported, "
                summary += f"{progress_dialog.skipped_files} skipped, {progress_dialog.failed_files} failed"
                self.statusBar().showMessage(summary, 5000)

    def view_snapshots(self):
        dialog = SnapshotViewerDialog(self)
        dialog.exec_()

    def eventFilter(self, source, event):
        # Remove delete key handling
        return super().eventFilter(source, event)

    def on_snapshot_deleted(self, snapshot_name):
        """Handle snapshot deletion updates"""
        self.load_data_from_db()  # Always refresh the main window when a snapshot is deleted

    def on_row_double_clicked(self, row, column):
        player_name = self.table.item(row, 0).text()
        dialog = PlayerDetailsDialog(self, player_name)
        dialog.exec_()

    def on_item_clicked(self, item):
        """Select the entire row when any cell is clicked"""
        self.table.selectRow(item.row())

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
        """Check for new CSV files in the import directory and handle their import."""
        try:
            if not self._ensure_import_directory():
                return

            new_files = self._find_new_files()
            if not new_files:
                return

            self._handle_file_import(new_files)

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Error checking for new files: {str(e)}")
            print(f"Error in check_for_new_files: {e}")

    def _ensure_import_directory(self):
        """Ensure import directory exists and create if necessary."""
        if not os.path.exists(IMPORT_DIR):
            try:
                os.makedirs(IMPORT_DIR, exist_ok=True)
                return False
            except Exception as e:
                print(f"Failed to create import directory: {e}")
                return False
        return True

    def _find_new_files(self):
        """Find and validate new CSV files that haven't been imported yet."""
        if not (csv_files := glob.glob(os.path.join(IMPORT_DIR, "*_processed.csv"))):
            return []
            
        return [file_path for file_path in csv_files 
                if self._is_valid_new_file(file_path)]

    def _is_valid_new_file(self, file_path):
        """Check if file is valid and contains new data."""
        try:
            with open(file_path, newline='') as csvfile:
                csvreader = csv.reader(csvfile)
                next(csvreader)  # Skip header
                rows = list(csvreader)
                if not rows:
                    return False
                
                is_duplicate, _ = self.db.check_duplicate_data(rows)
                return not is_duplicate
        except Exception as e:
            print(f"Error validating file {file_path}: {e}")
            return False

    def _handle_file_import(self, new_files):
        """Handle the import dialog and file processing."""
        dialog = ImportStartupDialog(
            [os.path.basename(f) for f in new_files],
            self
        )
        
        if dialog.exec_() == QDialog.Accepted:
            self._process_selected_files(dialog.get_selected_files(), new_files)

    def _process_selected_files(self, selected_filenames, new_files):
        """Process the selected files and import them into the database."""
        for filename in selected_filenames:
            file_path = os.path.join(IMPORT_DIR, filename)
            try:
                self._import_single_file(file_path)
            except Exception as e:
                QMessageBox.critical(self, "Error", 
                    f"Failed to import {filename}: {str(e)}")
        
        self.load_data_from_db()

    def _create_snapshot_name(self, row):
        """Create snapshot name using split date/time fields"""
        return f"{row[0]} - {row[1]} - {row[2]} {row[3]} - {row[4]}"  # outcome - map - date time - team

    def _import_single_file(self, file_path):
        """Import a single CSV file into the database."""
        with open(file_path, newline='') as csvfile:
            csvreader = csv.reader(csvfile)
            next(csvreader)  # Skip header
            rows = list(csvreader)
            
            if rows:
                first_row = rows[0]
                datetime_str = first_row[2]
                date_str, time_str = datetime_str.split(' ', 1) if ' ' in datetime_str else (datetime_str, '')
                snapshot_name = f"{first_row[0]} - {first_row[1]} - {date_str} {time_str} - {first_row[3]}"
                
                self.db.import_snapshot(snapshot_name, rows)
                self.statusBar().showMessage(f"Imported: {snapshot_name}", 3000)

    def check_new_files_on_startup(self):
        """Check for new files on application startup."""
        try:
            if not (new_files := self.import_manager.check_new_files()):
                return
                
            dialog = ImportStartupDialog([f[0] for f in new_files], self)
            if dialog.exec_() != QDialog.Accepted:
                return
                
            self._process_startup_files(dialog.get_selected_files(), new_files)
        except Exception as e:
            print(f"Error checking for new files: {e}")
            QMessageBox.warning(self, "File Check Error", 
                              f"Error checking for new files: {str(e)}")

    def _process_startup_files(self, selected_files, new_files):
        """Process files selected during startup."""
        if not selected_files:
            return
            
        files_to_import = []
        for filename in selected_files:
            if matching_file := next((f[1] for f in new_files if f[0] == filename), None):
                files_to_import.append(matching_file)
        
        if files_to_import:
            # Show import progress dialog for startup imports
            progress_dialog = ImportProgressDialog(self.db, files_to_import, self)
            result = progress_dialog.exec_()
            
            if result == QDialog.Accepted and progress_dialog.successful_imports > 0:
                self.load_data_from_db()
                summary = f"Import complete: {progress_dialog.successful_imports} imported, "
                summary += f"{progress_dialog.skipped_files} skipped, {progress_dialog.failed_files} failed"
                self.statusBar().showMessage(summary, 5000)

    def check_for_updates(self, manual_check=False, force_check=False):
        """Check for application updates from GitHub"""
        try:
            # Always force check for both manual checks and startup checks
            update_checker = UpdateChecker(APP_VERSION)
            print(f"Checking for updates (manual={manual_check}, force={force_check})...")
            is_update_available, latest_version, download_url, release_notes = update_checker.check_for_updates(
                force_check=True  # Always force check to avoid caching issues
            )
            
            # Extra safety check - if versions match exactly, never suggest an update
            if is_update_available and latest_version.strip() == APP_VERSION.strip():
                print("WARNING: Update checker incorrectly reported update needed.")
                print(f"Current: '{APP_VERSION}', Latest: '{latest_version}'")
                print("Forcing is_update_available to False")
                is_update_available = False
            
            if is_update_available:
                print(f"Update available: current={APP_VERSION}, latest={latest_version}")
                dialog = UpdateDialog(latest_version, APP_VERSION, download_url, release_notes, self)
                dialog.exec_()
                if dialog.should_disable_updates():
                    self.settings.setValue('check_updates_on_startup', False)
                    self.auto_update_action.setChecked(False)
            elif manual_check:  # Only show "no updates" message for manual checks
                QMessageBox.information(self, "No Updates", 
                    f"You're running the latest version ({APP_VERSION}).")
                
        except Exception as e:
            if manual_check:  # Only show error message for manual checks
                QMessageBox.warning(self, "Update Check Failed", 
                    f"Failed to check for updates: {str(e)}")
            print(f"Update check error: {str(e)}")

    def toggle_auto_updates(self, enabled):
        """Toggle automatic update checks"""
        self.settings.setValue('check_updates_on_startup', enabled)

    def clear_update_cache(self):
        """Clear cached update files."""
        cache_dir = os.path.join(ROOT_DIR, "cache")
        if os.path.exists(cache_dir):
            reply = QMessageBox.question(self, 'Clear Update Cache',
                'This will delete all cached updates. Continue?',
                QMessageBox.Yes | QMessageBox.No)
            
            if reply == QMessageBox.Yes:
                try:
                    for filename in os.listdir(cache_dir):
                        file_path = os.path.join(cache_dir, filename)
                        try:
                            if os.path.isfile(file_path):
                                os.unlink(file_path)
                            elif os.path.isdir(file_path):
                                shutil.rmtree(file_path)
                        except Exception as e:
                            print(f"Error deleting {file_path}: {e}")
                    QMessageBox.information(self, "Success", "Update cache cleared successfully.")
                except Exception as e:
                    QMessageBox.critical(self, "Error", f"Failed to clear cache: {str(e)}")
            else:
                QMessageBox.information(self, "Info", "No update cache found.")

    def show_about_dialog(self):
        """Show application about dialog"""
        QMessageBox.about(self, "About Delta Force Leaderboard",
            f"<h2>Delta Force Leaderboard</h2>"
            f"<p>Version: {APP_VERSION}</p>"
            f"<p>A tool for tracking player performance in Delta Force games.</p>")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
