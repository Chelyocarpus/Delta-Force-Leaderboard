import sqlite3
import re
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                            QLineEdit, QComboBox, QPushButton, QMessageBox, QLabel)
from PyQt5.QtCore import Qt

class EditSnapshotDialog(QDialog):
    def __init__(self, parent, match_details):
        super().__init__(parent)
        self.parent = parent
        self.match_details = match_details.copy()  # Copy to avoid modifying original
        self.original_snapshot = match_details.get('snapshot_name', '')
        self.original_full_date = match_details.get('full_date', '')
        
        self.setWindowTitle("Edit Match")
        self.setMinimumWidth(400)
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # Form for editing basic match details
        form_layout = QFormLayout()
        
        # Date field
        self.date_input = QLineEdit(self.match_details.get('date', ''))
        form_layout.addRow("Date:", self.date_input)
        
        # Time field
        self.time_input = QLineEdit(self.match_details.get('time', ''))
        form_layout.addRow("Time:", self.time_input)
        
        # Map field
        self.map_input = QComboBox()
        self.map_input.setEditable(True)
        self.map_input.setCurrentText(self.match_details.get('map', ''))
        self.load_maps()
        form_layout.addRow("Map:", self.map_input)
        
        # Outcome field
        self.outcome_input = QComboBox()
        self.outcome_input.addItems(["VICTORY", "DEFEAT"])
        self.outcome_input.setCurrentText(self.match_details.get('outcome', 'VICTORY'))
        form_layout.addRow("Outcome:", self.outcome_input)
        
        # Team field
        self.team_input = QComboBox()
        self.team_input.setEditable(True)
        self.team_input.setCurrentText(self.match_details.get('team', ''))
        self.load_teams()
        form_layout.addRow("Team:", self.team_input)
        
        layout.addLayout(form_layout)
                
        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save Changes")
        save_button.clicked.connect(self.save_changes)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def load_maps(self):
        """Load existing maps from database"""
        try:
            with self.parent.parent.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT map FROM matches ORDER BY map")
                maps = [row[0] for row in cursor.fetchall()]
                self.map_input.clear()
                self.map_input.addItems(maps)
                # Set back the current value
                self.map_input.setCurrentText(self.match_details.get('map', ''))
        except Exception as e:
            print(f"Error loading maps: {e}")
            
    def load_teams(self):
        """Load existing teams from database"""
        try:
            with self.parent.parent.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT DISTINCT team FROM matches ORDER BY team")
                teams = [row[0] for row in cursor.fetchall()]
                self.team_input.clear()
                self.team_input.addItems(teams)
                # Set back the current value
                self.team_input.setCurrentText(self.match_details.get('team', ''))
        except Exception as e:
            print(f"Error loading teams: {e}")
            
    def save_changes(self):
        """Save changes to the database"""
        try:
            # Get values from form
            new_date = self.date_input.text().strip()
            new_time = self.time_input.text().strip()
            new_map = self.map_input.currentText().strip()
            new_outcome = self.outcome_input.currentText().strip()
            new_team = self.team_input.currentText().strip()
            
            # Validate input
            if not all([new_date, new_map, new_outcome, new_team]):
                QMessageBox.warning(self, "Validation Error", "Date, Map, Outcome and Team fields are required")
                return
            
            # Validate time format if provided
            if new_time and not self._is_valid_time_format(new_time):
                QMessageBox.warning(self, "Invalid Time Format", 
                                  "Time should be in HH:MM:SS or HH:MM format")
                return
            
            # Combine date and time for the database
            new_full_date = new_date
            if new_time:
                new_full_date += f" {new_time}"
                
            # Extract components from the original match ID
            if not self.original_snapshot:
                # If no snapshot name provided, construct from individual parts
                parts = self.match_details.get('outcome', '') + ' - ' + \
                        self.match_details.get('map', '') + ' - ' + \
                        self.original_full_date + ' - ' + \
                        self.match_details.get('team', '')
            else:
                parts = self.original_snapshot
                
            try:
                original_outcome, original_map, original_date, original_team = parts.split(' - ')
            except ValueError:
                QMessageBox.critical(self, "Error", "Could not parse original match details")
                return
                
            with self.parent.parent.db.get_connection() as conn:
                cursor = conn.cursor()
                
                # Update the match entries
                cursor.execute("""
                    UPDATE matches 
                    SET data = ?, map = ?, outcome = ?, team = ? 
                    WHERE data = ? AND map = ? AND outcome = ? AND team = ?
                """, (new_full_date, new_map, new_outcome, new_team,
                      self.original_full_date, original_map, original_outcome, original_team))
                
                rows_updated = cursor.rowcount
                conn.commit()
                
                if rows_updated > 0:
                    QMessageBox.information(self, "Success", 
                                          f"Updated {rows_updated} match entries")
                    self.accept()
                else:
                    QMessageBox.warning(self, "No Changes", 
                                      "No records were updated. The match may have been deleted.")
        
        except sqlite3.Error as e:
            QMessageBox.critical(self, "Database Error", f"Failed to update match: {str(e)}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"An unexpected error occurred: {str(e)}")
    
    def _is_valid_time_format(self, time_str):
        """Validate time format (HH:MM:SS or HH:MM)"""
        return bool(re.match(r'^\d{1,2}:\d{2}(:\d{2})?$', time_str))