from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import csv
import logging
from pathlib import Path

@dataclass
class Config:
    MAP_NAME_CORRECTIONS = {
        "Ihreshold-Attac: and Defend": "Threshold - Attack and Defend",
        "Shatted - Attack and Defend": "Shafted - Attack and Defend",
        "Threshold-Attack and Defend": "Threshold - Attack and Defend",
        "hatted - Attack and Defend": "Shafted - Attack and Defend",
        "Ascension-Attac: and Defend": "Ascension - Attack and Defend",
        "Cracked-Attac: and Defend": "Cracked - Attack and Defend",
        "Shafted-Attac: and Defend": "Shafted - Attack and Defend",
        "Trench ines - Attack and Defend": "Trench Lines - Attack and Defend",
        "Trench ines-Attack and Defend": "Trench Lines - Attack and Defend",
        "Cracked-Attack and Defend": "Cracked - Attack and Defend",
        "Shatted - Attack and Detend": "Shafted - Attack and Defend",
        "Knite Edge - Attack and Defend": "Knife Edge - Attack and Defend",
        "Threshold - Attack and Detend": "Threshold - Attack and Defend",
    }
    
    OUTCOME_CORRECTIONS = {
        "SULLESS": "SUCCESS",
        "FAILIRE": "FAILURE",
        "FAILUPE": "FAILURE",
        "SUCCFSS": "SUCCESS",
        "VILIORY": "VICTORY",
    }
    
    CLASS_MAP = {
        "+": "Support",
        "o": "Recon",
        "A": "Assault",
        "-": "Support",
        ".": "Engineer",
        " ": "Engineer",
        "9": "Recon",
    }
    
    MEDAL_TYPES = [
        "Combat Bronze Medal", "Combat Silver Medal", "Combat Gold Medal",
        "Capture Bronze Medal", "Capture Silver Medal", "Capture Gold Medal",
        "Logistics Bronze Medal", "Logistics Silver Medal", "Logistics Gold Medal",
        "Intelligence Bronze Medal", "Intelligence Silver Medal", "Intelligence Gold Medal"
    ]
    
    CSV_HEADERS = [
        "Outcome", "Map", "Data", "Team", "Rank", "Class", "Name", "Score",
        "Kills", "Deaths", "Assists", "Revives", "Vehicle Damage", "Captures",
        "Tactical Respawn", "Combat Medal", "Capture Medal", "Logistics Medal",
        "Intelligence Medal"
    ]
    
    TEAM_NAME_CORRECTIONS = {
        "GTI": "ATTACK",
        "HAAVK": "DEFENSE"
    }

@dataclass
class PlayerData:
    prefix: str
    player_class: str
    name: str
    stats: List[int]

class DataProcessor:
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)

    def read_file(self, filepath: str) -> Optional[List[str]]:
        try:
            with open(filepath, 'r') as file:
                return file.read().strip().split('\n')
        except FileNotFoundError:
            self.logger.error(f"File not found: {filepath}")
        except Exception as e:
            self.logger.error(f"Error reading file {filepath}: {e}")
        return None

    def process_scoreboard(self, lines: List[str]) -> List[PlayerData]:
        players = []
        i = 0
        while i < len(lines):
            line = lines[i].strip()
            if not line or not line[0].isdigit():
                i += 1
                continue

            parts = line.split()
            next_line = lines[i + 1].strip() if i + 1 < len(lines) else ""
            next_parts = next_line.split()

            try:
                # Process player from current line
                if next_line and next_parts and next_parts[0].replace(',', '').isdigit():
                    rank = parts[0]
                    name_parts = parts[1:]
                    
                    # Improved class and name parsing using CLASS_MAP
                    if name_parts and name_parts[0] in self.config.CLASS_MAP:
                        status = name_parts[0]
                        name = ' '.join(name_parts[1:])
                    else:
                        status = '.'  # Default to Engineer
                        name = ' '.join(name_parts)
                    
                    # Clean the name by removing any class markers and commas
                    name_cleaned = []
                    for part in name.split():
                        if part not in self.config.CLASS_MAP and not (part == '.' and len(part) == 1):
                            name_cleaned.append(part.replace(',', ''))  # Remove commas
                    name = ' '.join(name_cleaned)
                    
                    # Get stats from next line
                    stats = []
                    for part in next_parts[:8]:
                        try:
                            stats.append(int(part.replace(',', '')))
                        except ValueError:
                            continue
                    
                    if len(stats) == 8:
                        players.append(PlayerData(
                            prefix=rank,
                            player_class=self.config.CLASS_MAP[status],
                            name=name,
                            stats=stats
                        ))
                        
                        # Process second player if exists
                        if len(next_parts) > 8:
                            second_player = next_parts[8:]
                            if len(second_player) >= 2:
                                rank2 = second_player[0]
                                name_parts2 = second_player[1:]
                                
                                # Same improved class and name parsing for second player
                                if name_parts2 and name_parts2[0] in self.config.CLASS_MAP:
                                    status2 = name_parts2[0]
                                    name2 = ' '.join(name_parts2[1:])
                                else:
                                    status2 = '.'
                                    name2 = ' '.join(name_parts2)
                                
                                # Clean second player name and remove commas
                                name2_cleaned = []
                                for part in name2.split():
                                    if part not in self.config.CLASS_MAP and not (part == '.' and len(part) == 1):
                                        name2_cleaned.append(part.replace(',', ''))  # Remove commas
                                name2 = ' '.join(name2_cleaned)
                                
                                # Get second player stats from next line
                                if i + 2 < len(lines):
                                    stats2 = []
                                    for part in lines[i + 2].split()[:8]:
                                        try:
                                            stats2.append(int(part.replace(',', '')))
                                        except ValueError:
                                            continue
                                    
                                    if len(stats2) == 8:
                                        players.append(PlayerData(
                                            prefix=rank2,
                                            player_class=self.config.CLASS_MAP[status2],
                                            name=name2,
                                            stats=stats2
                                        ))
                        i += 2 if len(next_parts) > 8 else 1
                        continue

                # If that fails, try to process as single-line format
                if len(parts) >= 10:  # Minimum length for single line with stats
                    # Look for 8 consecutive numbers in the line
                    for j in range(2, len(parts)-7):
                        try:
                            # Try to parse 8 consecutive numbers
                            stats = [int(parts[k].replace(',', '')) for k in range(j, j+8)]
                            name = ' '.join(parts[2:j])  # Everything before stats is name
                            
                            players.append(PlayerData(
                                prefix=parts[0],
                                player_class=self.config.CLASS_MAP[parts[1] if parts[1] in '+-oA' else '.'],
                                name=name,
                                stats=stats
                            ))
                            break
                        except ValueError:
                            continue

            except Exception as e:
                self.logger.warning(f"Error processing line {i}: {e}")
            
            i += 1

        return players

class MedalProcessor:
    def __init__(self, config: Config):
        self.config = config

    def process_medals(self, filepath: str) -> Dict[str, int]:
        lines = DataProcessor(self.config).read_file(filepath)
        if not lines:
            return {}
        
        return {medal: sum(1 for line in lines if line.strip() == medal)
                for medal in self.config.MEDAL_TYPES}

    def get_highest_medal(self, medals: Dict[str, int], category: str) -> str:
        """Returns the specific medal for a category if present in the medals dictionary"""
        for level in ["Gold", "Silver", "Bronze"]:
            medal_name = f"{category} {level} Medal"
            if medal_name in medals and medals[medal_name] > 0:
                return level
        return "None"

class MatchProcessor:
    def __init__(self, input_dir: str):
        self.input_dir = Path(input_dir)
        self.config = Config()
        self.data_processor = DataProcessor(self.config)
        self.medal_processor = MedalProcessor(self.config)
        self.logger = logging.getLogger(__name__)

    def process_matches(self):
        scoreboard_files = self.input_dir.glob("scoreboard_*_ocr.txt")
        for scoreboard_file in scoreboard_files:
            self.process_single_match(scoreboard_file)

    def process_single_match(self, scoreboard_file: Path):
        timestamp = scoreboard_file.stem.split('scoreboard_')[1].split('_ocr')[0]
        general_info_file = self.input_dir / f"general_information_{timestamp}_ocr.txt"
        medals_file = self.input_dir / f"medals_{timestamp}.txt"
        team_file = self.input_dir / f"team_{timestamp}_ocr.txt"  # Add team file path
        output_file = self.input_dir / f"match_{timestamp}_processed.csv"

        if not general_info_file.exists():
            self.logger.warning(f"No general information file found for {scoreboard_file}")
            return

        # Read team name from team file
        team_name = "Unknown"
        if team_file.exists():
            team_lines = self.data_processor.read_file(str(team_file))
            if team_lines and team_lines[0].strip():
                team_name = team_lines[0].strip()

        scoreboard_data = self.data_processor.process_scoreboard(
            self.data_processor.read_file(str(scoreboard_file)) or []
        )
        outcome, map_name, date = self.process_general_info(
            self.data_processor.read_file(str(general_info_file)) or []
        )
        medals_data = self.medal_processor.process_medals(str(medals_file))

        self.write_csv(output_file, scoreboard_data, outcome, map_name, date, team_name, medals_data)

    def process_general_info(self, lines: List[str]) -> Tuple[str, str, str]:
        if len(lines) < 2:
            return ("Unknown", "Unknown", "Unknown")
        
        # Handle outcome
        outcome = lines[0].strip()
        outcome = self.config.OUTCOME_CORRECTIONS.get(outcome, outcome)
        if outcome == "SUCCESS":
            outcome = "VICTORY"
        outcome = outcome.replace("?", "").strip()
        
        # Handle map name and date
        map_name = "Unknown"
        date_str = "Unknown"
        
        # Skip any "?" lines and get remaining content
        valid_lines = [line.strip() for line in lines[1:] if line.strip() and line.strip() != "?"]
        
        if valid_lines:
            # First valid line after outcome is always map name
            map_line = valid_lines[0]
            
            # Check if map name contains a date
            words = map_line.split()
            for i, part in enumerate(words):
                # Look for month abbreviation with optional period
                if part.rstrip('.').lower() in ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 
                                              'jul', 'aug', 'sep', 'oct', 'nov', 'dec']:
                    try:
                        # Take everything before the date parts as map name
                        map_name = ' '.join(words[:i-1])  # -1 to exclude the day number
                        date_str = ' '.join(words[i-1:])  # Include from day number onwards
                        break
                    except:
                        continue
            
            if date_str == "Unknown":
                map_name = map_line
                # Try to get date from next line if exists
                if len(valid_lines) > 1:
                    date_str = valid_lines[1]
        
        map_name = self.config.MAP_NAME_CORRECTIONS.get(map_name, map_name)
        
        # Format date string
        try:
            if date_str and date_str != "Unknown":
                parts = date_str.split()
                if len(parts) >= 3:  # At least day, month, year
                    day = parts[0].zfill(2)
                    month = parts[1].rstrip('.')  # Remove potential period
                    year = parts[2]
                    time = parts[3] if len(parts) > 3 else "00:00:00"
                    if not self._is_valid_time(time):
                        time = "00:00:00"
                    date_str = f"{day} {month} {year} {time}"
        except Exception as e:
            self.logger.warning(f"Could not parse date: {date_str}")
            date_str = "Unknown"
            
        return outcome, map_name, date_str

    def _is_valid_time(self, time_str: str) -> bool:
        try:
            hours, minutes, seconds = map(int, time_str.split(':'))
            return 0 <= hours < 24 and 0 <= minutes < 60 and 0 <= seconds < 60
        except Exception:
            return False

    def write_csv(self, output_file: Path, players: List[PlayerData], 
                 outcome: str, map_name: str, date: str, team_name: str, medals: Dict[str, int]):
        # Apply team name correction
        team_name = self.config.TEAM_NAME_CORRECTIONS.get(team_name, team_name)
        
        rows = []
        for player in players:
            # Extract individual stats
            score, kills, deaths, assists, revives, vehicle_damage, captures, tactical = (
                player.stats[0],  # Score
                player.stats[1],  # Kills
                player.stats[2],  # Deaths
                player.stats[3],  # Assists
                player.stats[4],  # Revives
                player.stats[5],  # Vehicle Damage
                player.stats[6],  # Captures
                player.stats[7]   # Tactical Respawn
            ) if len(player.stats) >= 8 else (0, 0, 0, 0, 0, 0, 0, 0)
            
            row = [
                outcome, map_name, date, team_name,
                player.prefix, player.player_class, player.name, score,
                kills, deaths, assists, revives, vehicle_damage, captures,
                tactical
            ]
            
            # Add medal information
            for category in ["Combat", "Capture", "Logistics", "Intelligence"]:
                row.append(self.medal_processor.get_highest_medal(medals, category))
            
            rows.append(row)
        
        with open(output_file, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(self.config.CSV_HEADERS)
            writer.writerows(rows)
        
        self.logger.info(f"Created CSV file: {output_file}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    input_directory = Path(__file__).parent / 'workflow'
    processor = MatchProcessor(input_directory)
    processor.process_matches()
