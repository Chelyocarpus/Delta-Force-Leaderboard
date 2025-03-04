from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, QDialogButtonBox, 
    QListWidget, QListWidgetItem, QApplication
)
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtCore import Qt, pyqtSignal, QObject, QRunnable, QThreadPool
import os
import time

class ImportSignals(QObject):
    """Signals for the import process"""
    progress = pyqtSignal(int, int)  # (current_file_index, total_files)
    file_status = pyqtSignal(str, bool, str)  # (filename, success, message)
    finished = pyqtSignal()
    error = pyqtSignal(str)

class ImportRunnable(QRunnable):
    """Runnable for importing CSV files using QThreadPool"""
    
    def __init__(self, db, files):
        super().__init__()
        self.db = db
        self.files = files
        self.signals = ImportSignals()
        self.is_running = True
        
    def run(self):
        total_files = len(self.files)
        
        for i, file_path in enumerate(self.files):
            if not self.is_running:
                break
                
            # Report progress
            self.signals.progress.emit(i, total_files)
            
            # Get file name for status reporting
            file_name = os.path.basename(file_path)
            
            try:
                # Use the thread-safe import method
                success = self.db.import_csv_worker(file_path)
                
                # Use different messages for duplicates vs successful imports
                if success:
                    self.signals.file_status.emit(file_name, True, "Successfully imported")
                else:
                    self.signals.file_status.emit(file_name, False, "Skipped duplicate file")
                    
                # Small delay to prevent UI from freezing and show progress
                time.sleep(0.1)
                
            except Exception as e:
                self.signals.file_status.emit(file_name, False, f"Error: {str(e)}")
        
        self.signals.finished.emit()

    def stop(self):
        self.is_running = False


class ImportProgressDialog(QDialog):
    """Dialog showing progress of CSV import operation"""
    def __init__(self, db, files, parent=None):
        super().__init__(parent)
        self.db = db
        self.files = files
        self.successful_imports = 0
        self.skipped_files = 0
        self.failed_files = 0
        self.runnable = None
        
        self.setWindowTitle("Importing Files")
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        # Create layout
        layout = QVBoxLayout(self)
        
        # Status label
        self.status_label = QLabel("Preparing to import files...")
        self.status_label.setAlignment(Qt.AlignCenter)
        font = QFont()
        font.setBold(True)
        self.status_label.setFont(font)
        layout.addWidget(self.status_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, len(files))
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Status list
        layout.addWidget(QLabel("Import Status:"))
        self.status_list = QListWidget()
        layout.addWidget(self.status_list)
        
        # Summary label
        self.summary_label = QLabel("")
        layout.addWidget(self.summary_label)
        
        # Button box
        self.button_box = QDialogButtonBox(QDialogButtonBox.Cancel)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        
        # Set up and start the import task
        self.start_import()
        
    def start_import(self):
        """Set up and start the import runnable"""
        # Create the import runnable
        self.runnable = ImportRunnable(self.db, self.files)
        
        # Connect signals
        self.runnable.signals.progress.connect(self.update_progress)
        self.runnable.signals.file_status.connect(self.update_file_status)
        self.runnable.signals.finished.connect(self.import_finished)
        
        # Start the runnable in the thread pool
        QThreadPool.globalInstance().start(self.runnable)
        
    def update_progress(self, current, total):
        """Update progress bar and status label"""
        self.progress_bar.setValue(current + 1)
        self.status_label.setText(f"Importing file {current + 1} of {total}...")
        
    def update_file_status(self, filename, success, message):
        """Update status list with file import result"""
        item = QListWidgetItem(f"{filename}: {message}")
        
        if success:
            item.setForeground(QColor("green"))
            self.successful_imports += 1
        elif "duplicate" in message.lower():
            item.setForeground(QColor("blue"))
            self.skipped_files += 1
        else:
            item.setForeground(QColor("red"))
            self.failed_files += 1
            
        self.status_list.addItem(item)
        self.status_list.scrollToBottom()
        
        # Update summary
        self._update_summary()
        
    def _update_summary(self):
        """Update the summary label with current stats"""
        total_processed = self.successful_imports + self.skipped_files + self.failed_files
        summary = f"Processed: {total_processed}/{len(self.files)} | "
        summary += f"Imported: {self.successful_imports} | "
        summary += f"Skipped: {self.skipped_files} | "
        summary += f"Failed: {self.failed_files}"
        self.summary_label.setText(summary)
        
    def import_finished(self):
        """Handle completion of the import process"""
        self.status_label.setText("Import Complete")
        self.button_box.clear()
        self.button_box.addButton(QDialogButtonBox.Ok)
        self.button_box.accepted.connect(self.accept)
        
    def reject(self):
        """Handle dialog rejection (Cancel button)"""
        # Stop the import process
        if self.runnable:
            self.runnable.stop()
        
        # Call the base class reject
        super().reject()
    
    def closeEvent(self, event):
        """Handle window close event"""
        if self.runnable:
            self.runnable.stop()
        super().closeEvent(event)
