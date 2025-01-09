from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QPushButton, 
    QListWidget, QHBoxLayout, QListWidgetItem, QCheckBox
)
from PyQt5.QtCore import Qt

class ImportOnStartupDialog(QDialog):
    def __init__(self, new_files, parent=None):
        super().__init__(parent)
        self.new_files = new_files
        self.selected_files = []
        self.initialize_ui()

    def initialize_ui(self):
        self.setWindowTitle("New Data Files Found")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Add description label
        label = QLabel("The following new files were found in the imports folder:")
        layout.addWidget(label)
        
        # Create list widget for files
        self.list_widget = QListWidget()
        for file in self.new_files:
            item = QListWidgetItem()
            self.list_widget.addItem(item)
            checkbox = QCheckBox(file)
            checkbox.setChecked(True)
            self.list_widget.setItemWidget(item, checkbox)
        layout.addWidget(self.list_widget)
        
        # Add buttons
        button_layout = QHBoxLayout()
        
        self.import_button = QPushButton("Import Selected")
        self.import_button.clicked.connect(self.accept)
        
        self.skip_button = QPushButton("Skip")
        self.skip_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.import_button)
        button_layout.addWidget(self.skip_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)

    def get_selected_files(self):
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            checkbox = self.list_widget.itemWidget(item)
            if checkbox.isChecked():
                selected.append(checkbox.text())
        return selected
