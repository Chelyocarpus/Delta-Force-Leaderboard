<p align="center">
    <img src="https://github.com/user-attachments/assets/afe99d59-28dc-4896-81fa-3025da782333" width="50%" />
</p>

This project processes and analyzes player statistics from the Delta Force video game using OCR and data processing techniques, aiming to provide detailed insights and analytics for players. The project consists of several scripts that handle different aspects of the workflow, from preparing the screenshot for OCR, performing OCR on images, processing and cleaning the extracted data, and finally displaying the results in a user-friendly GUI.

Despite its name, this project could be adapted to any video game that features a scoreboard or statistics. The OCR and file structure allows for customization to fit different game formats and data structures, making it a versatile tool for analyzing player performance across various games.

It is a also prime example of the capabilities of AI tools like GitHub Copilot and Claude 3.5 & 3.7 Sonnet. The codebase is entirely generated with the assistance of these language models, showcasing their potential in software development.

# Core Features

📊 **Comprehensive Performance Tracking**
<p align="center">
    <img src="https://github.com/user-attachments/assets/c8403b36-7b3a-4e52-a56f-bfc8d6fb8185" width="50%" />
</p>

- Monitors monthly trends for kills, deaths, assists, and revives with interactive visualization
- Tracks detailed combat metrics including K/D ratio, vehicle damage, and objective captures
- Records and displays player class usage percentages and identifies favorite class
- Calculates win rates and tracks match outcomes with detailed performance history
- Measures team contributions through revives, tactical respawns, and assist tracking

🎖️ **Medal Tracking System**
<p align="center">
    <img src="https://github.com/user-attachments/assets/37d62074-78b2-48b5-9861-19e5cc2cd619" width="50%" />
</p>

- Medal statistics tracking with visual summary at the top
- Automatic detection of Combat, Capture, Logistics, and Intelligence medals
- Dynamic table display showing match history with medal achievements
- Color-coded visualization of Bronze, Silver, and Gold tier medals with emoji indicators


⚔️ **Multi-Role Support**
<p align="center">
    <img src="https://github.com/user-attachments/assets/3a18e9ad-8d71-48d4-97f7-db747de10232" width="50%" />
</p>

- Shows detailed statistics for each class including games played, victories, and win rates
- Tracks kills, deaths, K/D ratio, and vehicle damage statistics per class
- Displays total score, average score, and best score achievements per class


🎯 **Map Performance**
<p align="center">
    <img src="https://github.com/user-attachments/assets/4b584b98-beb4-456c-940b-e9b660c8c9a9" width="50%" />
</p>

- Track performance metrics for each battlefield
- Monitor kills, score, and combat efficiency per map
- Track your best performances and averages


🤝 **Team Analytics**
<p align="center">
    <img src="https://github.com/user-attachments/assets/35d01e74-a8d2-45e6-bf72-7094ea984b3d" width="50%" />
</p>

- Detailed team performance metrics
- Attack and Defense side statistics

🥇 **Achievements**
<p align="center">
    <img src="https://github.com/user-attachments/assets/4f0ec69f-8155-4dad-89e4-093c4e2bc9ac" width="50%" />
</p>

- Tracks 16+ unique achievements across 5 categories with exponential progression and visual star ratings
- Shows detailed performance metrics with color-coded progress bars
- Features 8-10 levels per achievement with clear progress tracking

💾 **Database Management**
<p align="center">
  <img src="https://github.com/user-attachments/assets/a5cf999e-e82d-479e-8425-8855067efbb1" width="50%" />
</p>

- Comprehensive automated backup system that creates hourly snapshots of the database to prevent data loss
- Manual backup functionality allowing users to create on-demand database copies at any time
- Flexible restore system capable of recovering data from any previous backup point
- Advanced data integrity checks and protection mechanisms to ensure database reliability

🔄 **Automated Processing**
- Screenshot-based data capture
- Intelligent OCR recognition

# 🔑 Key Components

**Screenshot cropping (crop_regions.py)**
- Opens an image from a specified path.
- Uses the pillow library to crop the image to a specified rectangular region.
- Saves the cropped image to a specified output folder.

**Extract Medals (extract_medals.py)**
- Detects medal presence using pixel-perfect color threshold analysis
- Supports 4 medal categories: Combat, Capture, Logistics, Intelligence
- Identifies medal ranks (Gold, Silver, Bronze)
- Batch processes multiple images from a folder
- Outputs results to workflow directory

**Extract Team Name (extract_team_name.py)**
- Searches for bright pixels (230+ RGB values) in a specific region to detect team presence.
- Crops the team name section using predefined coordinates.
- Processes multiple screenshots in batch mode.
- Saves cropped images to a workflow subfolder with naming pattern team_<original_filename>.jpg

**OCR Processing (batch_ocr_processor.py)**
- Uses the doctr library to perform OCR on screenshots containing player statistics.
- Configures the OCR predictor with specific detection and recognition architectures.
- Saves the extracted text to a .txt file for further processing.

**Data Cleanup (process_match_data.py)**
- Reads the OCR output from the .txt file.
- Processes the lines to extract relevant player statistics, including rank, class, name, score, kills, deaths, assists, revives, and captures.
- Tries to fix issues caused by OCR (e.g. wrong or missing characters)
- Maps class symbols to their respective names (e.g., "+" to "Medic").
- Writes the cleaned data to a CSV file (output.csv).

**GUI Display (leaderboard.py)**
- Provides a PyQt5-based GUI to display player statistics.
- Includes a PlayerDetailsDialog class to show detailed statistics for a selected player.
- Displays a summary of player statistics, including games played, total score, average score, total kills, total deaths, K/D ratio, total assists, total revives, total captures, best score, average rank, and favorite class.
- Shows a match history table with detailed statistics for each match.

# Example Workflow
### 1. Take a Screenshot

- Take a screenshot right after the round ends or from the match history view.

### 2. Start run.py

- Run `run.py` to process your screenshots and output useful data for `leaderboard.py`.

### 3. Start leaderboard.py

- Next, run `leaderboard.py`. You’ll be prompted automatically to import new data.

# Dependencies
> [!tip]
> To install the necessary dependencies, run the following command in your terminal: `pip install -r requirements.txt`

- PyQt5==5.15.9
- Pillow==10.0.0
- tqdm==4.66.1
- python-doctr==0.6.0
- python-doctr[torch]
- typing-extensions>=4.0.0
- pathlib>=1.0.1
- markdown>=3.4.1
- packaging>=21.3
- requests>=2.27.1
- security==1.3.1

# Q & A
- **Q: Can using these scripts result in a ban due to anti-cheat mechanisms?**
- **A:** No, these scripts operate solely on screenshots captured via the print screen button or Steam overlay. They do not interact with the game directly (no memory reading, hooking, etc.), ensuring compliance with anti-cheat policies.

- **Q: Does this include statistics for all Delta Force players?**
- **A:** No, it only displays stats for players you've played with. The data comes solely from the screenshots you've imported, there's no access to an online database.

# Credits
- Claude 3.5 & 3.7 Sonnet (Main Developer)
- Team Jade (Delta Force Developers)
- GitHub Copilot (Code Suggestions)
- Community Contributors

# Acknowledgments

Special thanks to [Mindee](https://github.com/mindee/doctr) for their exceptional `docTR` OCR library, which has significantly streamlined the text recognition pipeline. While traditional OCR approaches often require complex preprocessing steps including image upsampling, format conversion, binary mask generation, and color inversions, docTR provides an elegant solution with minimal setup.

The library's powerful OCR capabilities can be implemented with just a few lines of code:

```python
from doctr.models import ocr_predictor

# Initialize the OCR model with pre-trained weights
predictor = ocr_predictor(
    det_arch='fast_base',
    reco_arch='crnn_vgg16_bn',
    pretrained=True
)

# Process document
result = predictor(doc_image)
```

This implementation has drastically improved the OCR accuracy while reducing development complexity and maintenance overhead. The pre-trained models perform exceptionally well across various document types and text styles, making it an invaluable tool for document processing needs.
