import os
import subprocess
import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QPushButton, QVBoxLayout, 
                            QWidget, QFileDialog, QLabel, QMessageBox, QProgressBar,
                            QTextEdit, QStatusBar)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
import json

class SettingsManager:
    def __init__(self):
        self.settings_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'settings.json')
        self.settings = self.load_settings()
    
    def load_settings(self):
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, 'r') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Error loading settings: {e}")
                return {"screenshots_path": ""}
        return {"screenshots_path": ""}
    
    def save_settings(self):
        try:
            with open(self.settings_file, 'w') as f:
                json.dump(self.settings, f)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def get_screenshots_path(self):
        return self.settings.get("screenshots_path", "")
    
    def set_screenshots_path(self, path):
        self.settings["screenshots_path"] = path
        self.save_settings()

class ProcessingThread(QThread):
    progress_update = pyqtSignal(int, str)
    process_complete = pyqtSignal(bool, str)
    
    def __init__(self, scripts, script_dir, screenshots_path):
        super().__init__()
        self.scripts = scripts
        self.script_dir = script_dir
        self.screenshots_path = screenshots_path
        
    def run(self):
        os.environ["DELTA_SCREENSHOTS_PATH"] = self.screenshots_path
        
        total_scripts = len(self.scripts)
        
        for i, script in enumerate(self.scripts):
            try:
                script_path = os.path.join(self.script_dir, script)
                self.progress_update.emit(int(((i) / total_scripts) * 100), f"Running {os.path.basename(script)}...")
                
                # Run the script and capture output
                process = subprocess.Popen(
                    ['python', script_path], 
                    stdout=subprocess.PIPE, 
                    stderr=subprocess.PIPE,
                    text=True
                )
                
                while process.poll() is None:
                    # Read output in real-time
                    stdout_line = process.stdout.readline()
                    if stdout_line:
                        self.progress_update.emit(
                            int(((i + 0.5) / total_scripts) * 100), 
                            stdout_line.strip()
                        )
                
                # Check for any errors
                if process.returncode != 0:
                    stderr_output = process.stderr.read()
                    self.process_complete.emit(False, f"Error running {script}: {stderr_output}")
                    return
                
            except Exception as e:
                self.process_complete.emit(False, f"Error running {script}: {str(e)}")
                return
        
        self.progress_update.emit(100, "Processing completed successfully!")
        self.process_complete.emit(True, "All scripts have run successfully.")

class DeltaForceLeaderboard(QMainWindow):
    def __init__(self):
        super().__init__()
        self.settings_manager = SettingsManager()
        self.processing_thread = None
        self.initUI()
    
    def initUI(self):
        self.setWindowTitle('Delta Force Leaderboard Processor')
        self.setGeometry(300, 300, 700, 500)
        
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)
        
        # Welcome message
        welcome_label = QLabel("Welcome to Delta Force Leaderboard Processor!")
        welcome_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(welcome_label)
        
        # Path display
        self.path_label = QLabel(f"Screenshots folder: {self.settings_manager.get_screenshots_path()}")
        layout.addWidget(self.path_label)
        
        # Set path button
        path_button = QPushButton("Set Screenshots Folder")
        path_button.clicked.connect(self.set_screenshots_path)
        layout.addWidget(path_button)
        
        # Process button
        self.process_button = QPushButton("Process Screenshots")
        self.process_button.clicked.connect(self.process_screenshots)
        layout.addWidget(self.process_button)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Status log
        self.log_display = QTextEdit()
        self.log_display.setReadOnly(True)
        self.log_display.setMinimumHeight(200)
        layout.addWidget(self.log_display)
        
        # Instructions
        instructions = QLabel(
            "Instructions:\n"
            "1. Set the folder where your game screenshots are stored\n"
            "2. Click 'Process Screenshots' to analyze the images\n"
            "3. Results will be saved in the workflow folder"
        )
        layout.addWidget(instructions)
        
        # Status bar
        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("Ready")
    
    def set_screenshots_path(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Screenshots Folder")
        if folder:
            self.settings_manager.set_screenshots_path(folder)
            self.path_label.setText(f"Screenshots folder: {folder}")
            self.statusBar.showMessage(f"Screenshots folder set to: {folder}")
    
    def process_screenshots(self):
        screenshots_path = self.settings_manager.get_screenshots_path()
        if not screenshots_path or not os.path.exists(screenshots_path):
            QMessageBox.warning(self, "Invalid Path", "Please set a valid screenshots folder path first.")
            return
        
        # Disable the process button while processing
        self.process_button.setEnabled(False)
        self.progress_bar.setValue(0)
        self.log_display.clear()
        self.log_display.append("Starting processing...")
        self.statusBar.showMessage("Processing in progress...")
        
        script_dir = os.path.dirname(os.path.abspath(__file__))
        
        # List of scripts to run
        scripts = [
            'components/crop_regions.py',
            'components/extract_medals.py',
            'components/extract_team_name.py',
            'components/batch_ocr_processor.py',
            'components/process_match_data.py'
        ]
        
        # Create and start the processing thread
        self.processing_thread = ProcessingThread(scripts, script_dir, screenshots_path)
        self.processing_thread.progress_update.connect(self.update_progress)
        self.processing_thread.process_complete.connect(self.processing_finished)
        self.processing_thread.start()
    
    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.log_display.append(message)
        # Ensure the latest message is visible
        self.log_display.verticalScrollBar().setValue(self.log_display.verticalScrollBar().maximum())
        self.statusBar.showMessage(f"Processing: {value}%")
    
    def processing_finished(self, success, message):
        self.process_button.setEnabled(True)
        
        if success:
            self.statusBar.showMessage("Processing completed successfully")
            self.log_display.append("✅ " + message)
            QMessageBox.information(self, "Success", message)
        else:
            self.statusBar.showMessage("Processing failed")
            self.log_display.append("❌ " + message)
            QMessageBox.critical(self, "Processing Error", message)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = DeltaForceLeaderboard()
    window.show()
    sys.exit(app.exec_())