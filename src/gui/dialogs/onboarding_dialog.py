from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QLabel, QLineEdit, 
                            QPushButton, QHBoxLayout, QWidget, QSpacerItem,
                            QSizePolicy)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont

class OnboardingDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Welcome to Delta Force Leaderboard")
        self.setMinimumWidth(450)
        self.setModal(True)
        
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        self.setLayout(layout)
        
        # Welcome header
        welcome_label = QLabel("Welcome to Delta Force Leaderboard!")
        welcome_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        welcome_label.setFont(font)
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))
        layout.addWidget(welcome_label)
        
        # Explanation text
        info_label = QLabel(
            "To help identify your stats, please enter your in-game player name below."
            "This will be used to track your performance, award medals and achievements."
        )
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignCenter)
        layout.addItem(QSpacerItem(20, 10, QSizePolicy.Minimum, QSizePolicy.Minimum))
        layout.addWidget(info_label)
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Minimum))
        
        # Player name input
        name_layout = QHBoxLayout()
        name_label = QLabel("Your Player Name:")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Enter your in-game name")
        name_layout.addWidget(name_label)
        name_layout.addWidget(self.name_input)
        
        layout.addLayout(name_layout)
        layout.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))
        
        # Buttons
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("Save")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.accept)
        self.skip_button = QPushButton("Skip")
        self.skip_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.skip_button)
        button_layout.addWidget(self.save_button)
        
        layout.addLayout(button_layout)
        
        # Connect signals
        self.name_input.textChanged.connect(self.validate_input)
        
    def validate_input(self, text):
        self.save_button.setEnabled(bool(text.strip()))
        
    def get_player_name(self):
        return self.name_input.text().strip()
