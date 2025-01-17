import sqlite3
import pandas as pd
import os
from datetime import datetime
import shutil
import csv
from pathlib import Path
from typing import List
import time

class Database:
    def __init__(self):
        # Get the project root directory (3 levels up from src/data/database.py)
        self.base_path = Path(__file__).resolve().parent.parent.parent
        # Create data directory if it doesn't exist
        self.data_dir = self.base_path / 'data'
        self.data_dir.mkdir(exist_ok=True)
        
        # Set database path relative to data directory
        self.db_path = str(self.data_dir / 'leaderboard.db')
        print(f"Debug - Using database at: {self.db_path}")
        
        self.create_database()

    def get_connection(self):
        """Get a database connection"""
        return sqlite3.connect(self.db_path)

    def create_database(self):
        """Create database and required tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create matches table with all required fields
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_name TEXT,
                match_date TEXT,
                outcome TEXT,
                map TEXT,
                team TEXT,
                rank INTEGER,
                class TEXT,
                player_name TEXT,
                score INTEGER,
                kills INTEGER,
                deaths INTEGER,
                assists INTEGER,
                revives INTEGER,
                captures INTEGER,
                combat_medal TEXT,
                capture_medal TEXT,
                logistics_medal TEXT,
                intelligence_medal TEXT
            )
        ''')
        
        # Create index for commonly queried fields
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_player_name ON matches(player_name)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_match_date ON matches(match_date)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_snapshot ON matches(snapshot_name)')
        
        conn.commit()
        conn.close()

    def get_imported_match_identifiers(self) -> List[tuple]:
        """Get list of all unique match identifiers in database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT DISTINCT match_date, outcome, map, team 
                    FROM matches
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
        """Import CSV file into database"""
        if self.is_duplicate_file(file_path):
            return False
            
        try:
            # Read CSV file
            df = pd.read_csv(file_path)
            
            # Add snapshot_name column based on first row
            first_row = df.iloc[0]
            snapshot_name = f"{first_row['Outcome']} - {first_row['Map']} - {first_row['Data']} - {first_row['Team']}"
            df['snapshot_name'] = snapshot_name
            
            # Rename columns to match database schema
            column_mapping = {
                'Outcome': 'outcome',
                'Map': 'map',
                'Data': 'match_date',
                'Team': 'team',
                'Rank': 'rank',
                'Class': 'class',
                'Name': 'player_name',
                'Score': 'score',
                'Kills': 'kills',
                'Deaths': 'deaths',
                'Assists': 'assists',
                'Revives': 'revives',
                'Captures': 'captures',
                'Combat Medal': 'combat_medal',
                'Capture Medal': 'capture_medal',
                'Logistics Medal': 'logistics_medal',
                'Intelligence Medal': 'intelligence_medal'
            }
            
            df.rename(columns=column_mapping, inplace=True)
            
            # Import to database
            with sqlite3.connect(self.db_path) as conn:
                df.to_sql('matches', conn, if_exists='append', index=False)
            
            return True
            
        except Exception as e:
            print(f"Error importing CSV: {e}")
            return False

    def backup_database(self):
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_filename = f'leaderboard_{timestamp}.backup'
        backup_path = str(self.data_dir / backup_filename)
        shutil.copy2(self.db_path, backup_path)
        return backup_path

    def restore_backup(self, backup_path):
        if os.path.exists(backup_path):
            # Close any existing connections
            try:
                conn = sqlite3.connect(self.db_path)
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
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            if not rows:
                return False, None
                
            # Get metadata from first row
            first_row = rows[0]
            outcome, map_name, match_date, team = first_row[0:4]
            
            # First check: Look for matches with same metadata
            cursor.execute("""
                SELECT COUNT(DISTINCT player_name) as player_count,
                       SUM(score) as total_score,
                       SUM(kills) as total_kills,
                       SUM(deaths) as total_deaths,
                       GROUP_CONCAT(player_name) as players,
                       outcome || ' - ' || map || ' - ' || match_date || ' - ' || team as match_id
                FROM matches 
                WHERE outcome = ? AND map = ? AND match_date = ? AND team = ?
                GROUP BY outcome, map, match_date, team
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
        finally:
            if 'conn' in locals():
                conn.close()

    def get_table_info(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = cursor.fetchall()
        
        table_info = {}
        for table in tables:
            cursor.execute(f"PRAGMA table_info({table[0]})")
            columns = cursor.fetchall()
            table_info[table[0]] = [col[1] for col in columns]
        
        conn.close()
        return table_info

    def import_snapshot(self, snapshot_name, rows):
        """Import match data into database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            for row in rows:
                cursor.execute("""
                    INSERT INTO matches (
                        outcome, map, match_date, team, rank, class,
                        player_name, score, kills, deaths, assists,
                        revives, captures, combat_medal, capture_medal,
                        logistics_medal, intelligence_medal
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, row)
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error importing match data: {e}")
            if 'conn' in locals():
                conn.close()
            return False

    def _close_all_connections(self) -> bool:
        """Try to close all database connections"""
        try:
            # Create temporary connection to force other connections to close
            temp_conn = sqlite3.connect(self.db_path)
            cursor = temp_conn.cursor()
            
            # This will force other connections to close
            cursor.execute("PRAGMA wal_checkpoint(FULL)")
            cursor.execute("PRAGMA optimize")
            temp_conn.commit()
            
            # Close our temporary connection
            cursor.close()
            temp_conn.close()
            
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
            temp_conn = sqlite3.connect(self.db_path, timeout=20)
            temp_cursor = temp_conn.cursor()
            
            # Force close other connections
            temp_cursor.execute("PRAGMA optimize")
            temp_cursor.execute("PRAGMA wal_checkpoint(TRUNCATE)")
            temp_conn.commit()
            
            # Close our connection too
            temp_cursor.close()
            temp_conn.close()
            
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
            conn = None
            try:
                conn = sqlite3.connect(self.db_path, timeout=20)
                cursor = conn.cursor()
                
                # Drop all tables
                cursor.execute("DROP TABLE IF EXISTS matches")
                
                # Recreate tables
                self.create_database()
                
                return True
                
            except Exception as e:
                print(f"Error during purge: {e}")
                return False
                
            finally:
                if conn:
                    try:
                        conn.close()
                    except:
                        pass

        except Exception as e:
            print(f"Error during backup before purge: {e}")
            return False

if __name__ == "__main__":
    pass

__all__ = ['Database']
