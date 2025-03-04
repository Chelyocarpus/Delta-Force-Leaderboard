import sqlite3
import pandas as pd
import os
from datetime import datetime
import shutil
import csv
from pathlib import Path
from typing import List
from contextlib import contextmanager
from queue import Queue
from threading import Lock, current_thread

# Constants
DB_FILENAME = 'leaderboard.db'
TABLE_NAME = 'matches'
BACKUP_PREFIX = 'leaderboard_'
BACKUP_SUFFIX = '.backup'

class ConnectionPool:
    def __init__(self, db_path, max_connections=5):
        self.db_path = db_path
        self.max_connections = max_connections
        self.connections = {}  # Dict to track thread-specific connections
        self.lock = Lock()
        
    def get_connection(self):
        """Get a connection specific to the current thread"""
        thread_id = current_thread().ident
        
        with self.lock:
            if thread_id not in self.connections:
                # Create a new connection for this thread
                conn = sqlite3.connect(self.db_path)
                conn.row_factory = sqlite3.Row
                self.connections[thread_id] = conn
                
            return self.connections[thread_id]
    
    @contextmanager
    def connection(self):
        """Context manager for thread-safe database access"""
        conn = self.get_connection()
        try:
            yield conn
        finally:
            # We don't close the connection as it's kept for the thread
            # Just commit any changes
            conn.commit()

    def close_all(self):
        """Close all connections in the pool"""
        with self.lock:
            for thread_id, conn in list(self.connections.items()):
                try:
                    conn.close()
                    del self.connections[thread_id]
                except sqlite3.Error:
                    pass

class Database:
    def __init__(self):
        # Get the project root directory (3 levels up from src/data/database.py)
        self.base_path = Path(__file__).resolve().parent.parent.parent
        # Create data directory if it doesn't exist
        self.data_dir = self.base_path / 'data'
        self.data_dir.mkdir(exist_ok=True)
        
        # Set database path relative to data directory
        self.db_path = str(self.data_dir / DB_FILENAME)
        print(f"Debug - Using database at: {self.db_path}")
        
        # Initialize connection pool
        self.pool = ConnectionPool(self.db_path)

        self.create_database()

    def get_connection(self):
        """Get a database connection from the pool"""
        return self.pool.connection()

    def create_database(self):
        """Create database with minimal required structure"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Create matches table with only essential fields
            cursor.execute(f'''
                CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    snapshot_name TEXT
                )
            ''')
            
            # Create basic indexes
            cursor.execute(f'CREATE INDEX IF NOT EXISTS idx_snapshot ON {TABLE_NAME}(snapshot_name)')

    def _ensure_columns_exist(self, headers):
        """Ensure all columns from CSV exist in database"""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get existing columns
            cursor.execute(f"PRAGMA table_info({TABLE_NAME})")
            existing_columns = {row[1].lower() for row in cursor.fetchall()}
            
            # Map CSV headers to SQL-friendly column names
            mapped_headers = {}
            for header in headers:
                # Convert header to lowercase and SQL-friendly format
                sql_name = header.lower().strip().replace(' ', '_')
                # Remove any special characters
                sql_name = ''.join(c for c in sql_name if c.isalnum() or c == '_')
                mapped_headers[header] = sql_name
                
                # Add column if it doesn't exist
                if sql_name not in existing_columns and sql_name != 'id':
                    try:
                        cursor.execute(f'ALTER TABLE {TABLE_NAME} ADD COLUMN "{sql_name}" TEXT')
                        print(f"Added new column: {sql_name}")
                    except sqlite3.OperationalError as e:
                        print(f"Column creation error: {e}")
            
            return mapped_headers

    def get_imported_match_identifiers(self) -> List[tuple]:
        """Get list of all unique match identifiers in database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    SELECT DISTINCT snapshot_name, 
                           GROUP_CONCAT(name) as players,
                           COUNT(*) as player_count,
                           SUM(CAST(score as INTEGER)) as total_score
                    FROM {TABLE_NAME}
                    GROUP BY snapshot_name
                """)
                return cursor.fetchall()
        except sqlite3.Error as e:
            print(f"Error getting imported matches: {e}")
            return []

    def is_duplicate_file(self, file_path: str) -> bool:
        """Check if file content has already been imported"""
        try:
            with open(file_path, 'r', newline='') as csvfile:
                csvreader = csv.reader(csvfile)
                headers = next(csvreader)  # Skip header
                rows = list(csvreader)
                
                if not rows:
                    return False

                # Calculate key metrics for comparison
                players = sorted([row[6] for row in rows if len(row) > 6])
                total_score = sum(int(row[7]) for row in rows if len(row) > 7 and row[7].isdigit())
                player_count = len(players)
                snapshot_name = self._create_snapshot_name(headers, rows[0])
                
                imported_matches = self.get_imported_match_identifiers()
                
                for match in imported_matches:
                    stored_snapshot, stored_players, stored_count, stored_score = match
                    stored_players = sorted(stored_players.split(','))
                    
                    # Consider it duplicate if:
                    # 1. Same snapshot name
                    # 2. Same number of players
                    # 3. Score difference is less than max of (5% of total score, 100 points)
                    # 4. At least 80% of player names match
                    if (stored_snapshot == snapshot_name and 
                        stored_count == player_count and
                        abs(stored_score - total_score) < max(total_score * 0.05, 100)):
                        
                        # Check player overlap
                        common_players = set(players) & set(stored_players)
                        if len(common_players) >= (player_count * 0.8):
                            return True
                            
                return False
                    
        except (IOError, csv.Error, IndexError, ValueError) as e:
            print(f"Error checking for duplicates: {e}")
            return False
    
    # Add a thread-safe import method for worker threads
    def import_csv_worker(self, file_path: str) -> bool:
        """Thread-safe import for worker threads"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        # We'll do the duplicate check inside the method rather than separately
        try:
            # Read and validate CSV
            with open(file_path, 'r', newline='') as csvfile:
                csvreader = csv.reader(csvfile)
                headers = next(csvreader)
                rows = list(csvreader)
                
                if not rows:
                    return False
                
                # Create unique ID for this match
                snapshot_name = self._create_snapshot_name(headers, rows[0])
                
                # Thread-safe connection
                with self.get_connection() as conn:
                    # Check for duplicate first
                    cursor = conn.cursor()
                    cursor.execute(f"SELECT COUNT(*) FROM {TABLE_NAME} WHERE snapshot_name = ?", (snapshot_name,))
                    if cursor.fetchone()[0] > 0:
                        return False  # Skip duplicate
                    
                    # Process columns 
                    header_mapping = self._ensure_columns_exist(headers)
                    
                    # Create records
                    records = self._prepare_records(rows, headers, header_mapping, snapshot_name)
                    
                    # Insert records
                    columns = list(records[0].keys())
                    placeholders = ','.join(['?' for _ in columns])
                    columns_str = ','.join([f'"{col}"' for col in columns])
                    
                    for record in records:
                        values = [record[col] for col in columns]
                        cursor.execute(f"INSERT INTO {TABLE_NAME} ({columns_str}) VALUES ({placeholders})", values)
                        
                    return True  # Success
            
        except (IOError, sqlite3.Error, csv.Error, KeyError, IndexError) as e:
            print(f"Error importing file {file_path}: {e}")
            raise

    def _read_csv_headers(self, file_path: str) -> tuple[list, csv.reader]:
        """Read CSV headers and return headers and reader object."""
        try:
            csvfile = open(file_path, 'r', newline='')
            reader = csv.reader(csvfile)
            headers = next(reader)
            if not headers:
                raise ValueError("No headers found in CSV file")
            return headers, reader
        except Exception as e:
            raise IOError(f"Failed to read CSV headers: {e}")

    def _process_csv_rows(self, reader: csv.reader, headers: list) -> list:
        """Process CSV rows and return list of data rows."""
        rows = list(reader)
        if not rows:
            raise ValueError("No data rows found in CSV file")
        return rows

    def _create_snapshot_name(self, headers: list, first_row: list) -> str:
        """Create snapshot name from first row data."""
        row_dict = {headers[i]: first_row[i] for i in range(len(headers))}
        return (f"{row_dict['Outcome']} - {row_dict['Map']} - "
                f"{row_dict['Data']} - {row_dict['Team']}")

    def _prepare_records(self, rows: list, headers: list, 
                        header_mapping: dict, snapshot_name: str) -> list:
        """Convert rows to database records."""
        records = []
        for row in rows:
            record = {'snapshot_name': snapshot_name}
            for j, value in enumerate(row):
                if j < len(headers):
                    column_name = header_mapping[headers[j]]
                    record[column_name] = value
            records.append(record)
        return records

    def _insert_records(self, records: list) -> None:
        """Insert records into database."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            columns = list(records[0].keys())
            placeholders = ','.join(['?' for _ in columns])
            columns_str = ','.join([f'"{col}"' for col in columns])
            
            for record in records:
                values = [record[col] for col in columns]
                cursor.execute(f"INSERT INTO {TABLE_NAME} ({columns_str}) VALUES ({placeholders})", values)

    def import_csv(self, file_path: str) -> bool:
        """Import CSV file into database with dynamic columns."""
        if not os.path.exists(file_path):
            print(f"File not found: {file_path}")
            raise FileNotFoundError(f"File not found: {file_path}")

        if self.is_duplicate_file(file_path):
            print(f"Skipping duplicate file: {file_path}")
            return False

        try:
            # Read and validate CSV
            headers, reader = self._read_csv_headers(file_path)
            print(f"Importing file: {file_path}")
            print(f"Found headers: {headers}")

            # Process rows
            rows = self._process_csv_rows(reader, headers)
            print(f"Found {len(rows)} data rows")

            # Create column mapping and ensure columns exist
            header_mapping = self._ensure_columns_exist(headers)

            # Create snapshot and prepare records
            snapshot_name = self._create_snapshot_name(headers, rows[0])
            records = self._prepare_records(rows, headers, header_mapping, snapshot_name)

            # Insert records into database
            self._insert_records(records)
            print(f"Successfully imported {len(records)} records")
            return True

        except (IOError, ValueError) as e:
            print(f"Import error: {e}")
            raise ValueError(f"Import error: {e}")
        except sqlite3.Error as e:
            print(f"Database error: {e}")
            raise sqlite3.Error(f"Database error: {e}")
        except Exception as e:
            print(f"Unexpected error during import: {e}")
            raise Exception(f"Unexpected error during import: {e}")
        finally:
            if 'reader' in locals() and hasattr(reader, 'close'):
                reader.close()

    def backup_database(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'{BACKUP_PREFIX}{timestamp}{BACKUP_SUFFIX}'
        backup_path = str(self.data_dir / backup_filename)
        shutil.copy2(self.db_path, backup_path)
        return backup_path

    def restore_backup(self, backup_path):
        """Restore database from backup file"""
        if os.path.exists(backup_path):
            shutil.copy2(backup_path, self.db_path)
            return True
        return False

    def check_duplicate_data(self, rows):
        """
        Sophisticated duplicate check that looks at:
        1. Match metadata (outcome, map, date, team)
        2. Player count and names
        3. Score totals and key statistics
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if not rows:
                    return False, None
                    
                # Get metadata from first row
                first_row = rows[0]
                outcome, map_name, match_date, team = first_row[:4]  # Simplified slice notation
                
                # First check: Look for matches with same metadata
                cursor.execute(f"""
                    SELECT COUNT(DISTINCT name) as player_count,
                           SUM(score) as total_score,
                           SUM(kills) as total_kills,
                           SUM(deaths) as total_deaths,
                           GROUP_CONCAT(name) as players,
                           outcome || ' - ' || map || ' - ' || data || ' - ' || team as match_id
                    FROM {TABLE_NAME} 
                    WHERE outcome = ? AND map = ? AND data = ? AND team = ?
                    GROUP BY outcome, map, data, team
                """, (outcome, map_name, match_date, team))
                
                existing_matches = cursor.fetchall()
                
                if not existing_matches:
                    return False, None
                    
                # Compare with current data
                new_player_count = len(rows)
                new_total_score = sum(int(row[7]) for row in rows)  # Score column
                new_total_kills = sum(int(row[8]) for row in rows)  # Kills column
                new_total_deaths = sum(int(row[9]) for row in rows)  # Deaths column
                new_players = sorted([row[6] for row in rows])  # Player names
                
                for match in existing_matches:
                    player_count, total_score, total_kills, total_deaths, players, match_id = match
                    existing_players = sorted(players.split(','))
                    
                    # Check if match statistics are similar enough
                    if (player_count == new_player_count and
                        abs(total_score - new_total_score) < 100 and  # Allow small variance
                        abs(total_kills - new_total_kills) < 10 and
                        abs(total_deaths - new_total_deaths) < 10 and
                        new_players == existing_players):
                        
                        return True, match_id
                
                return False, None
                
        except (sqlite3.Error, IndexError, ValueError) as e:
            print(f"Error checking duplicates: {e}")
            return False, None

    def get_table_info(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = cursor.fetchall()
            
            table_info = {}
            for table in tables:
                cursor.execute(f"PRAGMA table_info({table[0]})")
                columns = cursor.fetchall()
                table_info[table[0]] = [col[1] for col in columns]
            
            return table_info

    def import_snapshot(self, snapshot_name, rows):
        """Import match data into database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # Changed column names to match the schema, using 'data' instead of 'date'
                for row in rows:
                    cursor.execute(f"""
                        INSERT INTO {TABLE_NAME} (
                            outcome, map, data, team, rank, class,
                            name, score, kills, deaths, assists,
                            revives, captures, combat_medal, capture_medal,
                            logistics_medal, intelligence_medal
                        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                    """, row)
                
                return True
        except sqlite3.Error as e:
            print(f"Error importing match data: {e}")
            return False

    def purge_database(self) -> bool:
        """Delete all data from the database without deleting the file"""
        try:
            backup_path = self.backup_database()
            print(f"Created backup at: {backup_path}")
            
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
                self.create_database()
                return True

        except (sqlite3.Error, IOError) as e:
            print(f"Error during purge/backup: {e}")
            return False

    def __del__(self):
        """Cleanup when object is destroyed"""
        if hasattr(self, 'pool'):
            self.pool.close_all()

__all__ = ['Database']