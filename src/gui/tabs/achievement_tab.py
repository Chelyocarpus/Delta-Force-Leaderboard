from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                            QLabel, QProgressBar, QScrollArea, QSizePolicy)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QFont, QIcon
import sqlite3
import logging
import os

# Setup logging
logger = logging.getLogger(__name__)

# Achievement definitions
ACHIEVEMENTS = {
    "Combat": [
        {
            "id": "marksman",
            "name": "Marksman",
            "description": "Get kills in battle",
            "base_threshold": 1000,
            "growth_factor": 2.0,
            "max_level": 10,
            "query": """
                SELECT SUM(CAST(kills AS INTEGER)) FROM matches WHERE name = ?
            """,
            "icon": "medal_kills.png"
        },
        {
            "id": "headhunter",
            "name": "Headhunter",
            "description": "Get high K/D (>=2.0) ratio in matches",
            "base_threshold": 10,
            "growth_factor": 1.5,
            "max_level": 8,
            "query": """
                SELECT COUNT(*) FROM matches
                WHERE name = ?
                AND CAST(kills AS FLOAT) / CASE 
                    WHEN CAST(deaths AS INTEGER) = 0 THEN 1.0
                    ELSE CAST(deaths AS FLOAT)
                END >= 2.0
                AND CAST(kills AS INTEGER) > 0
            """,
            "icon": "medal_kd.png"
        },
        {
            "id": "vehicle_destroyer",
            "name": "Vehicle Destroyer",
            "description": "Accumulate vehicle damage",
            "base_threshold": 1000,
            "growth_factor": 2.5,
            "max_level": 10,
            "query": """
                SELECT SUM(CAST(vehicle_damage AS INTEGER)) FROM matches WHERE name = ?
            """,
            "icon": "medal_vehicle.png"
        }
    ],
    "Teamplay": [
        {
            "id": "team_player",
            "name": "Team Player",
            "description": "Get assists helping your teammates",
            "base_threshold": 1000,
            "growth_factor": 2.0,
            "max_level": 10,
            "query": """
                SELECT SUM(CAST(assists AS INTEGER)) FROM matches WHERE name = ?
            """,
            "icon": "medal_assists.png"
        },
        {
            "id": "guardian_angel",
            "name": "Guardian Angel",
            "description": "Revive fallen teammates",
            "base_threshold": 50,
            "growth_factor": 2.0,
            "max_level": 10,
            "query": """
                SELECT SUM(CAST(revives AS INTEGER)) FROM matches WHERE name = ?
            """,
            "icon": "medal_revives.png"
        },
        {
            "id": "reinforcement",
            "name": "Reinforcement",
            "description": "Provide tactical respawns for your team",
            "base_threshold": 100,
            "growth_factor": 2.0,
            "max_level": 10,
            "query": """
                SELECT SUM(CAST(tactical_respawn AS INTEGER)) FROM matches WHERE name = ?
            """,
            "icon": "medal_respawn.png"
        }
    ],
    "Objective": [
        {
            "id": "flag_bearer",
            "name": "Flag Bearer",
            "description": "Capture objectives",
            "base_threshold": 1000,
            "growth_factor": 2.0,
            "max_level": 10,
            "query": """
                SELECT SUM(CAST(captures AS INTEGER)) FROM matches WHERE name = ?
            """,
            "icon": "medal_captures.png"
        },
        {
            "id": "victory",
            "name": "Victory",
            "description": "Win matches",
            "base_threshold": 100,
            "growth_factor": 2.0,
            "max_level": 10,
            "query": """
                SELECT COUNT(*) FROM matches WHERE name = ? AND outcome LIKE '%VICTORY%'
            """,
            "icon": "medal_victory.png"
        },
        {
            "id": "top_rank",
            "name": "Top Rank",
            "description": "Finish matches in the top 3",
            "base_threshold": 5,
            "growth_factor": 2.0,
            "max_level": 10,
            "query": """
                SELECT COUNT(*) FROM matches WHERE name = ? AND CAST(rank AS INTEGER) <= 3
            """,
            "icon": "medal_top_rank.png"
        }
    ],
    "Specialist": [
        {
            "id": "assault_master",
            "name": "Assault Master",
            "description": "Play matches as Assault class",
            "base_threshold": 100,
            "growth_factor": 2.0,
            "max_level": 8,
            "query": """
                SELECT COUNT(*) FROM matches WHERE name = ? AND class = 'Assault'
            """,
            "icon": "medal_assault.png"
        },
        {
            "id": "engineer_master",
            "name": "Engineer Master",
            "description": "Play matches as Engineer class",
            "base_threshold": 100,
            "growth_factor": 2.0,
            "max_level": 8,
            "query": """
                SELECT COUNT(*) FROM matches WHERE name = ? AND class = 'Engineer'
            """,
            "icon": "medal_engineer.png"
        },
        {
            "id": "support_master",
            "name": "Support Master",
            "description": "Play matches as Support class",
            "base_threshold": 100,
            "growth_factor": 2.0,
            "max_level": 8,
            "query": """
                SELECT COUNT(*) FROM matches WHERE name = ? AND class = 'Support'
            """,
            "icon": "medal_support.png"
        },
        {
            "id": "recon_master",
            "name": "Recon Master",
            "description": "Play matches as Recon class",
            "base_threshold": 100,
            "growth_factor": 2.0,
            "max_level": 8,
            "query": """
                SELECT COUNT(*) FROM matches WHERE name = ? AND class = 'Recon'
            """,
            "icon": "medal_recon.png"
        }
    ],
    "Dedication": [
        {
            "id": "veteran",
            "name": "Veteran",
            "description": "Play many matches",
            "base_threshold": 50,
            "growth_factor": 2.0,
            "max_level": 10,
            "query": """
                SELECT COUNT(*) FROM matches WHERE name = ?
            """,
            "icon": "medal_games.png"
        },
        {
            "id": "commitment",
            "name": "Commitment",
            "description": "Score total points across all matches",
            "base_threshold": 1000000,
            "growth_factor": 2.0,
            "max_level": 10,
            "query": """
                SELECT SUM(CAST(score AS INTEGER)) FROM matches WHERE name = ?
            """,
            "icon": "medal_points.png"
        },
        {
            "id": "win_streak",
            "name": "Win Streak",
            "description": "Achieve streaks of 3+ consecutive victories",
            "base_threshold": 5,  # Changed to require 5 streaks for first level
            "growth_factor": 2.0,
            "max_level": 10,
            "query": """
                WITH RECURSIVE
                matches_with_streak AS (
                    SELECT 
                        outcome,
                        data,
                        ROW_NUMBER() OVER (ORDER BY data) as row_num,
                        CASE WHEN outcome LIKE '%VICTORY%' THEN 1 ELSE 0 END as is_victory
                    FROM matches 
                    WHERE name = ?
                ),
                streak_calc AS (
                    SELECT 
                        row_num,
                        is_victory,
                        CASE 
                            WHEN is_victory = 0 THEN 0
                            WHEN LAG(is_victory, 1, 0) OVER (ORDER BY row_num) = 0 THEN 1
                            ELSE NULL
                        END as streak_start
                    FROM matches_with_streak
                ),
                streak_groups AS (
                    SELECT 
                        row_num,
                        is_victory,
                        SUM(CASE WHEN streak_start IS NOT NULL THEN 1 ELSE 0 END) 
                            OVER (ORDER BY row_num) as streak_group
                    FROM streak_calc
                    WHERE is_victory = 1
                ),
                streak_lengths AS (
                    SELECT 
                        streak_group,
                        COUNT(*) as streak_length
                    FROM streak_groups
                    GROUP BY streak_group
                )
                SELECT 
                    COUNT(*) as streak_count
                FROM streak_lengths
                WHERE streak_length >= 3
            """,
            "icon": "medal_streak.png"
        }
    ],
    # New category for Map achievements
    "Map Mastery": [
        {
            "id": "map_diversification",
            "name": "Map Explorer",
            "description": "Play on different maps at least 5 times each",
            "base_threshold": 1,
            "growth_factor": 2,
            "max_level": 10,
            "query": """
                SELECT COUNT(*) FROM (
                    SELECT map
                    FROM matches 
                    WHERE name = ? AND map IS NOT NULL AND map != ''
                    GROUP BY map
                    HAVING COUNT(*) >= 5
                )
            """,
            "icon": "medal_maps.png"
        },
        {
            "id": "map_specialist",
            "name": "Map Specialist",
            "description": "Play many matches on a single map",
            "base_threshold": 10,
            "growth_factor": 2.0,
            "max_level": 10,
            "query": """
                SELECT MAX(map_count) FROM (
                    SELECT map, COUNT(*) as map_count 
                    FROM matches 
                    WHERE name = ? AND map IS NOT NULL AND map != ''
                    GROUP BY map
                )
            """,
            "icon": "medal_map_expert.png"
        },
        {
            "id": "conquest_master",
            "name": "Conquest Master",
            "description": "Win matches on different maps (at least 2 wins each)",
            "base_threshold": 2,
            "growth_factor": 1.5,
            "max_level": 5,
            "query": """
                SELECT COUNT(*) FROM (
                    SELECT map
                    FROM matches 
                    WHERE name = ? AND outcome LIKE '%VICTORY%' AND map IS NOT NULL AND map != ''
                    GROUP BY map
                    HAVING COUNT(*) >= 2
                )
            """,
            "icon": "medal_conquest.png"
        },
        {
            "id": "map_domination",
            "name": "Map Domination",
            "description": "Achieve high win rate on a specific map (min. 5 matches)",
            "base_threshold": 60,
            "growth_factor": 1.2,
            "max_level": 10,
            "query": """
                SELECT MAX(win_percentage) FROM (
                    SELECT 
                        map, 
                        COUNT(*) as total_matches,
                        ROUND(SUM(CASE WHEN outcome LIKE '%VICTORY%' THEN 1 ELSE 0 END) * 100.0 / COUNT(*)) as win_percentage
                    FROM matches 
                    WHERE name = ? AND map IS NOT NULL AND map != ''
                    GROUP BY map
                    HAVING COUNT(*) >= 5
                )
            """,
            "icon": "medal_domination.png"
        }
    ]
}

def check_achievement_progress(db_path, player_name, achievement):
    """Check the progress of an achievement for a player"""
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(achievement["query"], (player_name,))
            result = cursor.fetchone()

            return 0 if not result or result[0] is None else float(result[0])
    except Exception as e:
        logger.error(f"Error checking achievement {achievement['name']}: {str(e)}")
        return 0

def calculate_level_thresholds(achievement):
    """Calculate exponentially increasing thresholds for achievement levels"""
    base = achievement["base_threshold"]
    factor = achievement["growth_factor"]
    max_level = achievement["max_level"]

    return [
        int(base * (factor ** (level - 1)))
        for level in range(1, max_level + 1)
    ]

def get_achievement_level(value, achievement):
    """Determine the achievement level based on progress using exponential thresholds"""
    thresholds = calculate_level_thresholds(achievement)

    return next(
        (
            (i, threshold, thresholds)
            for i, threshold in enumerate(thresholds)
            if value < threshold
        ),
        (achievement["max_level"], thresholds[-1], thresholds),
    )

def create_achievement_widget(achievement, current_value):
    """Create a widget to display an achievement with exponential progression"""
    widget = QWidget()
    layout = QHBoxLayout()
    
    # Icon placeholder (will be replaced with actual icons)
    icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 
                           "resources", "icons", achievement.get("icon", "medal_default.png"))
    
    icon_label = QLabel()
    if os.path.exists(icon_path):
        pixmap = QPixmap(icon_path).scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        icon_label.setPixmap(pixmap)
    else:
        icon_label.setText("🏅")
        icon_label.setFont(QFont("Arial", 24))
    
    icon_label.setFixedSize(50, 50)
    layout.addWidget(icon_label)
    
    # Achievement info
    info_layout = QVBoxLayout()
    
    # Name and description with improved styling
    name_label = QLabel(f"<b>{achievement['name']}</b>")
    name_label.setStyleSheet("font-size: 14px;")
    desc_label = QLabel(achievement['description'])
    desc_label.setStyleSheet("color: #666;")
    desc_label.setWordWrap(True)
    
    info_layout.addWidget(name_label)
    info_layout.addWidget(desc_label)
    
    # Calculate level and thresholds
    level, current_level_threshold, all_thresholds = get_achievement_level(current_value, achievement)
    
    # Format numbers with thousand separators
    current_value_formatted = f"{int(current_value):,}"
    threshold_formatted = f"{current_level_threshold:,}"
    
    if level < achievement["max_level"]:
        if current_level_threshold > 0:
            progress = int(round((current_value / current_level_threshold) * 100))
            progress = max(0, min(100, progress))
        else:
            progress = 0
        
        # Create level indicator with stars - using a more readable gold color
        level_text = "★" * level + "☆" * (achievement["max_level"] - level)
        level_label = QLabel(f"Level {level} {level_text}")
        level_label.setStyleSheet(f"""
            color: {'#FFC125' if level > 0 else '#666'};  /* Brighter gold */
            font-size: 12px;
            margin-bottom: 2px;
        """)
        info_layout.addWidget(level_label)
        
        # Enhanced progress bar
        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setValue(progress)
        
        # Color-code progress bar based on completion
        if progress >= 66:
            style_color = "#4CAF50"  # Green
        elif progress >= 33:
            style_color = "#FFA726"  # Orange
        else:
            style_color = "#2196F3"  # Blue
            
        progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid #CCC;
                border-radius: 3px;
                text-align: center;
                height: 20px;
            }}
            QProgressBar::chunk {{
                background-color: {style_color};
                border-radius: 2px;
            }}
        """)
        
        # Show detailed progress information
        progress_text = f"{current_value_formatted}/{threshold_formatted}"
        progress_bar.setFormat(f"{progress_text} ({progress}%)")
        info_layout.addWidget(progress_bar)
        
        # Show next level info - fixed calculation
        if level < achievement["max_level"]:  # Changed condition to show for all non-max levels
            next_threshold = all_thresholds[level]
            remaining = int(next_threshold - current_value)  # Convert to integer
            next_level_label = QLabel(f"{remaining:,} points to next level")
            next_level_label.setStyleSheet("color: #666; font-size: 10px;")
            info_layout.addWidget(next_level_label)
    else:
        # Max level reached styling - adjusted gold color
        max_label = QLabel(f"ELITE ACHIEVED - Level {level}")
        max_label.setStyleSheet("""
            color: #FFC125;  /* Brighter gold */
            font-weight: bold;
            font-size: 14px;
            padding: 5px;
            background-color: #2C3E50;
            border-radius: 3px;
        """)
        info_layout.addWidget(max_label)
        
        total_label = QLabel(f"Total Score: {current_value_formatted}")
        total_label.setStyleSheet("color: #666; font-size: 12px;")
        info_layout.addWidget(total_label)
    
    layout.addLayout(info_layout)
    layout.setStretch(1, 1)  # Make info section expand
    widget.setLayout(layout)
    return widget

def setup_achievement_tab(dialog):
    """Setup the achievement tab with the given dialog"""
    tab = QWidget()
    layout = QVBoxLayout()
    
    # Create a scrollable area
    scroll_area = QScrollArea()
    scroll_area.setWidgetResizable(True)
    scroll_content = QWidget()
    scroll_layout = QVBoxLayout(scroll_content)
    
    db_path = dialog.parent.db.db_path
    player_name = dialog.player_name
    
    # Add achievements by category
    for category, achievements in ACHIEVEMENTS.items():
        group_box = QGroupBox(category)
        group_layout = QVBoxLayout()
        
        for achievement in achievements:
            current_value = check_achievement_progress(db_path, player_name, achievement)
            achievement_widget = create_achievement_widget(achievement, current_value)
            group_layout.addWidget(achievement_widget)
        
        group_box.setLayout(group_layout)
        scroll_layout.addWidget(group_box)
    
    # Add some vertical spacing at the bottom
    spacer = QWidget()
    spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    scroll_layout.addWidget(spacer)
    
    scroll_area.setWidget(scroll_content)
    layout.addWidget(scroll_area)
    
    tab.setLayout(layout)
    return tab