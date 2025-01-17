# delta-force-leaderboard
![Splash Screen](https://github.com/user-attachments/assets/6988feac-4adf-4b05-b853-e46de93c5fbf)

This project is designed to process and analyze player statistics from the Delta Force video game using OCR (Optical Character Recognition) and data processing techniques. The project consists of several scripts that handle different aspects of the workflow, from preparing the screenshot for OCR, performing OCR on images, processing and cleaning the extracted data, and finally displaying the results in a user-friendly GUI.

Despite its name, this project could be adapted to any video game that features a scoreboard or statistics. The OCR and file structure allows for customization to fit different game formats and data structures, making it a versatile tool for analyzing player performance across various games.

It is a also prime example of the capabilities of AI tools like GitHub Copilot, Claude 3.5 Sonnet, and GPT-4. The codebase is entirely generated with the assistance of these language models, showcasing their potential in software development.

# Core Features

📊 **Comprehensive Statistics**
<p align="center">
    <img src="https://github.com/user-attachments/assets/4426d914-d115-4627-a07e-c64748435dd6" width="50%" />
</p>

- Detailed player performance metrics including K/D ratio, assists, revives and captures
- Advanced scoring system for multiple combat roles
- Historical match data preservation


🎖️ **Medal Recognition System**
<p align="center">
    <img src="https://github.com/user-attachments/assets/735bbf50-c680-47c5-8e5c-57c32eeaf895" width="50%" />
</p>

- Automatic detection of Combat, Capture, Logistics, and Intelligence medals
- Tracks Bronze, Silver, and Gold achievement tiers
- Recognition for outstanding battlefield performances


⚔️ **Multi-Role Support**
<p align="center">
    <img src="https://github.com/user-attachments/assets/81861a9c-8b75-4b08-95d1-d1b971997377" width="50%" />
</p>

- Specialized tracking for Support, Recon, Assault, and Engineer classes
- Role-specific performance metrics


🎯 **Map Intelligence**
<p align="center">
    <img src="https://github.com/user-attachments/assets/d5b5e09e-140b-4365-95bb-ddcac599b88c" width="50%" />
</p>

- Performance tracking across different battlefields
- Map-specific statistics and outcomes


🤝 **Team Analytics**
<p align="center">
    <img src="https://github.com/user-attachments/assets/5f5c8f92-af55-4923-865b-8d5e4ea90948" width="50%" />
</p>

- Detailed team performance metrics
- Attack and Defense side statistics


💾 **Database Management**
<p align="center">
  <img src="https://github.com/user-attachments/assets/ad4ea027-612c-4f2a-aa83-683f7f122a06" width="50%" />
</p>

- Comprehensive automated backup system that creates hourly snapshots of the database to prevent data loss
- Manual backup functionality allowing users to create on-demand database copies at any time
- Flexible restore system capable of recovering data from any previous backup point
- Advanced data integrity checks and protection mechanisms to ensure database reliability

🔍 **Search & Filter**
- Quick player lookup
- Sort by any stat column
- Customizable data views

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
> `pip install -r requirements.txt`

- python-doctr==0.6.0
- python-doctr[torch]
- Pillow>=9.0.0
- typing-extensions>=4.0.0
- pathlib>=1.0.1

# Q & A
- **Q: Can using these scripts result in a ban due to anti-cheat mechanisms?**
- **A:** No, these scripts operate solely on screenshots captured via the print screen button or Steam overlay. They do not interact with the game directly (no memory reading, hooking, etc.), ensuring compliance with anti-cheat policies.

# Credits
- Claude 3.5 Sonnet (Main Developer)
- GPT-4 (AI Assistance)
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