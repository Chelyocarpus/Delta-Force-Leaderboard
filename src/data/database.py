import sqlite3
import os
import shutil
import time
from queue import Queue
from threading import Lock
from ..utils.constants import DB_PATH

class Database:
    def __init__(self):
        self.db_path = DB_PATH
        self._connection_pool = Queue(maxsize=10)
        self._pool_lock = Lock()
        self._init_pool()
        self.init_database()
        self.optimize_database()
        
    def _init_pool(self):
        """Initialize connection pool"""
        for _ in range(10):
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Enable row factory for better performance
            self._connection_pool.put(conn)

    def get_connection(self):
        """Get a connection from the pool"""
        with self._pool_lock:
            return self._connection_pool.get()

    def return_connection(self, conn):
        """Return connection to the pool"""
        with self._pool_lock:
            self._connection_pool.put(conn)

    def execute_query(self, query, params=None):
        """Execute query using connection pool"""
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            return cursor.fetchall()
        finally:
            self.return_connection(conn)

    def init_database(self):
        """Initialize the database and create tables if they don't exist"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Create base tables
            cursor.execute('''CREATE TABLE IF NOT EXISTS snapshots (
                rank INTEGER, class TEXT, team TEXT, name TEXT, score INTEGER,
                kills INTEGER, deaths INTEGER, assists INTEGER,
                revives INTEGER, captures INTEGER,
                combat_medal TEXT, capture_medal TEXT,
                logistics_medal TEXT, intelligence_medal TEXT,
                snapshot_name TEXT, timestamp DATETIME,
                map TEXT)''')  # Added map column
            
            # Add medal columns if they don't exist
            cursor.execute("PRAGMA table_info(snapshots)")
            columns = [col[1] for col in cursor.fetchall()]
            
            medal_columns = {
                'combat_medal': 'TEXT',
                'capture_medal': 'TEXT',
                'logistics_medal': 'TEXT',
                'intelligence_medal': 'TEXT'
            }
            
            for col_name, col_type in medal_columns.items():
                if col_name not in columns:
                    cursor.execute(f"ALTER TABLE snapshots ADD COLUMN {col_name} {col_type}")
            
            # Add map column if it doesn't exist
            if 'map' not in columns:
                cursor.execute("ALTER TABLE snapshots ADD COLUMN map TEXT")
                # Migrate existing data
                cursor.execute("""
                    UPDATE snapshots 
                    SET map = TRIM(REPLACE(
                        substr(snapshot_name, 1, 
                            CASE 
                                WHEN instr(snapshot_name, ' - ') > 0 
                                THEN instr(snapshot_name, ' - ') - 1
                                ELSE length(snapshot_name)
                            END
                        ),
                        'ATTACK', ''
                    ))
                    WHERE map IS NULL
                """)
            
            # Rest of table creation
            cursor.execute('''CREATE TABLE IF NOT EXISTS players (
                rank INTEGER, class TEXT, team TEXT, name TEXT, score INTEGER,
                kills INTEGER, deaths INTEGER, assists INTEGER,
                revives INTEGER, captures INTEGER)''')
                
            cursor.execute('''CREATE TABLE IF NOT EXISTS medals (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                category TEXT,
                rank TEXT,
                snapshot_name TEXT,
                timestamp DATETIME,
                UNIQUE(name, category, snapshot_name))''')
                
            conn.commit()

    def optimize_database(self):
        """Optimize database performance"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute("PRAGMA temp_store=MEMORY")
            conn.execute("PRAGMA mmap_size=30000000000")
            conn.execute("VACUUM")

    def backup_database(self):
        """Create a timestamped backup of the database"""
        timestamp = time.strftime("%Y%m%d-%H%M%S")
        backup_path = f"{self.db_path}.{timestamp}.backup"
        with sqlite3.connect(self.db_path) as conn:
            backup = sqlite3.connect(backup_path)
            conn.backup(backup)
            backup.close()
        return backup_path

    def restore_backup(self, backup_path):
        """Restore database from backup"""
        if os.path.exists(backup_path):
            with sqlite3.connect(backup_path) as backup:
                with sqlite3.connect(self.db_path) as conn:
                    backup.backup(conn)
            return True
        return False

    def check_duplicate_data(self, rows):
        """Check if the data already exists in the database"""
        # Create normalized data hash for comparison
        data_hash = []
        for row in rows:
            # Extract key fields in same order as stored in database
            try:
                rank = int(row[4])
                class_name = row[5]
                team = row[3].upper() if row[3] else None
                name = row[6]
                score = int(row[7])
                kills = int(row[8])
                deaths = int(row[9])
                assists = int(row[10])
                revives = int(row[11])
                captures = int(row[12])
                
                # Create hash string with all fields
                hash_str = f"{rank}|{class_name}|{team}|{name}|{score}|{kills}|{deaths}|{assists}|{revives}|{captures}"
                data_hash.append(hash_str)
            except (IndexError, ValueError):
                continue
                
        data_hash = sorted(data_hash)  # Sort for consistent comparison

        # Compare with existing snapshots
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT snapshot_name FROM snapshots")
            snapshots = cursor.fetchall()
            
            for snapshot in snapshots:
                cursor.execute("""
                    SELECT rank, class, team, name, score, kills, deaths, assists, revives, captures 
                    FROM snapshots 
                    WHERE snapshot_name = ?
                    ORDER BY rank
                """, (snapshot[0],))
                existing_data = cursor.fetchall()
                
                # Create hash for existing data
                existing_hash = []
                for row in existing_data:
                    hash_str = '|'.join(str(x) if x is not None else '' for x in row)
                    existing_hash.append(hash_str)
                existing_hash = sorted(existing_hash)
                
                if data_hash == existing_hash:
                    return True, snapshot[0]
        
        return False, None

    def import_snapshot(self, snapshot_name, timestamp, rows, medals_data=None):
        """Import a new snapshot into the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Extract map name from snapshot_name
            map_name = snapshot_name.split(' - ')[0].replace('ATTACK', '').strip()
            
            for row in rows:
                try:
                    # Extract and normalize team value
                    team = row[3].upper() if row[3] else None  # Normalize to uppercase
                    if team not in ('ATTACK', 'DEFENSE'):
                        team = None
                    
                    # Rest of data extraction
                    rank = int(row[4])
                    class_name = row[5]
                    name = row[6]
                    score = int(row[7])
                    kills = int(row[8])
                    deaths = int(row[9])
                    assists = int(row[10])
                    revives = int(row[11])
                    captures = int(row[12])
                    
                    # Process medal data
                    combat_medal = row[13] if len(row) > 13 and row[13] != 'None' else None
                    capture_medal = row[14] if len(row) > 14 and row[14] != 'None' else None
                    logistics_medal = row[15] if len(row) > 15 and row[15] != 'None' else None
                    intelligence_medal = row[16] if len(row) > 16 and row[16] != 'None' else None

                    # Insert into snapshots with map name
                    cursor.execute('''
                        INSERT INTO snapshots (
                            rank, class, team, name, score, kills, deaths, assists, revives, captures,
                            combat_medal, capture_medal, logistics_medal, intelligence_medal,
                            snapshot_name, timestamp, map
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        rank, class_name, team, name, score, kills, deaths, assists, revives, captures,
                        combat_medal, capture_medal, logistics_medal, intelligence_medal,
                        snapshot_name, timestamp, map_name
                    ))

                    # Insert medals into medals table
                    medals = [
                        ('Combat', combat_medal),
                        ('Capture', capture_medal),
                        ('Logistics', logistics_medal),
                        ('Intelligence', intelligence_medal)
                    ]
                    
                    for category, medal_rank in medals:
                        if medal_rank and medal_rank != 'None':
                            cursor.execute("""
                                INSERT OR REPLACE INTO medals 
                                (name, category, rank, snapshot_name, timestamp)
                                VALUES (?, ?, ?, ?, ?)
                            """, (name, category, medal_rank, snapshot_name, timestamp))

                except (IndexError, ValueError) as e:
                    print(f"Error processing row for {name}: {e}")
                    continue

            conn.commit()
            self._update_players_table()

    def _update_players_table(self):
        """Update players table with latest data"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO players (
                    rank, class, team, name, score, 
                    kills, deaths, assists, revives, captures
                )
                SELECT 
                    MAX(rank),
                    class,
                    team,  -- Include team in aggregation
                    name,
                    SUM(score),
                    SUM(kills),
                    SUM(deaths),
                    SUM(assists),
                    SUM(revives),
                    SUM(captures)
                FROM snapshots
                GROUP BY name, team  -- Group by team as well
            """)
            conn.commit()

    def delete_player(self, name):
        """Delete a player and their data from the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM snapshots WHERE name = ?", (name,))
            cursor.execute("DELETE FROM players WHERE name = ?", (name,))
            cursor.execute("DELETE FROM medals WHERE name = ?", (name,))
            conn.commit()

    def delete_snapshot(self, snapshot_name):
        """Delete a snapshot and clean up orphaned player data"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Get all names from this snapshot for cleanup
            cursor.execute("SELECT name FROM snapshots WHERE snapshot_name = ?", (snapshot_name,))
            names = [row[0] for row in cursor.fetchall()]
            
            # Delete snapshot
            cursor.execute("DELETE FROM snapshots WHERE snapshot_name = ?", (snapshot_name,))
            cursor.execute("DELETE FROM medals WHERE snapshot_name = ?", (snapshot_name,))
            
            # Clean up orphaned players
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

    def purge_database(self):
        """Delete all data from the database"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM snapshots")
            cursor.execute("DELETE FROM players")
            cursor.execute("DELETE FROM medals")
            conn.commit()
