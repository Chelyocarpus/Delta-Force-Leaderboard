import os
from pathlib import Path
import json
from typing import List, Optional
from ...data.database import Database
from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QDialogButtonBox, QMessageBox, QCheckBox
)

class FileImportError(Exception):
    """Raised when there is an error importing a file"""
    pass

class DuplicateFileError(Exception):
    """Raised when attempting to import a duplicate file"""
    pass

class ImportManagerError(Exception):
    """Raised when there is an error in the ImportManager"""
    pass

class ImportManager:
    def __init__(self, watch_folder: str = "../../../components/workflow") -> None:
        self.base_path = Path(__file__).resolve().parent
        # Make watch_folder path absolute using project root
        project_root = self.base_path.parent.parent.parent
        self.watch_folder = (project_root / "components" / "workflow").resolve()
        self.imported_files_path = project_root / 'imported_files.json'
        
        print(f"Debug - Watch folder absolute path: {self.watch_folder}")
        print(f"Debug - Imported files path: {self.imported_files_path}")
        
        if not self.watch_folder.exists():
            os.makedirs(self.watch_folder)
            print(f"Debug - Created watch folder: {self.watch_folder}")
            
        self.imported_files = self._load_imported_files()
        self.db = Database()

    def _load_imported_files(self) -> List[str]:
        try:
            if self.imported_files_path.exists():
                imported = json.loads(self.imported_files_path.read_text())
                print(f"Debug - Loaded {len(imported)} imported files")
                return imported
        except json.JSONDecodeError:
            print("Warning: Corrupted imported_files.json, starting fresh")
        except (IOError, PermissionError, OSError) as e:
            print(f"Warning: Could not access imported_files.json: {e}")
        except Exception as e:
            print(f"Debug - Error loading imported files: {e}")
        return []

    def _save_imported_files(self) -> None:
        self.imported_files_path.write_text(json.dumps(self.imported_files))

    def _clean_imported_files(self) -> None:
        """Remove non-existent files from the imported files list"""
        cleaned_files = []
        for f in self.imported_files:
            try:
                if Path(f).exists():
                    cleaned_files.append(f)
            except (IOError, PermissionError, OSError) as e:
                print(f"Warning: Could not access file {f}: {e}")
        self.imported_files = cleaned_files
        self._save_imported_files()

    def _validate_imported_files(self) -> None:
        """Remove files from tracking that aren't actually in database"""
        if not self.imported_files:
            return
            
        valid_files = []
        for file_path in self.imported_files:
            try:
                file = Path(file_path)
                if file.exists():
                    # Check if file is actually in database
                    is_in_db = self.db.is_duplicate_file(str(file))
                    if is_in_db:
                        valid_files.append(file_path)
                    else:
                        print(f"Debug - Removing from tracking, not in database: {file.name}")
            except (IOError, PermissionError, OSError) as e:
                print(f"Warning: Could not access file {file_path}: {e}")
            
        self.imported_files = valid_files
        self._save_imported_files()

    def clear_tracking(self) -> None:
        """Clear the imported files tracking"""
        self.imported_files = []
        self._save_imported_files()

    def check_new_files(self) -> List[str]:
        """Only check for new files without importing"""
        if not self.watch_folder.exists():
            print(f"Debug - Watch folder missing: {self.watch_folder}")
            return []
            
        # Clean up tracking list and validate against database
        self._clean_imported_files()
        self._validate_imported_files()
        
        print(f"Debug - After validation, tracking {len(self.imported_files)} files")
        
        new_files = []
        try:
            all_csvs = list(self.watch_folder.glob('*.csv'))
            print(f"Debug - Found {len(all_csvs)} CSV files in folder")
            
            for file in all_csvs:
                try:
                    file_str = str(file.absolute())
                    print(f"Debug - Checking file: {file.name}")
                    
                    # Use thread-safe database access
                    with self.db.get_connection():
                        is_duplicate = self.db.is_duplicate_file(file_str)
                    
                    if not is_duplicate:
                        new_files.append((file.name, file_str))
                        print(f"Debug - New file found: {file.name}")
                    else:
                        print(f"Debug - File exists in database: {file.name}")
                        if file_str not in self.imported_files:
                            self.imported_files.append(file_str)
                            self._save_imported_files()
                except (IOError, PermissionError, OSError) as e:
                    print(f"Warning: Could not access file {file}: {e}")
                    continue
            
            print(f"Debug - Found {len(new_files)} new files to import")
            return new_files
            
        except Exception as e:
            print(f"Debug - Error scanning files: {e}")
            return []

    def import_file(self, file_path: str) -> None:
        """Import a single file and record it"""
        file = Path(file_path)
        if not file.exists():
            raise FileNotFoundError(f"File not found: {file_path}")
            
        try:
            # Use thread-safe import method
            if (success := self.db.import_csv_worker(str(file))):
                self.imported_files.append(str(file))
                self._save_imported_files()
            else:
                raise DuplicateFileError("This file has already been imported")
                
        except (IOError, PermissionError) as e:
            raise FileImportError(f"Error accessing {file.name}: {str(e)}") from e
        except Exception as e:  # Keep this to catch any database errors
            raise FileImportError(f"Error importing {file.name}: {str(e)}") from e

class ImportStartupDialog(QDialog):
    def __init__(self, files: List[str], parent: Optional[QDialog] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("New Files Found")
        self.setModal(True)
        self.resize(400, 300)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        label = QLabel("New match files found. Select files to import:")
        label.setWordWrap(True)
        layout.addWidget(label)
        
        self.list_widget = QListWidget()
        for file in files:
            item = QListWidgetItem(self.list_widget)
            checkbox = QCheckBox(file)
            checkbox.setChecked(True)  # Set checkbox checked by default
            self.list_widget.addItem(item)
            self.list_widget.setItemWidget(item, checkbox)
        layout.addWidget(self.list_widget)
        
        # Add Select All / Deselect All buttons
        button_layout = QVBoxLayout()
        select_all_btn = QPushButton("Select All")
        select_all_btn.clicked.connect(self.select_all)
        deselect_all_btn = QPushButton("Deselect All")
        deselect_all_btn.clicked.connect(self.deselect_all)
        button_layout.addWidget(select_all_btn)
        button_layout.addWidget(deselect_all_btn)
        layout.addLayout(button_layout)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def get_selected_files(self) -> List[str]:
        """Return list of selected file names"""
        selected = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            checkbox = self.list_widget.itemWidget(item)
            if checkbox.isChecked():
                selected.append(checkbox.text())
        return selected

    def select_all(self) -> None:
        self._set_all_checked(True)

    def deselect_all(self) -> None:
        self._set_all_checked(False)

    def _set_all_checked(self, checked: bool) -> None:
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            checkbox = self.list_widget.itemWidget(item)
            checkbox.setChecked(checked)

def run_import_check() -> None:
    try:
        manager = ImportManager()
        new_files = manager.check_new_files()
        
        if new_files:
            dialog = ImportStartupDialog([f[0] for f in new_files])
            dialog.select_all()
            
            if dialog.exec_() == QDialog.Accepted:
                selected_names = dialog.get_selected_files()
                for filename, filepath in new_files:
                    if filename in selected_names:
                        try:
                            manager.import_file(filepath)
                            print(f"Successfully imported {filename}")
                        except (FileImportError, DuplicateFileError, FileNotFoundError) as e:
                            QMessageBox.warning(None, "Import Error", 
                                f"Failed to import {filename}\n\nError: {str(e)}")
    except (IOError, PermissionError) as e:
        QMessageBox.critical(None, "Critical Error",
            f"Failed to access required files:\n\n{str(e)}")
    except ImportManagerError as e:
        QMessageBox.critical(None, "Critical Error",
            f"Failed to initialize import system:\n\n{str(e)}")
