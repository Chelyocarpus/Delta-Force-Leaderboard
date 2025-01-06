import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget,
    QMenu, QAction, QMenuBar, QFileDialog, QMessageBox, QDialog, QComboBox, QPushButton,
    QHBoxLayout, QLabel, QHeaderView, QLineEdit, QGroupBox, QGridLayout, QTabWidget, QScrollArea
)
from PyQt5.QtCore import Qt, pyqtSignal, QSortFilterProxyModel, QSettings
from PyQt5.QtGui import QIcon
import csv, sqlite3, os
from datetime import datetime

class SnapshotViewerDialog(QDialog):
    snapshot_deleted = pyqtSignal(str)  # Signal for deletion notification
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Snapshot Viewer")
        self.setGeometry(200, 200, 800, 500)
        
        layout = QVBoxLayout()
        
        # Snapshot selector
        selector_layout = QHBoxLayout()
        self.snapshot_combo = QComboBox()
        self.refresh_snapshots()
        selector_layout.addWidget(QLabel("Select Snapshot:"))
        selector_layout.addWidget(self.snapshot_combo)
        layout.addLayout(selector_layout)
        
        # Table
        self.table = QTableWidget()
        self.table.setColumnCount(9)
        self.table.setHorizontalHeaderLabels([
            "Rank", "Class", "Name", "Score", "Kills", "Deaths", "Assists", "Revives", "Captures"
        ])
        layout.addWidget(self.table)
        
        # Add buttons layout
        buttons_layout = QHBoxLayout()
        
        load_btn = QPushButton("Load Snapshot")
        load_btn.clicked.connect(self.load_selected_snapshot)
        buttons_layout.addWidget(load_btn)
        
        delete_btn = QPushButton("Delete Snapshot")
        delete_btn.clicked.connect(self.delete_selected_snapshot)
        buttons_layout.addWidget(delete_btn)
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
        self.snapshot_deleted.connect(parent.on_snapshot_deleted)
    
    def refresh_snapshots(self):
        self.snapshot_combo.clear()
        with sqlite3.connect(self.parent.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT snapshot_name, timestamp 
                FROM snapshots 
                ORDER BY timestamp DESC
            """)
            snapshots = cursor.fetchall()
            for snapshot in snapshots:
                # Show both name and timestamp in combo box
                display_text = f"{snapshot[0]} ({snapshot[1]})"
                self.snapshot_combo.addItem(display_text, snapshot[0])  # Store original name as data
    
    def load_selected_snapshot(self):
        snapshot_name = self.snapshot_combo.currentData()  # Get original name from data
        if not snapshot_name:
            return
            
        with sqlite3.connect(self.parent.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM snapshots WHERE snapshot_name = ?", (snapshot_name,))
            data = cursor.fetchall()
            
            self.table.setRowCount(len(data))
            for row, rowData in enumerate(data):
                # Skip snapshot_name and timestamp columns (last 2 columns)
                for col, value in enumerate(rowData[:-2]):
                    item = QTableWidgetItem(str(value))
                    self.table.setItem(row, col, item)

    def delete_selected_snapshot(self):
        if self.snapshot_combo.currentIndex() < 0:
            return
            
        snapshot_name = self.snapshot_combo.currentData()
        reply = QMessageBox.question(self, 'Delete Snapshot',
                                   f'Are you sure you want to delete "{snapshot_name}"?',
                                   QMessageBox.Yes | QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            try:
                with sqlite3.connect(self.parent.db_path) as conn:
                    cursor = conn.cursor()
                    
                    # Get all names from this snapshot for cleanup
                    cursor.execute("""
                        SELECT name FROM snapshots 
                        WHERE snapshot_name = ?
                    """, (snapshot_name,))
                    names = [row[0] for row in cursor.fetchall()]
                    
                    # Delete from snapshots table
                    cursor.execute("DELETE FROM snapshots WHERE snapshot_name = ?", 
                                 (snapshot_name,))
                    
                    # Delete from players table if these names aren't in other snapshots
                    for name in names:
                        cursor.execute("""
                            DELETE FROM players 
                            WHERE name = ? 
                            AND NOT EXISTS (
                                SELECT 1 FROM snapshots 
                                WHERE name = ? 
                                AND snapshot_name != ?
                            )
                        """, (name, name, snapshot_name))
                    
                    conn.commit()
                
                self.refresh_snapshots()
                self.parent.load_data_from_db()  # Refresh main window immediately
                self.snapshot_deleted.emit(snapshot_name)  # Emit signal
                
                if self.snapshot_combo.count() > 0:
                    self.load_selected_snapshot()
                else:
                    self.table.setRowCount(0)
                
                QMessageBox.information(self, "Success", 
                    f"Snapshot '{snapshot_name}' deleted successfully")
                    
            except Exception as e:
                QMessageBox.critical(self, "Error", 
                    f"Failed to delete snapshot: {str(e)}")

class PlayerDetailsDialog(QDialog):
    def __init__(self, parent=None, player_name=None):
        super().__init__(parent)
        self.parent = parent
        self.player_name = player_name
        self.setWindowTitle(f"Player Details - {player_name}")
        self.settings = QSettings('DeltaForce', 'Leaderboard')
        
        # Restore window state or use default
        geometry = self.settings.value('player_details_geometry')
        if geometry:
            self.restoreGeometry(geometry)
        else:
            self.setGeometry(200, 200, 900, 500)
        
        # Create main layout and tab widget
        layout = QVBoxLayout()
        self.tabs = QTabWidget()
        
        # Create tabs
        self.overall_tab = QWidget()
        self.class_tab = QWidget()
        self.attacker_tab = QWidget()
        self.defender_tab = QWidget()
        self.map_tab = QWidget()
        
        # Add tabs to widget
        self.tabs.addTab(self.overall_tab, "Overall Statistics")
        self.tabs.addTab(self.class_tab, "Class Statistics") 
        self.tabs.addTab(self.attacker_tab, "Attacker")
        self.tabs.addTab(self.defender_tab, "Defender")
        self.tabs.addTab(self.map_tab, "Map Performance")
        
        # Setup individual tabs
        self.setup_overall_tab()
        self.setup_class_tab()
        self.setup_attacker_tab()
        self.setup_defender_tab()
        self.setup_map_tab()
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def setup_overall_tab(self):
        layout = QVBoxLayout()
        # Move existing overall statistics code here
        summary_group = QGroupBox("Overall Statistics")
        summary_layout = QGridLayout()
        
        with sqlite3.connect(self.parent.db_path) as conn:
            cursor = conn.cursor()
            # Add favorite class query
            cursor.execute("""
                SELECT class, COUNT(*) as class_count
                FROM snapshots
                WHERE name = ?
                GROUP BY class
                ORDER BY class_count DESC
                LIMIT 1
            """, (self.player_name,))
            favorite_class = cursor.fetchone()
            
            # Updated stats query to round all values to integers
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT snapshot_name) as num_games,
                    SUM(score) as total_score,
                    ROUND(AVG(score)) as avg_score,
                    MAX(score) as best_score,
                    SUM(kills) as total_kills,
                    ROUND(AVG(kills)) as avg_kills,
                    SUM(deaths) as total_deaths,
                    ROUND(AVG(deaths)) as avg_deaths,
                    ROUND(CAST(SUM(kills) AS FLOAT) / 
                          CASE WHEN SUM(deaths) = 0 THEN 1 
                          ELSE SUM(deaths) END, 2) as kd_ratio,
                    SUM(assists) as total_assists,
                    ROUND(AVG(assists)) as avg_assists,
                    SUM(revives) as total_revives,
                    ROUND(AVG(revives)) as avg_revives,
                    SUM(captures) as total_captures,
                    ROUND(AVG(captures)) as avg_captures,
                    ROUND(AVG(rank)) as avg_rank
                FROM snapshots
                WHERE name = ?
            """, (self.player_name,))
            stats = cursor.fetchone()
            
            # Reorganize labels into logical groups
            stat_groups = {
                "General": [
                    ("Games Played:", stats[0]),
                    ("Average Rank:", stats[15]),
                    ("Favorite Class:", f"{favorite_class[0]} ({favorite_class[1]} times)")
                ],
                "Score": [
                    ("Total Score:", stats[1]),
                    ("Average Score:", stats[2]),
                    ("Best Score:", stats[3])
                ],
                "Combat": [
                    ("Total Kills:", stats[4]),
                    ("Average Kills:", stats[5]),
                    ("Total Deaths:", stats[6]),
                    ("Average Deaths:", stats[7]),
                    ("K/D Ratio:", stats[8])
                ],
                "Support": [
                    ("Total Assists:", stats[9]),
                    ("Average Assists:", stats[10]),
                    ("Total Revives:", stats[11]),
                    ("Average Revives:", stats[12])
                ],
                "Objectives": [
                    ("Total Captures:", stats[13]),
                    ("Average Captures:", stats[14])
                ]
            }
            
            # Create group boxes for each category
            row = 0
            for group_name, group_stats in stat_groups.items():
                group_box = QGroupBox(group_name)
                group_layout = QGridLayout()
                
                for i, (label, value) in enumerate(group_stats):
                    group_layout.addWidget(QLabel(label), i, 0)
                    if "K/D Ratio" in label:
                        formatted_value = f"{value:.2f}"
                    else:
                        formatted_value = str(int(value)) if isinstance(value, (int, float)) else str(value)
                    group_layout.addWidget(QLabel(formatted_value), i, 1)
                
                group_box.setLayout(group_layout)
                summary_layout.addWidget(group_box, row // 2, row % 2)
                row += 1

        summary_group.setLayout(summary_layout)
        layout.addWidget(summary_group)
        
        # Add history table
        history_group = QGroupBox("Match History")
        history_layout = QVBoxLayout()
        
        self.history_table = QTableWidget()
        self.history_table.setColumnCount(10)
        self.history_table.setHorizontalHeaderLabels([
            "Date", "Snapshot", "Rank", "Class", "Score", "Kills", 
            "Deaths", "Assists", "Revives", "Captures"
        ])
        
        # Load match history
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
        """, (self.player_name,))
        
        history = cursor.fetchall()
        self.history_table.setRowCount(len(history))
        
        for row, data in enumerate(history):
            for col, value in enumerate(data):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignCenter)
                self.history_table.setItem(row, col, item)
        
        self.history_table.resizeColumnsToContents()
        history_layout.addWidget(self.history_table)
        history_group.setLayout(history_layout)
        layout.addWidget(history_group)
        
        self.overall_tab.setLayout(layout)

    def setup_class_tab(self):
        layout = QVBoxLayout()
        
        # Define all available classes
        all_classes = ["Assault", "Engineer", "Support", "Recon"]
        
        with sqlite3.connect(self.parent.db_path) as conn:
            cursor = conn.cursor()
            
            for class_name in all_classes:
                # Get stats for this class
                cursor.execute("""
                    SELECT 
                        COUNT(*) as games,
                        ROUND(AVG(score)) as avg_score,
                        MAX(score) as best_score,
                        SUM(kills) as total_kills,
                        ROUND(AVG(kills), 1) as avg_kills,
                        SUM(deaths) as total_deaths,
                        ROUND(AVG(deaths), 1) as avg_deaths,
                        ROUND(CAST(SUM(kills) AS FLOAT) / 
                              CASE WHEN SUM(deaths) = 0 THEN 1 
                              ELSE SUM(deaths) END, 2) as kd_ratio,
                        SUM(assists) as total_assists,
                        ROUND(AVG(assists), 1) as avg_assists,
                        SUM(revives) as total_revives,
                        ROUND(AVG(revives), 1) as avg_revives,
                        SUM(captures) as total_captures,
                        ROUND(AVG(captures), 1) as avg_captures,
                        ROUND(AVG(rank)) as avg_rank
                    FROM snapshots
                    WHERE name = ? AND class = ?
                """, (self.player_name, class_name))
                stats = cursor.fetchone()
                
                # Create group box for this class
                class_group = QGroupBox(f"{class_name} Statistics")
                class_layout = QGridLayout()
                
                if stats[0] > 0:  # If player has played this class
                    # Organize stats into categories
                    stat_data = [
                        ("Games Played:", stats[0]),
                        ("Average Rank:", stats[14]),
                        ("Average Score:", stats[1]),
                        ("Best Score:", stats[2]),
                        ("K/D Ratio:", stats[7]),
                        ("Total Kills:", stats[3]),
                        ("Avg Kills:", stats[4]),
                        ("Total Deaths:", stats[5]),
                        ("Avg Deaths:", stats[6]),
                        ("Total Assists:", stats[8]),
                        ("Avg Assists:", stats[9]),
                        ("Total Revives:", stats[10]),
                        ("Avg Revives:", stats[11]),
                        ("Total Captures:", stats[12]),
                        ("Avg Captures:", stats[13])
                    ]
                    
                    # Add stats to layout in two columns
                    for i, (label, value) in enumerate(stat_data):
                        row = i % 8
                        col = i // 8 * 2
                        
                        class_layout.addWidget(QLabel(label), row, col)
                        if isinstance(value, float):
                            formatted_value = f"{value:.2f}" if "Ratio" in label else f"{value:.1f}"
                        else:
                            formatted_value = str(value)
                        class_layout.addWidget(QLabel(formatted_value), row, col + 1)
                else:
                    # Show "No data available" for unplayed classes
                    class_layout.addWidget(QLabel("No games played with this class"), 0, 0)
                
                class_group.setLayout(class_layout)
                layout.addWidget(class_group)
        
        # Add scroll area if many classes
        scroll = QScrollArea()
        scroll.setWidget(QWidget())
        scroll.widget().setLayout(layout)
        scroll.setWidgetResizable(True)
        
        # Main layout for tab
        main_layout = QVBoxLayout()
        main_layout.addWidget(scroll)
        self.class_tab.setLayout(main_layout)

    def setup_attacker_tab(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Coming Soon"))
        layout.addStretch()
        self.attacker_tab.setLayout(layout)

    def setup_defender_tab(self):
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Coming Soon"))
        layout.addStretch()
        self.defender_tab.setLayout(layout)

    def setup_map_tab(self):
        layout = QVBoxLayout()
        
        # Create table for map statistics
        map_table = QTableWidget()
        map_table.setColumnCount(8)
        map_table.setHorizontalHeaderLabels([
            "Map", "Games", "Avg Score", "Avg Kills", 
            "Avg Deaths", "K/D", "Avg Assists", "Avg Captures"
        ])
        
        with sqlite3.connect(self.parent.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 
                    snapshot_name,
                    COUNT(*) as games,
                    ROUND(AVG(score)) as avg_score,
                    ROUND(AVG(kills)) as avg_kills,
                    ROUND(AVG(deaths)) as avg_deaths,
                    ROUND(CAST(AVG(kills) AS FLOAT) / 
                          CASE WHEN AVG(deaths) = 0 THEN 1 
                          ELSE AVG(deaths) END, 2) as kd_ratio,
                    ROUND(AVG(assists)) as avg_assists,
                    ROUND(AVG(captures)) as avg_captures
                FROM snapshots
                WHERE name = ?
                GROUP BY snapshot_name
                ORDER BY avg_score DESC
            """, (self.player_name,))
            
            map_stats = cursor.fetchall()
            map_table.setRowCount(len(map_stats))
            
            for row, data in enumerate(map_stats):
                for col, value in enumerate(data):
                    item = QTableWidgetItem(str(value))
                    item.setTextAlignment(Qt.AlignCenter)
                    map_table.setItem(row, col, item)
        
        map_table.resizeColumnsToContents()
        layout.addWidget(map_table)
        self.map_tab.setLayout(layout)

    def closeEvent(self, event):
        # Save window geometry on close
        self.settings.setValue('player_details_geometry', self.saveGeometry())
        super().closeEvent(event)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Leaderboard")
        self.setGeometry(100, 100, 1000, 600)
        self.settings = QSettings('DeltaForce', 'Leaderboard')
        
        self.restore_window_state()

        # Set window icon
        icon_path = os.path.join(os.path.dirname(__file__), "favicon.png")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
            app_icon = QIcon(icon_path)
            QApplication.setWindowIcon(app_icon)

        # Initialize database
        self.init_database()
        
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
        
        import_action = QAction("Import CSV", self)
        import_action.triggered.connect(self.import_csv)
        file_menu.addAction(import_action)
        
        view_snapshots_action = QAction("View Snapshots", self)
        view_snapshots_action.triggered.connect(self.view_snapshots)
        file_menu.addAction(view_snapshots_action)

    def init_database(self):
        self.db_path = os.path.join(os.path.dirname(__file__), "leaderboard.db")
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('''CREATE TABLE IF NOT EXISTS players (
                rank INTEGER, class TEXT, name TEXT, score INTEGER,
                kills INTEGER, deaths INTEGER, assists INTEGER,
                revives INTEGER, captures INTEGER)''')
            
            cursor.execute('''CREATE TABLE IF NOT EXISTS snapshots (
                rank INTEGER, class TEXT, name TEXT, score INTEGER,
                kills INTEGER, deaths INTEGER, assists INTEGER,
                revives INTEGER, captures INTEGER,
                snapshot_name TEXT, timestamp DATETIME)''')
            conn.commit()

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
        file_names, _ = QFileDialog.getOpenFileNames(
            self, 
            "Import CSV Files", 
            "", 
            "CSV Files (*.csv)"
        )
        
        if file_names:
            imported_count = 0
            skipped_count = 0
            
            for file_name in file_names:
                try:
                    # First read the CSV data
                    csv_rows = []
                    with open(file_name, newline='') as csvfile:
                        csvreader = csv.reader(csvfile)
                        next(csvreader)  # Skip header row
                        csv_rows = list(csvreader)
                    
                    with sqlite3.connect(self.db_path) as conn:
                        cursor = conn.cursor()
                        
                        # Check for duplicate data
                        is_duplicate, existing_snapshot = self.check_duplicate_data(cursor, csv_rows)
                        
                        if is_duplicate:
                            skipped_count += 1
                            continue
                        
                        # If not duplicate, proceed with import
                        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
                        base_name = os.path.splitext(os.path.basename(file_name))[0]
                        snapshot_name = f"{base_name}_{timestamp}"
                        
                        for row in csv_rows:
                            cursor.execute(
                                'INSERT INTO snapshots VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                                row + [snapshot_name, timestamp]
                            )
                            cursor.execute("""
                                INSERT OR IGNORE INTO players 
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """, row)
                        
                        conn.commit()
                        self.current_snapshot = snapshot_name
                        imported_count += 1
                        
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

    def deleteSelectedRows(self):
        if not self.table.selectedItems():
            return
            
        reply = QMessageBox.question(self, 'Delete Rows',
                                   'Are you sure you want to delete selected rows?',
                                   QMessageBox.Yes | QMessageBox.No)
                                   
        if reply == QMessageBox.Yes:
            rows = set()
            for item in self.table.selectedItems():
                rows.add(item.row())
            
            try:
                with sqlite3.connect(self.db_path) as conn:
                    cursor = conn.cursor()
                    for row in sorted(rows, reverse=True):
                        name = self.table.item(row, 0).text()  # Name is now in column 0
                        
                        # Delete from snapshots first
                        cursor.execute("""
                            DELETE FROM snapshots 
                            WHERE name = ?
                        """, (name,))
                        
                        # Then delete from players
                        cursor.execute("""
                            DELETE FROM players 
                            WHERE name = ?
                        """, (name,))
                        
                        self.table.removeRow(row)
                    conn.commit()
                    
                # Refresh the view to ensure consistency
                self.load_data_from_db()
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to delete rows: {str(e)}")
                self.load_data_from_db()  # Refresh in case of partial deletion

    def eventFilter(self, source, event):
        if (source is self.table and event.type() == event.KeyPress 
            and event.key() == Qt.Key_Delete):
            self.deleteSelectedRows()
            return True
        return super().eventFilter(source, event)

    def tableContextMenuEvent(self, event):
        context_menu = QMenu(self)
        
        delete_action = QAction("Delete", self)
        delete_action.triggered.connect(self.deleteSelectedRows)
        context_menu.addAction(delete_action)
        
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
        player_name = self.table.item(row, 0).text()  # Name is in first column
        dialog = PlayerDetailsDialog(self, player_name)
        dialog.exec_()

class NumericSortItem(QTableWidgetItem):
    def __init__(self, value):
        super().__init__(str(value))
        self._value = float(value)

    def __lt__(self, other):
        return self._value < other._value

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
