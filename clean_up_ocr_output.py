import csv
import os
import glob
import datetime

# Add map name corrections dictionary
MAP_NAME_CORRECTIONS = {
    "Ihreshold-Attac: and Defend": "Threshold - Attack and Defend",
    # Add more corrections as needed:
    "Shatted - Attack and Defend": "Shattered - Attack and Defend",
    "Threshold-Attack and Defend": "Threshold - Attack and Defend",
    "hatted - Attack and Defend": "Shattered - Attack and Defend",
    "Ascension-Attac: and Defend": "Ascension - Attack and Defend",
}

# Add outcome corrections dictionary
OUTCOME_CORRECTIONS = {
    "SULLESS": "SUCCESS",
    "FAILIRE": "FAILURE",
    "FAILUPE": "FAILURE",
    "SUCCFSS": "SUCCESS",
    # Add more corrections as needed
}

def read_input_file(filepath):
    try:
        with open(filepath, 'r') as file:
            return file.read().strip().split('\n')
    except FileNotFoundError:
        print(f"Error: Input file '{filepath}' not found.")
        return None
    except Exception as e:
        print(f"Error reading input file: {str(e)}")
        return None

def process_lines(input_lines):
    # Add class mapping dictionary
    class_map = {
        "+": "Support",
        "o": "Recon",
        "A": "Assault",
        ".": "Engineer"
    }
    
    rows = []
    current_prefix = None
    current_class = None
    current_name = None
    current_numbers = []
    
    for line in input_lines:
        words = line.split()
        
        # Check if this line contains a word (not just numbers)
        if any(char.isalpha() for char in line):
            # If there is an existing name, save the current data
            if current_name:
                # Ensure there are exactly 6 numbers
                # TODO: Handle cases where there are less than 6 numbers due to bad OCR, maybe use a percentage threshold
                if len(current_numbers) == 6:
                    rows.append([current_prefix, current_class, current_name] + current_numbers)
            
            # Extract the rank (e.g., "1", "2", etc.)
            current_prefix = words[0]
            
            # If there is a class (i.e., "+" or "A" or "o"), it will be in the second word
            if len(words) > 2 and words[1] in class_map:
                current_class = class_map[words[1]]  # Convert symbol to class name
                current_name = " ".join(words[2:])  # Everything after the class is the name
            else:
                # Handle the case without a class (e.g., "30 SeniorMoo") due to bad OCR
                current_class = "Engineer"  # OCR failed to detect class, default to Engineer (OCR has problems with Engineer)
                current_name = " ".join(words[1:])  # The rest is the name
            
            # Clean up name by removing leading "- "
            if current_name.startswith("- "):
                current_name = current_name[2:]
            
            # Reset the numbers list
            current_numbers = []
        else:
            # Collect numbers (assumed to be scores, kills, etc.)
            current_numbers.extend([int(word) for word in words if word.isdigit()])
    
    # Append the last processed line
    if current_name and len(current_numbers) == 6:
        rows.append([current_prefix, current_class, current_name] + current_numbers)
    
    return rows

def is_valid_time(time_str):
    """Helper function to validate time format"""
    try:
        hours, minutes, seconds = map(int, time_str.split(':'))
        return 0 <= hours < 24 and 0 <= minutes < 60 and 0 <= seconds < 60
    except:
        return False

def process_general_info(input_lines):
    """
    Process the general information file to extract outcome, map name, and other data.
    """
    if len(input_lines) < 3:
        return ("Unknown", "Unknown", "Unknown")
    
    outcome = input_lines[0].strip()
    outcome = OUTCOME_CORRECTIONS.get(outcome, outcome)
    if outcome == "SUCCESS":
        outcome = "VICTORY"
    
    # Check if second line contains "?", if not use it as map name
    if "?" not in input_lines[1]:
        map_name = input_lines[1].strip()
        date_parts = [line.strip() for line in input_lines[2:] if line.strip()]
    else:
        map_name = input_lines[2].strip()
        date_parts = [line.strip() for line in input_lines[3:] if line.strip()]
    
    map_name = MAP_NAME_CORRECTIONS.get(map_name, map_name)
    
    # Clean and format date string
    date_str = " ".join(date_parts)
    date_str = date_str.replace(" - ", " ").replace("-", " ")  # Remove various separators
    try:
        parts = date_str.split()
        if len(parts) >= 2:  # Changed condition to handle shorter date formats
            day = parts[0].zfill(2)  # Ensure 2 digits for day
            month = parts[1]
            # Set default values for year and time if not provided
            year = parts[2] if len(parts) > 2 else str(datetime.datetime.now().year)
            time = parts[3] if len(parts) > 3 else "00:00:00"
            
            # Validate time format and value
            if not is_valid_time(time):
                time = "00:00:00"
                
            data = f"{day} {month} {year} {time}"
        else:
            data = date_str
    except Exception as e:
        print(f"Warning: Could not format date: {date_str}")
        data = date_str
    
    return outcome, map_name, data

def write_csv(rows, filename, outcome="", map_name="", data=""):
    # Updated headers to include outcome and data
    headers = ["Outcome", "Map", "Data", "Rank", "Class", "Name", "Score", "Kills", "Deaths", "Assists", "Revives", "Captures"]
    
    # Add outcome, map and data to each row
    enhanced_rows = [[outcome, map_name, data] + row for row in rows]
    
    # Write to CSV file
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(enhanced_rows)

# Update the main execution block
input_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workflow')
scoreboard_files = glob.glob(os.path.join(input_directory, "scoreboard_*_ocr.txt"))

for scoreboard_file in scoreboard_files:
    # Find corresponding general info file
    timestamp = scoreboard_file.split('scoreboard_')[1].split('_ocr.txt')[0]
    general_info_file = os.path.join(input_directory, f"general_information_{timestamp}_ocr.txt")
    
    if not os.path.exists(general_info_file):
        print(f"Warning: No general information file found for {scoreboard_file}")
        continue
    
    # Generate output filename based on timestamp
    output_file = os.path.join(input_directory, f"match_{timestamp}_processed.csv")
    
    # Read and process both files
    scoreboard_lines = read_input_file(scoreboard_file)
    general_info_lines = read_input_file(general_info_file)
    
    if scoreboard_lines and general_info_lines:
        # Process the files
        outcome, map_name, data = process_general_info(general_info_lines)
        rows = process_lines(scoreboard_lines)
        
        # Write the output to a CSV file
        write_csv(rows, output_file, outcome, map_name, data)
        print(f"CSV file '{output_file}' has been created with data from both files.")
