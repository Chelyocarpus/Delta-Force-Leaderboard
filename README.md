# delta-force-leaderboard

![grafik](https://github.com/user-attachments/assets/f8326d92-e905-42fb-b038-8d7b9cf656ae)

This project is designed to process and analyze player statistics from the Delta Force video game using OCR (Optical Character Recognition) and data processing techniques. The project consists of several scripts that handle different aspects of the workflow, from preparing the screenshot for OCR, performing OCR on images, cleaning up and processing the extracted data, and finally displaying the results in a user-friendly GUI.

This code is completly 100% AI generated with GitHub Copilot (more like Mainpilot). This project is also a good example what LLM's like Claude 3.5 Sonnet and GPT 4o are capable of.

# Key Components

### Screenshot cropping (prepare_scoreboard_for_ocr.py)

- Opens an image from a specified path.
- Uses the pillow library to crop the image to a specified rectangular region.
- Saves the cropped image to a specified output folder.

### OCR Processing (perform_ocr_on_img.py)

- Uses the doctr library to perform OCR on screenshots containing player statistics.
- Configures the OCR predictor with specific detection and recognition architectures.
- Saves the extracted text to a .txt file for further processing.

### Data Cleanup (clean_up_ocr_output.py)

- Reads the OCR output from the .txt file.
- Processes the lines to extract relevant player statistics, including rank, class, name, score, kills, deaths, assists, revives, and captures.
- Tries to fix issues caused by OCR (e.g. wrong or missing characters)
- Maps class symbols to their respective names (e.g., "+" to "Medic").
- Writes the cleaned data to a CSV file (output.csv).

### GUI Display (stats.py)

- Provides a PyQt5-based GUI to display player statistics.
- Includes a PlayerDetailsDialog class to show detailed statistics for a selected player.
- Displays a summary of player statistics, including games played, total score, average score, total kills, total deaths, K/D ratio, total assists, total revives, total captures, best score, average rank, and favorite class.
- Shows a match history table with detailed statistics for each match.

# Example Workflow
### 1. Take a Screenshot

- Take a screenshot of the scoreboard ingame (either after the Round or in Match History)

### 2. Prepare Screenshot for OCR

- Run prepare_scoreboard_for_ocr.py to prepare the screenshot for OCR. The better the source, the better the OCR

### 3. Perform OCR on Image

- Run perform_ocr_on_img.py to analyze image and extract text data.
- The extracted text is saved to ocr_output.txt.

### 4. Clean Up OCR Output

- Run clean_up_ocr_output.py to process the OCR output and generate a cleaned CSV file (output.csv).

### 5. Display Statistics in GUI

- Run stats.py to launch the GUI. Import .csv data, view player statistics and match history.

# Dependencies
- Python 3.x
- PyQt5
- doctr
- pillow
- pytesseract
- OpenCV
- csv
- sqlite3

# Q & A
- **Q: This game has Anti-Cheat, can these scripts get me banned?**
- A: No, these scripts work entirely based on the screenshot made with the print screen button or Steam overlay. There's no interaction with the game itself whatsoever (no memory reading, hooking, etc.)

# Credits
- Claude 3.5 Sonnet
- GPT 4o
- Team Jade (Delta Force Developers)

