import json
import re
import os
import time
from packaging import version
from src.utils.constants import ROOT_DIR, APP_VERSION
from security import safe_requests

class UpdateChecker:
    def __init__(self, current_version, repo_owner="Chelyocarpus", repo_name="Delta-Force-Leaderboard"):
        # Make sure current_version is exactly the same as APP_VERSION
        self.current_version = APP_VERSION
        self.repo_owner = repo_owner
        self.repo_name = repo_name
        self.api_url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/releases/latest"
        self.cache_dir = os.path.join(ROOT_DIR, "cache")
        self.cache_file = os.path.join(self.cache_dir, "update_cache.json")
        self.cache_ttl = 3600  # Cache expiry in seconds (1 hour)
        
    def check_for_updates(self, force_check=False):
        """
        Check for updates from GitHub releases.
        
        Args:
            force_check (bool): If True, ignore cache and check GitHub directly
            
        Returns:
            tuple: (is_update_available, latest_version, download_url, release_notes)
        """
        try:
            # Try to use cached data first if not forcing a check
            if not force_check and (cached_data := self._get_cached_data()):
                return cached_data
            
            # If no cache or force check, get from GitHub API
            response = safe_requests.get(self.api_url, timeout=5)
            response.raise_for_status()
            
            release_data = json.loads(response.text)
            latest_version_tag = release_data.get("tag_name", "v0.0.0")
            
            # First compare versions as exact strings (accounting for whitespace)
            if self.current_version.strip() == latest_version_tag.strip():
                print(f"Exact version match: '{self.current_version}' == '{latest_version_tag}'")
                is_update_available = False
                
            else:
                # Clean version strings to ensure consistent format
                # Remove 'v' prefix, trim whitespace, and convert to lowercase
                clean_current = re.sub(r'^v', '', self.current_version).strip().lower()
                clean_latest = re.sub(r'^v', '', latest_version_tag).strip().lower()
                
                # Debug output with ASCII character codes to identify invisible characters
                print(f"Current version: '{self.current_version}' (cleaned: '{clean_current}'), ASCII: {[ord(c) for c in clean_current]}")
                print(f"Latest version: '{latest_version_tag}' (cleaned: '{clean_latest}'), ASCII: {[ord(c) for c in clean_latest]}")
                
                # Check exact string equality of cleaned versions
                if clean_current == clean_latest:
                    print("Cleaned versions are equal - no update needed")
                    is_update_available = False
                else:
                    # Since they're not equal strings, try proper version parsing
                    try:
                        current_parsed = version.parse(clean_current)
                        latest_parsed = version.parse(clean_latest)
                        
                        # Only consider it an update if latest is strictly greater than current
                        is_update_available = latest_parsed > current_parsed
                        print(f"Version comparison result: {is_update_available} (using packaging.version)")
                    except version.InvalidVersion as e:
                        print(f"Invalid version format: {e}")
                        # This is a last resort - we'll assume no update if the versions don't match
                        # but string comparison fails
                        is_update_available = False
                        print("Version comparison failed, assuming no update needed")
            
            # Final safety check
            if latest_version_tag == self.current_version:
                print("Final safety check - versions match exactly - forcing is_update_available to False")
                is_update_available = False
            
            # Prepare the result
            result = None
            if is_update_available:
                download_url = release_data.get("html_url", "")
                release_notes = release_data.get("body", "No release notes available")
                result = (True, latest_version_tag, download_url, release_notes)
            else:
                result = (False, latest_version_tag, "", "")
            
            # Save the results to cache
            self._cache_update_data(result, release_data)
            
            return result
            
        except Exception as e:
            print(f"Failed to check for updates: {e}")
            
            # If online check fails, try to use cache regardless of force_check
            if cached_data := self._get_cached_data():
                return cached_data
                
            return (False, "", "", f"Error checking for updates: {e}")

    def _get_cached_data(self):
        """
        Try to load and use cached update data
        
        Returns:
            tuple or None: Cached update data if valid, None otherwise
        """
        try:
            # Check if cache file exists
            if not os.path.exists(self.cache_file):
                return None
                
            # Read cache file
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
                
            # Check if cache is expired
            if time.time() - cache_data.get('timestamp', 0) > self.cache_ttl:
                return None
                
            # Return cached result
            return (
                cache_data.get('is_update_available', False), 
                cache_data.get('latest_version', ''), 
                cache_data.get('download_url', ''),
                cache_data.get('release_notes', '')
            )
                
        except Exception as e:
            print(f"Error reading update cache: {e}")
            return None
            
    def _cache_update_data(self, result, release_data):
        """
        Cache the update check results
        
        Args:
            result (tuple): The update check result
            release_data (dict): The full GitHub API response
        """
        try:
            # Ensure cache directory exists
            os.makedirs(self.cache_dir, exist_ok=True)
            
            # Unpack result tuple
            is_update_available, latest_version, download_url, release_notes = result
            
            # Create cache data
            cache_data = {
                'timestamp': time.time(),
                'is_update_available': is_update_available,
                'latest_version': latest_version,
                'download_url': download_url,
                'release_notes': release_notes,
                'full_api_response': release_data  # Store full data for future use
            }
            
            # Write to cache file
            with open(self.cache_file, 'w') as f:
                json.dump(cache_data, f)
                
        except Exception as e:
            print(f"Error writing update cache: {e}")
