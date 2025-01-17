from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import csv
import datetime
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
    }
    
    OUTCOME_CORRECTIONS = {
        "SULLESS": "SUCCESS",
        "FAILIRE": "FAILURE",
        "FAILUPE": "FAILURE",
        "SUCCFSS": "SUCCESS",
    }
    
    CLASS_MAP = {
        "+": "Support",
        "o": "Recon",
        "A": "Assault",
        ".": "Engineer"
    }
    
    MEDAL_TYPES = [
        "Combat Bronze Medal", "Combat Silver Medal", "Combat Gold Medal",
        "Capture Bronze Medal", "Capture Silver Medal", "Capture Gold Medal",
        "Logistics Bronze Medal", "Logistics Silver Medal", "Logistics Gold Medal",
        "Intelligence Bronze Medal", "Intelligence Silver Medal", "Intelligence Gold Medal"
    ]
    
    CSV_HEADERS = [
        "Outcome", "Map", "Data", "Team", "Rank", "Class", "Name", "Score", 
        "Kills", "Deaths", "Assists", "Revives", "Captures",
        "Combat Medal", "Capture Medal", "Logistics Medal", "Intelligence Medal"
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

    def process_player_line(self, line: str) -> Optional[PlayerData]:
        words = line.split()
        if not words or not any(char.isalpha() for char in line):
            return None

        prefix = words[0]
        if len(words) > 2 and words[1] in self.config.CLASS_MAP:
            player_class = self.config.CLASS_MAP[words[1]]
            name = " ".join(words[2:])
        else:
            player_class = "Engineer"
            name = " ".join(words[1:])

        name = name[2:] if name.startswith("- ") else name
        return PlayerData(prefix, player_class, name, [])

    def process_scoreboard(self, lines: List[str]) -> List[PlayerData]:
        players: List[PlayerData] = []
        current_player: Optional[PlayerData] = None

        for line in lines:
            if any(char.isalpha() for char in line):
                if current_player and len(current_player.stats) == 6:
                    players.append(current_player)
                current_player = self.process_player_line(line)
            elif current_player:
                numbers = [int(word) for word in line.split() if word.isdigit()]
                current_player.stats.extend(numbers)

        if current_player and len(current_player.stats) == 6:
            players.append(current_player)

        return players

class MedalProcessor:
    def __init__(self, config: Config):
        self.config = config

    def process_medals(self, filepath: str) -> Dict[str, int]:
        lines = DataProcessor(self.config).read_file(filepath)
        if not lines:
            return {}

        medals_dict = {}
        for line in lines:
            medal = line.strip()
            if medal in self.config.MEDAL_TYPES:
                medals_dict[medal] = medals_dict.get(medal, 0) + 1
        return medals_dict

    def get_highest_medal(self, medals: Dict[str, int], category: str) -> str:
        for level in ["Gold", "Silver", "Bronze"]:
            if f"{category} {level} Medal" in medals:
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
        if len(lines) < 3:
            return ("Unknown", "Unknown", "Unknown")
        
        outcome = lines[0].strip()
        outcome = self.config.OUTCOME_CORRECTIONS.get(outcome, outcome)
        if outcome == "SUCCESS":
            outcome = "VICTORY"
        
        if "?" not in lines[1]:
            map_name = lines[1].strip()
            date_parts = [line.strip() for line in lines[2:] if line.strip()]
        else:
            map_name = lines[2].strip()
            date_parts = [line.strip() for line in lines[3:] if line.strip()]
        
        map_name = self.config.MAP_NAME_CORRECTIONS.get(map_name, map_name)
        
        # Format date string
        date_str = " ".join(date_parts).replace(" - ", " ").replace("-", " ")
        try:
            parts = date_str.split()
            if len(parts) >= 2:
                day = parts[0].zfill(2)
                month = parts[1]
                year = parts[2] if len(parts) > 2 else str(datetime.datetime.now().year)
                time = parts[3] if len(parts) > 3 and self._is_valid_time(parts[3]) else "00:00:00"
                data = f"{day} {month} {year} {time}"
            else:
                data = date_str
        except Exception as e:
            self.logger.warning(f"Could not format date: {date_str}")
            data = date_str
        
        return outcome, map_name, data

    def _is_valid_time(self, time_str: str) -> bool:
        try:
            hours, minutes, seconds = map(int, time_str.split(':'))
            return 0 <= hours < 24 and 0 <= minutes < 60 and 0 <= seconds < 60
        except:
            return False

    def write_csv(self, output_file: Path, players: List[PlayerData], 
                 outcome: str, map_name: str, date: str, team_name: str, medals: Dict[str, int]):
        # Apply team name correction
        team_name = self.config.TEAM_NAME_CORRECTIONS.get(team_name, team_name)
        
        rows = []
        for player in players:
            row = [
                outcome, map_name, date, team_name,
                player.prefix, player.player_class, player.name,
                *player.stats
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
