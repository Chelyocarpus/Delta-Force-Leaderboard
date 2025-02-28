import os
import sys
import json
import tempfile
import subprocess
import platform
import shutil
import time
import requests
from zipfile import ZipFile
from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtCore import QThread, pyqtSignal, QObject
from src.utils.constants import ROOT_DIR

class DownloadProgressSignals(QObject):
    """Signals for the download progress."""
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

class UpdateDownloader(QThread):
    """Thread for downloading and installing updates."""
    def __init__(self, download_url, parent=None):
        super().__init__(parent)
        self.download_url = download_url
        self.signals = DownloadProgressSignals()
        self.temp_dir = tempfile.mkdtemp()
        self.is_cancelled = False
        self.cache_dir = os.path.join(ROOT_DIR, "cache")
        self.download_cache_dir = os.path.join(self.cache_dir, "downloads")
        self.cache_file = os.path.join(self.cache_dir, "update_cache.json")

    def run(self):
        """Run the download and installation process."""
        try:
            # Ensure cache directories exist
            os.makedirs(self.download_cache_dir, exist_ok=True)
            
            # Get the asset URL by checking cache first
            asset_url = self._get_download_url_from_cache() or self.download_url
            
            # Generate a unique filename for this version
            download_filename = self._get_filename_from_url(asset_url)
            cached_zip_path = os.path.join(self.download_cache_dir, download_filename)
            zip_path = os.path.join(self.temp_dir, "update.zip")
            
            # Check if we already have this version downloaded
            if os.path.exists(cached_zip_path):
                # Copy from cache rather than re-downloading
                self.signals.progress.emit(10)  # Show some progress
                shutil.copy2(cached_zip_path, zip_path)
                self.signals.progress.emit(100)  # Complete the progress
            else:
                # Download the update
                self._download_file(asset_url, zip_path)
                
                if self.is_cancelled:
                    return
                
                # Cache the downloaded file for future use
                try:
                    shutil.copy2(zip_path, cached_zip_path)
                except Exception as e:
                    print(f"Failed to cache downloaded file: {e}")
            
            if self.is_cancelled:
                return
                
            # Extract the update
            self._extract_update(zip_path)
            
            if self.is_cancelled:
                return
                
            # Prepare for installation
            install_script = self._prepare_installation()
            
            # Signal completion
            self.signals.finished.emit(install_script)
            
        except Exception as e:
            self.signals.error.emit(f"Update failed: {str(e)}")
            # Clean up temp files
            self._cleanup()
    
    def _get_download_url_from_cache(self):
        """Try to get direct download URL from cache to avoid API calls."""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r') as f:
                    cache_data = json.load(f)
                
                # If we have the full API response in cache, use it to get asset URLs
                if 'full_api_response' in cache_data:
                    response_data = cache_data['full_api_response']
                    assets = response_data.get('assets', [])
                    
                    if assets:
                        # Find the .zip asset
                        for asset in assets:
                            if asset['name'].endswith('.zip'):
                                return asset['browser_download_url']
                    
                    # If no asset was found but we have a tag name, use source download
                    tag = response_data.get('tag_name', 'latest')
                    if 'url' in response_data:
                        html_url = response_data.get('html_url', '')
                        if html_url:
                            parts = html_url.split('/')
                            if len(parts) >= 5:  # Minimum to extract owner/repo
                                repo_owner = parts[3]
                                repo_name = parts[4]
                                return f"https://github.com/{repo_owner}/{repo_name}/archive/{tag}.zip"
                                
            # If we got here, we couldn't find a URL in the cache
            return None
            
        except Exception as e:
            print(f"Error reading download URL from cache: {e}")
            return None

    def _get_filename_from_url(self, url):
        """Generate a unique filename for caching the download."""
        # Extract the last part of the URL as filename
        filename = url.split('/')[-1]
        
        # If it doesn't end with .zip, add a hash of the URL to ensure uniqueness
        if not filename.endswith('.zip'):
            import hashlib
            url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
            filename = f"{url_hash}_{filename}.zip"
            
        return filename

    def _download_file(self, url, destination):
        """Download file with progress updates."""
        try:
            response = requests.get(url, stream=True, timeout=60)
            response.raise_for_status()
            
            total_size = int(response.headers.get('content-length', 0))
            block_size = 8192
            downloaded = 0
            
            with open(destination, 'wb') as f:
                for chunk in response.iter_content(chunk_size=block_size):
                    if self.is_cancelled:
                        return
                        
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        progress = int((downloaded / total_size) * 100) if total_size > 0 else -1
                        self.signals.progress.emit(progress)
        
        except Exception as e:
            self.signals.error.emit(f"Download failed: {str(e)}")
            raise

    # The rest of the methods remain unchanged
    def _extract_update(self, zip_path):
        """Extract the downloaded zip file."""
        try:
            with ZipFile(zip_path, 'r') as zip_ref:
                # Get the top-level directory in the zip
                top_dirs = {item.split('/')[0] for item in zip_ref.namelist() if '/' in item}
                
                # Extract to temp directory
                zip_ref.extractall(self.temp_dir)
                
                # Check for a single top-level directory (typical GitHub release format)
                if len(top_dirs) == 1:
                    self.extracted_dir = os.path.join(self.temp_dir, list(top_dirs)[0])
                else:
                    self.extracted_dir = self.temp_dir
                    
        except Exception as e:
            self.signals.error.emit(f"Extraction failed: {str(e)}")
            raise

    def _prepare_installation(self):
        """Prepare the installation script based on platform."""
        try:
            current_exe = os.path.abspath(sys.argv[0])
            app_dir = os.path.dirname(current_exe)
            
            # Create platform-specific installation script
            if platform.system() == "Windows":
                install_script = os.path.join(self.temp_dir, "install_update.bat")
                with open(install_script, 'w') as f:
                    f.write(f'@echo off\n')
                    f.write(f'echo Waiting for application to close...\n')
                    f.write(f'ping 127.0.0.1 -n 3 > nul\n')  # Wait 3 seconds
                    f.write(f'echo Installing update...\n')
                    
                    # Copy all files from extracted directory to app directory
                    f.write(f'xcopy /E /Y "{self.extracted_dir}\\*" "{app_dir}\\"\n')
                    
                    # Restart the application
                    f.write(f'echo Update complete, restarting application...\n')
                    f.write(f'start "" "{current_exe}"\n')
                    f.write(f'exit\n')
            
            elif platform.system() == "Darwin":  # macOS
                install_script = os.path.join(self.temp_dir, "install_update.sh")
                with open(install_script, 'w') as f:
                    f.write(f'#!/bin/bash\n')
                    f.write(f'echo "Waiting for application to close..."\n')
                    f.write(f'sleep 3\n')
                    f.write(f'echo "Installing update..."\n')
                    
                    # Copy all files from extracted directory to app directory
                    f.write(f'cp -R "{self.extracted_dir}/"* "{app_dir}/"\n')
                    
                    # Make the application executable
                    f.write(f'chmod +x "{current_exe}"\n')
                    
                    # Restart the application
                    f.write(f'echo "Update complete, restarting application..."\n')
                    f.write(f'open "{current_exe}"\n')
                
                # Make the script executable
                os.chmod(install_script, 0o755)
            
            else:  # Linux
                install_script = os.path.join(self.temp_dir, "install_update.sh")
                with open(install_script, 'w') as f:
                    f.write(f'#!/bin/bash\n')
                    f.write(f'echo "Waiting for application to close..."\n')
                    f.write(f'sleep 3\n')
                    f.write(f'echo "Installing update..."\n')
                    
                    # Copy all files from extracted directory to app directory
                    f.write(f'cp -R "{self.extracted_dir}/"* "{app_dir}/"\n')
                    
                    # Make the application executable
                    f.write(f'chmod +x "{current_exe}"\n')
                    
                    # Restart the application
                    f.write(f'echo "Update complete, restarting application..."\n')
                    f.write(f'"{current_exe}" &\n')
                
                # Make the script executable
                os.chmod(install_script, 0o755)
            
            return install_script
        
        except Exception as e:
            self.signals.error.emit(f"Failed to prepare installation: {str(e)}")
            raise

    def _cleanup(self):
        """Clean up temporary files."""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir, ignore_errors=True)
        except:
            pass  # Ignore cleanup errors

    def cancel(self):
        """Cancel the download operation."""
        self.is_cancelled = True
