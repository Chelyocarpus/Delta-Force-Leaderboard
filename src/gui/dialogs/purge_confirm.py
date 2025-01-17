from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel, QLineEdit, QPushButton, QMessageBox
from PyQt5.QtCore import Qt

class PurgeConfirmDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Confirm Database Purge")
        self.setModal(True)
        
        layout = QVBoxLayout()
        
        # Warning label
        warning = QLabel("WARNING: This will permanently delete ALL match data!\nType 'PURGE' to confirm:")
        warning.setStyleSheet("color: red; font-weight: bold;")
        layout.addWidget(warning)
        
        # Confirmation input
        self.confirm_input = QLineEdit()
        layout.addWidget(self.confirm_input)
        
        # Confirm button
        self.purge_btn = QPushButton("Purge Database")
        self.purge_btn.setStyleSheet("background-color: #ff4444;")
        self.purge_btn.clicked.connect(self.check_confirmation)
        layout.addWidget(self.purge_btn)
        
        # Cancel button
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)
        
        self.setLayout(layout)

    def check_confirmation(self):
        if self.confirm_input.text() == "PURGE":
            self.accept()
        else:
            QMessageBox.warning(self, "Invalid Confirmation", 
                "Please type 'PURGE' exactly to confirm database purge.")
