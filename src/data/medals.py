from ..utils.constants import (
    MEDAL_CATEGORIES, MEDAL_RANKS,
    USER
)

class MedalProcessor:
    def __init__(self, db):
        self.db = db
        self.categories = MEDAL_CATEGORIES
        self.ranks = MEDAL_RANKS
        self.medal_column_map = {
            'combat_medal': 'Combat',
            'capture_medal': 'Capture',
            'logistics_medal': 'Logistics',
            'intelligence_medal': 'Intelligence'
        }

    def process_row_medals(self, row, snapshot_name, timestamp):
        """Process medals from a single row of CSV data"""
        if len(row) < 17:  # Make sure we have medal columns
            return None
            
        name = row[6]  # Name column
        if name not in USER:  # Only process medals for Adwdaa
            return None
            
        medals = []
        
        # Process each medal type
        medal_data = {
            'Combat': row[13],
            'Capture': row[14],
            'Logistics': row[15],
            'Intelligence': row[16]
        }
        
        for category, rank in medal_data.items():
            if rank and rank.lower() != 'none':
                medals.append({
                    'name': name,
                    'category': category,
                    'rank': rank,
                    'snapshot_name': snapshot_name,
                    'timestamp': timestamp
                })
        
        return medals if medals else None

    def process_batch_medals(self, rows, snapshot_name, timestamp):
        """Process multiple rows of medals efficiently"""
        if not rows:
            return []
            
        medals = []
        for row in rows:
            if row[5] not in USER:
                continue
                
            # Use list comprehension for better performance
            row_medals = [(row[5], category, row[col], snapshot_name, timestamp)
                         for col, category in self.medal_column_map.items()
                         if row[col] != 'None']
            medals.extend(row_medals)
            
        return medals

    def get_player_medal_stats(self, player_name, db_conn):
        """Get comprehensive medal statistics for a player"""
        if player_name not in USER:  # Only return stats for Adwdaa
            return None
            
        cursor = db_conn.cursor()
        
        # Get medal counts by type and rank
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT snapshot_name) as total_games,
                SUM(CASE WHEN combat_medal IS NOT NULL THEN 1 ELSE 0 END) as combat_medals,
                SUM(CASE WHEN capture_medal IS NOT NULL THEN 1 ELSE 0 END) as capture_medals,
                SUM(CASE WHEN logistics_medal IS NOT NULL THEN 1 ELSE 0 END) as logistics_medals,
                SUM(CASE WHEN intelligence_medal IS NOT NULL THEN 1 ELSE 0 END) as intel_medals,
                SUM(CASE WHEN combat_medal = 'Gold' THEN 1 ELSE 0 END) as combat_gold,
                SUM(CASE WHEN combat_medal = 'Silver' THEN 1 ELSE 0 END) as combat_silver,
                SUM(CASE WHEN combat_medal = 'Bronze' THEN 1 ELSE 0 END) as combat_bronze,
                SUM(CASE WHEN capture_medal = 'Gold' THEN 1 ELSE 0 END) as capture_gold,
                SUM(CASE WHEN capture_medal = 'Silver' THEN 1 ELSE 0 END) as capture_silver,
                SUM(CASE WHEN capture_medal = 'Bronze' THEN 1 ELSE 0 END) as capture_bronze,
                SUM(CASE WHEN logistics_medal = 'Gold' THEN 1 ELSE 0 END) as logistics_gold,
                SUM(CASE WHEN logistics_medal = 'Silver' THEN 1 ELSE 0 END) as logistics_silver,
                SUM(CASE WHEN logistics_medal = 'Bronze' THEN 1 ELSE 0 END) as logistics_bronze,
                SUM(CASE WHEN intelligence_medal = 'Gold' THEN 1 ELSE 0 END) as intel_gold,
                SUM(CASE WHEN intelligence_medal = 'Silver' THEN 1 ELSE 0 END) as intel_silver,
                SUM(CASE WHEN intelligence_medal = 'Bronze' THEN 1 ELSE 0 END) as intel_bronze
            FROM snapshots
            WHERE name = ?
        """, (player_name,))
        
        stats = cursor.fetchone()
        if not stats or stats[0] == 0:
            return None

        total_games = stats[0]
        games_with_medals = sum(1 for i in range(1, 5) if stats[i] > 0)
        
        medal_stats = {
            'total_games': total_games,
            'games_with_medals': games_with_medals,
            'medal_rate': (games_with_medals / total_games * 100) if total_games > 0 else 0,
            'category_games': {
                'Combat': stats[1],
                'Capture': stats[2],
                'Logistics': stats[3],
                'Intelligence': stats[4]
            },
            'detailed_stats': {
                'Combat': {
                    'Gold': [stats[5], stats[5]],
                    'Silver': [stats[6], stats[6]],
                    'Bronze': [stats[7], stats[7]]
                },
                'Capture': {
                    'Gold': [stats[8], stats[8]],
                    'Silver': [stats[9], stats[9]],
                    'Bronze': [stats[10], stats[10]]
                },
                'Logistics': {
                    'Gold': [stats[11], stats[11]],
                    'Silver': [stats[12], stats[12]],
                    'Bronze': [stats[13], stats[13]]
                },
                'Intelligence': {
                    'Gold': [stats[14], stats[14]],
                    'Silver': [stats[15], stats[15]],
                    'Bronze': [stats[16], stats[16]]
                }
            }
        }
        
        return medal_stats
