from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QFormLayout, QLineEdit,
                           QPushButton, QMessageBox, QComboBox, QHBoxLayout)
from PyQt5.QtCore import Qt

class EditSnapshotDialog(QDialog):
    def __init__(self, parent, match_details):
        super().__init__(parent)
        self.parent = parent
        self.match_details = match_details
        self.setWindowTitle("Edit Match Entry")
        self.setModal(True)
        self.init_ui()
        self.load_data()

    def init_ui(self):
        layout = QVBoxLayout()
        form = QFormLayout()

        # Create input fields
        self.date_input = QLineEdit()
        self.map_input = QLineEdit()
        self.outcome_combo = QComboBox()
        self.outcome_combo.addItems(["VICTORY", "DEFEAT"])
        self.team_combo = QComboBox()
        self.team_combo.addItems(["ATTACK", "DEFENSE"])

        # Add fields to form
        form.addRow("Date:", self.date_input)
        form.addRow("Map:", self.map_input)
        form.addRow("Outcome:", self.outcome_combo)
        form.addRow("Team:", self.team_combo)

        layout.addLayout(form)

        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_changes)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)

    def load_data(self):
        try:
            self.date_input.setText(self.match_details['date'])
            self.map_input.setText(self.match_details['map'])
            self.outcome_combo.setCurrentText(self.match_details['outcome'])
            self.team_combo.setCurrentText(self.match_details['team'])
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load data: {str(e)}")

    def save_changes(self):
        try:
            with self.parent.parent.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE matches 
                    SET data = ?, map = ?, outcome = ?, team = ?
                    WHERE data = ? AND map = ? AND outcome = ? AND team = ?
                """, (
                    self.date_input.text(),
                    self.map_input.text(),
                    self.outcome_combo.currentText(),
                    self.team_combo.currentText(),
                    self.match_details['date'],
                    self.match_details['map'],
                    self.match_details['outcome'],
                    self.match_details['team']
                ))
                
            QMessageBox.information(self, "Success", "Changes saved successfully!")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save changes: {str(e)})")