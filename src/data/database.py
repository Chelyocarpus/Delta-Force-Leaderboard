import sqlite3
import pandas as pd
import os
from datetime import datetime
import shutil
import csv
from pathlib import Path
from typing import List
import time
import json

# Constants
DB_FILENAME = 'leaderboard.db'
TABLE_NAME = 'matches'
BACKUP_PREFIX = 'leaderboard_'
BACKUP_SUFFIX = '.backup'

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
        
        self.create_database()

    def get_connection(self):
        """Get a database connection"""
        return sqlite3.connect(self.db_path)

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
            
            conn.commit()

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
            
            conn.commit()
            return mapped_headers

    def get_imported_match_identifiers(self) -> List[tuple]:
        """Get list of all unique match identifiers in database"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(f"""
                    SELECT DISTINCT data, outcome, map, team 
                    FROM {TABLE_NAME}
                """)
                return cursor.fetchall()
        except Exception as e:
            print(f"Error getting imported matches: {e}")
            return []

    def is_duplicate_file(self, file_path: str) -> bool:
        """Check if file content has already been imported"""
        try:
            with open(file_path, 'r', newline='') as csvfile:
                csvreader = csv.reader(csvfile)
                headers = next(csvreader)  # Skip header
                rows = list(csvreader)  # Get all rows
                
                if not rows:
                    return False
                    
                first_row = rows[0]
                imported_matches = self.get_imported_match_identifiers()
                
                # Check if this match's metadata matches any in database
                # Reorder to match_date, outcome, map, team
                match_data = (first_row[2], first_row[0], first_row[1], first_row[3])
                return match_data in imported_matches
                    
        except Exception as e:
            print(f"Error checking for duplicates: {e}")
            return False

    def import_csv(self, file_path):
        """Import CSV file into database with dynamic columns"""
        try:
            # First check for duplicates
            if self.is_duplicate_file(file_path):
                print(f"Skipping duplicate file: {file_path}")
                return False
            
            # Step 1: Read headers and create columns first
            try:
                with open(file_path, 'r', newline='') as csvfile:
                    reader = csv.reader(csvfile)
                    headers = next(reader)
                    if not headers:
                        raise ValueError("No headers found in CSV file")
                    
                    print(f"Importing file: {file_path}")
                    print(f"Found headers: {headers}")
                    
                    # Create column mapping before any data insertion
                    header_mapping = self._ensure_columns_exist(headers)
            except Exception as e:
                print(f"Error reading CSV headers: {str(e)}")
                return False
            
            # Step 2: Now read and insert the data
            try:
                with open(file_path, 'r', newline='') as csvfile:
                    reader = csv.reader(csvfile)
                    next(reader)  # Skip headers
                    rows = list(reader)
                    
                    if not rows:
                        print("No data rows found in CSV file")
                        return False
                    
                    print(f"Found {len(rows)} data rows")
                    
                    # Create snapshot name from first row
                    try:
                        first_row = {headers[i]: rows[0][i] for i in range(len(headers))}
                        snapshot_name = f"{first_row['Outcome']} - {first_row['Map']} - {first_row['Data']} - {first_row['Team']}"
                        print(f"Creating snapshot: {snapshot_name}")
                    except KeyError as e:
                        print(f"Missing required column in CSV: {str(e)}")
                        return False
                    except IndexError:
                        print("Invalid row format in CSV")
                        return False
                    
                    # Convert rows to dictionaries with mapped column names
                    records = []
                    for i, row in enumerate(rows, 1):
                        try:
                            record = {'snapshot_name': snapshot_name}
                            for j, value in enumerate(row):
                                if j < len(headers):
                                    column_name = header_mapping[headers[j]]
                                    record[column_name] = value
                            records.append(record)
                        except Exception as e:
                            print(f"Error processing row {i}: {str(e)}")
                            print(f"Row content: {row}")
                            continue
                    
                    if not records:
                        print("No valid records to import")
                        return False
                    
                    # Import to database
                    try:
                        with self.get_connection() as conn:
                            cursor = conn.cursor()
                            columns = list(records[0].keys())
                            placeholders = ','.join(['?' for _ in columns])
                            columns_str = ','.join([f'"{col}"' for col in columns])
                            
                            for i, record in enumerate(records, 1):
                                try:
                                    values = [record[col] for col in columns]
                                    query = f"INSERT INTO {TABLE_NAME} ({columns_str}) VALUES ({placeholders})"
                                    cursor.execute(query, values)
                                except sqlite3.Error as e:
                                    print(f"Database error on row {i}: {str(e)}")
                                    print(f"Failed record: {record}")
                                    continue
                            
                            conn.commit()
                            print(f"Successfully imported {len(records)} records")
                            return True
                            
                    except sqlite3.Error as e:
                        print(f"Database connection error: {str(e)}")
                        return False
                        
            except Exception as e:
                print(f"Error reading CSV data: {str(e)}")
                return False
                
        except Exception as e:
            print(f"General import error: {str(e)}")
            return False

    def backup_database(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'{BACKUP_PREFIX}{timestamp}{BACKUP_SUFFIX}'
        backup_path = str(self.data_dir / backup_filename)
        shutil.copy2(self.db_path, backup_path)
        return backup_path

    def restore_backup(self, backup_path):
        if os.path.exists(backup_path):
            # Close any existing connections
            try:
                conn = self.get_connection()
                conn.close()
            except:
                pass
            
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
                outcome, map_name, match_date, team = first_row[0:4]
                
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
                
        except Exception as e:
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
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error importing match data: {e}")
            return False

    def _close_all_connections(self) -> bool:
        """Try to close all database connections"""
        try:
            # Create temporary connection to force other connections to close
            with self.get_connection() as temp_conn:
                cursor = temp_conn.cursor()
                
                # This will force other connections to close
                cursor.execute("PRAGMA wal_checkpoint(FULL)")
                cursor.execute("PRAGMA optimize")
                temp_conn.commit()
                
                # Small delay to ensure connections are closed
                time.sleep(0.5)
                return True
        except Exception as e:
            print(f"Error closing connections: {e}")
            return False

    def _force_close_connections(self) -> None:
        """Close all database connections forcefully"""
        try:
            # Get a new connection and force close all others
            with self.get_connection() as temp_conn:
                temp_cursor = temp_conn.cursor()
                
                # Force close other connections
                temp_cursor.execute("PRAGMA optimize")
                temp_cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
                temp_conn.commit()
                
                # Windows needs extra time to release file handles
                time.sleep(1)
        except Exception as e:
            print(f"Error forcing connections closed: {e}")

    def purge_database(self) -> bool:
        """Delete all data from the database without deleting the file"""
        try:
            # Create backup first
            backup_path = self.backup_database()
            print(f"Created backup at: {backup_path}")
            
            # Instead of deleting file, drop and recreate tables
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    
                    # Drop all tables
                    cursor.execute(f"DROP TABLE IF EXISTS {TABLE_NAME}")
                    
                    # Recreate tables
                    self.create_database()
                    
                    return True
                    
            except Exception as e:
                print(f"Error during purge: {e}")
                return False

        except Exception as e:
            print(f"Error during backup before purge: {e}")
            return False

if __name__ == "__main__":
    pass

__all__ = ['Database']