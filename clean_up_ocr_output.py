import csv
import os
import glob

def read_input_file(filepath):
    """
    Reads the content of a file and returns it as a list of lines.

    Args:
        filepath (str): The path to the input file.

    Returns:
        list: A list of strings, each representing a line in the file.
              Returns None if the file is not found or an error occurs.

    Raises:
        FileNotFoundError: If the file does not exist.
        Exception: For any other exceptions that occur during file reading.
    """
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
    """
    Processes a list of input lines from OCR output and extracts structured data.
    Args:
        input_lines (list of str): List of strings, each representing a line of OCR output.
    Returns:
        list of list: A list of rows, where each row is a list containing:
            - Prefix (str): The rank or identifier (e.g., "1", "2", etc.).
            - Class (str): The class name derived from symbols ("Support", "Recon", "Assault", "Engineer").
            - Name (str): The name extracted from the line.
            - Numbers (list of int): A list of exactly 6 integers representing scores, kills, etc.
    Notes:
        - Lines containing words are processed to extract prefix, class, and name.
        - Lines containing only numbers are assumed to be scores and are collected.
        - If OCR fails to detect the class, it defaults to "Engineer".
        - The function ensures that each row has exactly 6 numbers; otherwise, the row is discarded.
    """
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

def write_csv(rows, filename):
    # Define the CSV headers
    headers = ["Rank", "Class", "Name", "Score", "Kills", "Deaths", "Assists", "Revives", "Captures"]
    
    # Write to CSV file
    with open(filename, mode='w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(headers)
        writer.writerows(rows)

# Update the main execution block
input_directory = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'workflow')
for input_file in glob.glob(os.path.join(input_directory, "*_ocr.txt")):
    # Generate output filename by replacing _ocr.txt with _processed.csv
    output_file = input_file.replace("_ocr.txt", "_processed.csv")
    
    # Read and process the input file
    input_lines = read_input_file(input_file)
    if input_lines:
        # Process the lines
        rows = process_lines(input_lines)

        # Write the output to a CSV file
        write_csv(rows, output_file)
        print(f"CSV file '{output_file}' has been created.")
