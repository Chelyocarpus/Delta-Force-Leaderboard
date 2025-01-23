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
        "VILIORY": "VICTORY",
    }
    
    CLASS_MAP = {
        "+": "Support",
        "o": "Recon",
        "A": "Assault",
        "-": "Support",
        ".": "Engineer",
        " ": "Engineer"
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
        
        for i in range(0, len(lines), 3):
            if i + 2 >= len(lines):
                break
            
            # First player info
            p1_info = lines[i].split()
            if not p1_info:
                continue
                
            rank1 = p1_info[0]
            status1 = '.' if len(p1_info) < 3 or p1_info[1] not in '+-oA' else p1_info[1]
            name1 = p1_info[-1] if len(p1_info) < 3 else ' '.join(p1_info[2:])
            
            # Parse first player stats
            stats1 = []
            stats1_parts = lines[i+1].split()
            for part in stats1_parts[:8]:
                try:
                    stats1.append(int(part))
                except ValueError:
                    continue
            
            if stats1:  # Only add player if we have stats
                players.append(PlayerData(
                    prefix=rank1,
                    player_class=self.config.CLASS_MAP[status1],
                    name=name1,
                    stats=stats1
                ))
            
            # Second player info from same stats line
            stats2_parts = lines[i+1].split()[8:]
            if len(stats2_parts) >= 2:
                rank2 = stats2_parts[0]
                status2 = '.' if len(stats2_parts) <= 2 or stats2_parts[1] not in '+-oA' else stats2_parts[1]
                name2 = stats2_parts[2] if len(stats2_parts) > 2 else stats2_parts[1]
                
                # Parse second player stats
                stats2 = []
                for part in lines[i+2].split():
                    try:
                        stats2.append(int(part))
                    except ValueError:
                        continue
                
                if stats2:  # Only add player if we have stats
                    players.append(PlayerData(
                        prefix=rank2,
                        player_class=self.config.CLASS_MAP[status2],
                        name=name2,
                        stats=stats2
                    ))
        
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
        # Remove any "?" characters from outcome
        outcome = outcome.replace("?", "").strip()
        
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
