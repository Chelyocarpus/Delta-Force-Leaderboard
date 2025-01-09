import os

# Base paths
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
RESOURCES_DIR = os.path.join(ROOT_DIR, 'resources')
DATA_DIR = os.path.join(ROOT_DIR, 'data')

# Import settings
IMPORT_DIR = os.path.join(ROOT_DIR, 'components', 'workflow')

# Database settings
DB_NAME = 'leaderboard.db'
DB_PATH = os.path.join(DATA_DIR, DB_NAME)

# Window dimensions
MAIN_WINDOW_SIZE = (1000, 600)
DETAILS_WINDOW_SIZE = (900, 500)
SNAPSHOT_WINDOW_SIZE = (1200, 600)

# Application settings
APP_NAME = 'DeltaForce'
APP_MODULE = 'Leaderboard'
APP_TITLE = 'Delta Force Leaderboard'

# Table column headers
MAIN_TABLE_COLUMNS = [
    "Name", "Score", "Kills", "Deaths", 
    "Assists", "Revives", "Captures"
]

SNAPSHOT_TABLE_COLUMNS = [
    "Outcome", "Map", "Date", "Team", "Rank", "Class", "Name",
    "Score", "Kills", "Deaths", "Assists", "Revives", "Captures",
    "Combat Medal", "Capture Medal", "Logistics Medal", "Intelligence Medal"
]

HISTORY_TABLE_COLUMNS = [
    "Date", "Snapshot", "Rank", "Class", "Score",
    "Kills", "Deaths", "Assists", "Revives", "Captures"
]

MEDAL_TABLE_COLUMNS = [
    "Date",
    "Match",
    "Medal Type",
    "Description",
    "Details"
]

# Medal settings
MEDAL_CATEGORIES = ["Combat", "Capture", "Logistics", "Intelligence"]
MEDAL_RANKS = ["Gold", "Silver", "Bronze"]  # Order by precedence
MEDAL_COLUMN_MAP = {
    'combat_medal': 13,
    'capture_medal': 14,
    'logistics_medal': 15,
    'intelligence_medal': 16
}
MEDAL_USERS = ["Adwdaa"]  # Only track medals for Adwdaa

# Player classes
PLAYER_CLASSES = ["Assault", "Engineer", "Support", "Recon"]

# SQL Queries
QUERY_FAVORITE_CLASS = """
    SELECT class, COUNT(*) as class_count
    FROM snapshots
    WHERE name = ?
    GROUP BY class
    ORDER BY class_count DESC
    LIMIT 1
"""

QUERY_VICTORY_STATS = """
    SELECT 
        SUM(CASE WHEN snapshot_name LIKE '%(VICTORY)%' THEN 1 ELSE 0 END) as victories,
        SUM(CASE WHEN snapshot_name LIKE '%(DEFEAT)%' THEN 1 ELSE 0 END) as defeats,
        ROUND(CAST(SUM(CASE WHEN snapshot_name LIKE '%(VICTORY)%' THEN 1 ELSE 0 END) AS FLOAT) * 100 /
            COUNT(*), 1) as win_rate
    FROM snapshots
    WHERE name = ?
"""

QUERY_PLAYER_STATS = """
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
"""
