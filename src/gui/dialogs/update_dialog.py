from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
    QCheckBox, QTextBrowser, QProgressBar, QMessageBox, QApplication
)
from PyQt5.QtCore import Qt, QUrl
from PyQt5.QtGui import QDesktopServices
import re
import markdown
import os
import sys
import subprocess
from src.utils.auto_updater import UpdateDownloader

class UpdateDialog(QDialog):
    def __init__(self, latest_version, current_version, download_url, release_notes, parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self.latest_version = latest_version
        self.current_version = current_version
        self.parent = parent
        self.downloader = None
        
        self.setWindowTitle("Update Available")
        self.setMinimumWidth(500)
        self.setMinimumHeight(300)
        
        self.main_layout = QVBoxLayout()
        
        # Add header with version information
        header_label = QLabel(f"<h2>Update Available!</h2>"
                             f"<p>A new version of Delta Force Leaderboard is available.</p>"
                             f"<p>Current version: {current_version}<br>"
                             f"Latest version: {latest_version}</p>")
        header_label.setTextFormat(Qt.RichText)
        self.main_layout.addWidget(header_label)
        
        # Display release notes
        notes_label = QLabel("<h3>Release Notes:</h3>")
        self.main_layout.addWidget(notes_label)
        
        notes_browser = QTextBrowser()
        # Convert Markdown to HTML for proper display
        try:
            # Process GitHub-style content
            processed_notes = self._process_release_notes(release_notes)
            
            html_notes = markdown.markdown(
                processed_notes,
                extensions=['fenced_code', 'tables', 'nl2br']
            )
            notes_browser.setHtml(html_notes)
        except Exception as e:
            print(f"Error processing release notes: {e}")
            # Fallback to plain text if markdown conversion fails
            notes_browser.setPlainText(release_notes)
        
        notes_browser.setOpenExternalLinks(True)
        self.main_layout.addWidget(notes_browser)
        
        # Add progress bar (hidden initially)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.main_layout.addWidget(self.progress_bar)
        
        # Status label (hidden initially)
        self.status_label = QLabel("Downloading update...")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setVisible(False)
        self.main_layout.addWidget(self.status_label)
        
        # Option to disable future notifications
        self.disable_check = QCheckBox("Don't check for updates automatically")
        self.main_layout.addWidget(self.disable_check)
        
        # Buttons for actions
        self.button_layout = QHBoxLayout()
        
        self.download_button = QPushButton("Download && Install")
        self.download_button.clicked.connect(self.download_and_install)
        
        self.browser_button = QPushButton("Open in Browser")
        self.browser_button.clicked.connect(self.open_download_url)
        
        self.remind_button = QPushButton("Remind Me Later")
        self.remind_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.cancel_download)
        self.cancel_button.setVisible(False)
        
        self.button_layout.addWidget(self.download_button)
        self.button_layout.addWidget(self.browser_button)
        self.button_layout.addWidget(self.remind_button)
        self.button_layout.addWidget(self.cancel_button)
        
        self.main_layout.addLayout(self.button_layout)
        self.setLayout(self.main_layout)
    
    def _process_release_notes(self, text):
        """Process release notes to handle GitMoji and improve formatting"""
        # Process GitHub-style checkboxes
        text = text.replace("- [ ]", "☐").replace("- [x]", "☑")
        
        # Make URLs clickable if not already in Markdown format
        url_pattern = r'(?<![\[\(])(https?://[^\s\)\]]+)(?![\]\)])'
        text = re.sub(url_pattern, r'[\1](\1)', text)
        
        # Handle GitMoji codes - convert to actual emoji
        gitmoji_mapping = {
            ":sparkles:": "✨", ":bug:": "🐛", ":memo:": "📝", ":rocket:": "🚀",
            ":art:": "🎨", ":zap:": "⚡️", ":fire:": "🔥", ":ambulance:": "🚑",
            ":books:": "📚", ":hammer:": "🔨", ":wrench:": "🔧", ":tada:": "🎉",
            ":lock:": "🔒", ":bookmark:": "🔖", ":rotating_light:": "🚨",
            ":construction:": "🚧", ":green_heart": "💚", ":arrow_down:": "⬇️",
            ":arrow_up:": "⬆️", ":pushpin:": "📌", ":construction_worker:": "👷",
            ":chart_with_upwards_trend:": "📈", ":recycle:": "♻️", ":heavy_plus_sign:": "➕",
            ":heavy_minus_sign:": "➖", ":wrench:": "🔧", ":globe_with_meridians:": "🌐",
            ":pencil2:": "✏️", ":hankey:": "💩", ":rewind:": "⏪", ":twisted_rightwards_arrows:": "🔀",
            ":package:": "📦", ":alien:": "👽", ":truck:": "🚚", ":page_facing_up:": "📄",
            ":boom:": "💥", ":bento:": "🍱", ":wheelchair:": "♿️", ":bulb:": "💡",
            ":beers:": "🍻", ":speech_balloon:": "💬", ":card_file_box:": "🗃️",
            ":loud_sound:": "🔊", ":mute:": "🔇", ":busts_in_silhouette:": "👥",
            ":children_crossing:": "🚸", ":iphone:": "📱", ":clown_face:": "🤡",
            ":egg:": "🥚", ":see_no_evil:": "🙈", ":camera_flash:": "📸",
            ":alembic:": "⚗️", ":mag:": "🔍", ":label:": "🏷️", ":seedling:": "🌱",
            ":triangular_flag_on_post:": "🚩", ":goal_net:": "🥅", ":dizzy:": "💫",
            ":wastebasket:": "🗑️", ":passport_control:": "🛂", ":adhesive_bandage:": "🩹",
            ":necktie:": "👔", ":stethoscope:": "🩺", ":technologist:": "🧑‍💻"
        }
        
        for code, emoji in gitmoji_mapping.items():
            text = text.replace(code, emoji)
        
        return text
    
    def download_and_install(self):
        """Download and install the update."""
        # Show progress UI
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Downloading update...")
        self.status_label.setVisible(True)
        
        # Hide/show appropriate buttons
        self.download_button.setEnabled(False)
        self.browser_button.setEnabled(False)
        self.remind_button.setEnabled(False)
        self.cancel_button.setVisible(True)
        
        # Start the download
        self.downloader = UpdateDownloader(self.download_url, self)
        self.downloader.signals.progress.connect(self.update_progress)
        self.downloader.signals.finished.connect(self.installation_ready)
        self.downloader.signals.error.connect(self.handle_error)
        self.downloader.start()
    
    def update_progress(self, value):
        """Update the progress bar."""
        self.progress_bar.setValue(value)
        if value >= 100:
            self.status_label.setText("Download complete. Preparing installation...")
    
    def installation_ready(self, install_script):
        """Handle the installation when download is complete."""
        self.status_label.setText("Update downloaded successfully!")
        
        reply = QMessageBox.question(
            self, "Install Update", 
            "The update has been downloaded. Install now? The application will restart.",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            try:
                # Run the installation script
                if os.path.exists(install_script):
                    if sys.platform.startswith('win'):
                        # Use subprocess.Popen to avoid waiting
                        subprocess.Popen(['cmd', '/c', install_script], 
                                        shell=False, creationflags=subprocess.CREATE_NEW_CONSOLE)
                    else:
                        # Unix platforms
                        subprocess.Popen(['bash', install_script])
                    
                    # Accept and close the application to allow the update to proceed
                    self.accept()
                    if self.parent:
                        self.parent.close()
                    else:
                        # Fixed: Use QApplication instance to quit
                        QApplication.instance().quit()
                else:
                    raise FileNotFoundError(f"Installation script not found: {install_script}")
            
            except Exception as e:
                QMessageBox.critical(
                    self, "Installation Error", 
                    f"Failed to start the installation: {str(e)}"
                )
        else:
            # Reset the UI if user cancels
            self.reset_ui()
    
    def handle_error(self, error_message):
        """Handle download or installation errors."""
        self.status_label.setText(f"Error: {error_message}")
        QMessageBox.critical(self, "Update Error", error_message)
        self.reset_ui()
    
    def reset_ui(self):
        """Reset the UI to initial state."""
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)
        self.download_button.setEnabled(True)
        self.browser_button.setEnabled(True)
        self.remind_button.setEnabled(True)
        self.cancel_button.setVisible(False)
    
    def cancel_download(self):
        """Cancel the download process."""
        if self.downloader and self.downloader.isRunning():
            self.downloader.cancel()
            self.downloader.wait()
        
        self.reset_ui()
        self.status_label.setText("Download cancelled")
        self.status_label.setVisible(True)
    
    def open_download_url(self):
        """Open the download URL in the default browser."""
        QDesktopServices.openUrl(QUrl(self.download_url))
        self.accept()
    
    def should_disable_updates(self):
        """Return whether automatic updates should be disabled."""
        return self.disable_check.isChecked()
