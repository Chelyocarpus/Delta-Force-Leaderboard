from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar, QDialogButtonBox, 
    QListWidget, QListWidgetItem, QApplication
)
from PyQt5.QtGui import QFont, QIcon, QColor
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QObject
import os
import time

class ImportWorker(QObject):
    """Worker thread for importing CSV files"""
    progress = pyqtSignal(int, int)  # (current_file_index, total_files)
    file_status = pyqtSignal(str, bool, str)  # (filename, success, message)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, db, files):
        super().__init__()
        self.db = db
        self.files = files
        self.is_running = True

    def process(self):
        total_files = len(self.files)
        
        for i, file_path in enumerate(self.files):
            if not self.is_running:
                break
                
            # Report progress
            self.progress.emit(i, total_files)
            
            # Update UI before processing
            file_name = os.path.basename(file_path)
            QApplication.processEvents()
            
            try:
                # Use the thread-safe import method
                success = self.db.import_csv_worker(file_path)
                
                # Use different messages for duplicates vs successful imports
                if success:
                    self.file_status.emit(file_name, True, "Successfully imported")
                else:
                    self.file_status.emit(file_name, False, "Skipped duplicate file")
                    
                # Small delay to prevent UI from freezing and show progress
                time.sleep(0.1)
                
            except Exception as e:
                self.file_status.emit(file_name, False, f"Error: {str(e)}")
        
        self.finished.emit()

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
        self.thread = None
        self.worker = None
        
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
        
        # Set up and start the worker thread
        self.setup_worker_thread()
        
    def setup_worker_thread(self):
        """Set up and start the worker thread"""
        # Create worker thread
        self.thread = QThread()
        self.worker = ImportWorker(self.db, self.files)
        self.worker.moveToThread(self.thread)
        
        # Connect signals
        self.thread.started.connect(self.worker.process)
        self.worker.progress.connect(self.update_progress)
        self.worker.file_status.connect(self.update_file_status)
        self.worker.finished.connect(self.import_finished)
        self.worker.finished.connect(self.thread.quit)
        
        # Start the thread
        self.thread.start()
        
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
        
        # Clean up the thread and worker
        self.cleanup_thread()
        
    def cleanup_thread(self):
        """Clean up the thread safely"""
        if hasattr(self, 'worker') and self.worker:
            self.worker.is_running = False
            
        if hasattr(self, 'thread') and self.thread:
            if self.thread.isRunning():
                self.thread.quit()
                # Give it some time to quit
                self.thread.wait(500)
            
            # Don't deleteLater here since we want to verify the thread is done first
            
    def reject(self):
        """Handle dialog rejection (Cancel button)"""
        # Stop the import process
        if hasattr(self, 'worker') and self.worker:
            self.worker.stop()
        
        # Clean up and wait for the thread to finish
        self.cleanup_thread()
        
        # Call the base class reject
        super().reject()
    
    def closeEvent(self, event):
        """Handle window close event"""
        self.cleanup_thread()
        super().closeEvent(event)
        
    def __del__(self):
        """Destructor to ensure thread cleanup"""
        self.cleanup_thread()
