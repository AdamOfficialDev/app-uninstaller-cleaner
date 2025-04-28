#!/usr/bin/env python3
import os
import sys
import shutil
import winreg
import subprocess
import logging
import argparse
from pathlib import Path
import ctypes
import json
import re
from typing import List, Dict, Optional, Tuple, Set
import time

# Check if running with admin privileges
def is_admin() -> bool:
    try:
        return ctypes.windll.shell32.IsUserAnAdmin() != 0
    except:
        return False

# Request admin privileges if needed
def request_admin():
    if not is_admin():
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit(0)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("uninstaller_log.txt"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Function to get list of all installed applications
def get_installed_applications() -> List[Dict]:
    """Get a list of all installed applications from the registry."""
    applications = []
    registry_locations = [
        winreg.HKEY_CURRENT_USER,
        winreg.HKEY_LOCAL_MACHINE
    ]
    registry_paths = [
        r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
        r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall"
    ]
    
    logger.info("Scanning registry for installed applications...")
    
    for hkey in registry_locations:
        for reg_path in registry_paths:
            try:
                logger.debug(f"Scanning {reg_path} in {'HKEY_CURRENT_USER' if hkey == winreg.HKEY_CURRENT_USER else 'HKEY_LOCAL_MACHINE'}...")
                with winreg.OpenKey(hkey, reg_path) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                try:
                                    display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                    logger.debug(f"Found: {display_name}")
                                    
                                    # Skip entries that look like Windows components or updates
                                    if ("KB" in display_name and any(x in display_name for x in ["Update", "Security Update", "Hotfix"])) or \
                                       any(x in display_name for x in ["Security Update for", "Update for"]):
                                        continue
                                    
                                    app_info = {
                                        "DisplayName": display_name,
                                        "Registry": f"{hkey}\\{reg_path}\\{subkey_name}"
                                    }
                                    
                                    # Get other useful information
                                    for value_name in ["UninstallString", "InstallLocation", "Publisher", "DisplayVersion"]:
                                        try:
                                            app_info[value_name] = winreg.QueryValueEx(subkey, value_name)[0]
                                        except:
                                            pass
                                            
                                    applications.append(app_info)
                                except (WindowsError, TypeError, ValueError) as e:
                                    pass
                        except WindowsError as e:
                            continue
            except WindowsError as e:
                logger.warning(f"Error accessing {reg_path}: {e}")
                continue
    
    logger.info(f"Found {len(applications)} applications before filtering.")
    
    # Remove duplicates (same DisplayName) and sort by DisplayName
    unique_apps = {}
    for app in applications:
        if app["DisplayName"] not in unique_apps:
            unique_apps[app["DisplayName"]] = app
    
    sorted_apps = sorted(unique_apps.values(), key=lambda x: x["DisplayName"].lower())
    logger.info(f"Found {len(sorted_apps)} unique applications after filtering.")
    
    return sorted_apps

class AppUninstaller:
    def __init__(self, app_name: str, thorough: bool = False, dry_run: bool = False, backup: bool = True):
        self.app_name = app_name
        self.thorough = thorough  # Deep cleaning mode
        self.dry_run = dry_run    # Preview mode without actually deleting
        self.backup = backup      # Create backups of registry and files before deletion
        self.backup_dir = Path("./backups") / f"{app_name}_{time.strftime('%Y%m%d_%H%M%S')}"
        self.registry_locations = [
            winreg.HKEY_CURRENT_USER,
            winreg.HKEY_LOCAL_MACHINE,
            winreg.HKEY_CLASSES_ROOT
        ]
        self.registry_paths = [
            f"SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Uninstall",
            f"SOFTWARE\\WOW6432Node\\Microsoft\\Windows\\CurrentVersion\\Uninstall"
        ]
        self.common_data_locations = [
            Path(os.environ["APPDATA"]),
            Path(os.environ["LOCALAPPDATA"]),
            Path(os.environ["ProgramData"]),
            Path(os.environ["ProgramFiles"]),
            Path(os.environ["ProgramFiles(x86)"]),
            Path("C:/Users") / os.environ["USERNAME"] / "AppData/Local/Temp",
            Path("C:/Windows/Temp")
        ]
        
    def find_uninstall_string(self) -> List[Dict]:
        """Find uninstall strings from registry for the application."""
        uninstall_entries = []
        
        for hkey in self.registry_locations[:2]:  # Only search HKCU and HKLM
            for reg_path in self.registry_paths:
                try:
                    with winreg.OpenKey(hkey, reg_path) as key:
                        for i in range(winreg.QueryInfoKey(key)[0]):
                            try:
                                subkey_name = winreg.EnumKey(key, i)
                                with winreg.OpenKey(key, subkey_name) as subkey:
                                    try:
                                        display_name = winreg.QueryValueEx(subkey, "DisplayName")[0]
                                        # Case-insensitive partial match
                                        if self.app_name.lower() in display_name.lower():
                                            entry = {
                                                "DisplayName": display_name,
                                                "Registry": f"{hkey}\\{reg_path}\\{subkey_name}"
                                            }
                                            
                                            # Try to get the uninstall string
                                            try:
                                                entry["UninstallString"] = winreg.QueryValueEx(subkey, "UninstallString")[0]
                                            except:
                                                entry["UninstallString"] = None
                                                
                                            # Try to get other useful data
                                            for value_name in ["InstallLocation", "Publisher", "DisplayVersion"]:
                                                try:
                                                    entry[value_name] = winreg.QueryValueEx(subkey, value_name)[0]
                                                except:
                                                    pass
                                                    
                                            uninstall_entries.append(entry)
                                    except:
                                        pass
                            except:
                                continue
                except:
                    continue
        
        return uninstall_entries
    
    def run_uninstaller(self, uninstall_string: str) -> bool:
        """Execute the uninstaller program."""
        if self.dry_run:
            logger.info(f"DRY RUN: Would execute uninstaller: {uninstall_string}")
            return True
            
        logger.info(f"Executing uninstaller: {uninstall_string}")
        
        # Handle different uninstaller formats
        if uninstall_string.startswith('"'):
            # Format: "C:\path\to\uninstaller.exe" /arguments
            parts = uninstall_string.split('" ', 1)
            program = parts[0].strip('"')
            args = parts[1] if len(parts) > 1 else ""
            
            # Add silent flags if not present
            if "/S" not in args and "/SILENT" not in args and "/VERYSILENT" not in args and "/quiet" not in args:
                args += " /S"
                
            try:
                if args:
                    result = subprocess.run([program, args], capture_output=True, text=True)
                else:
                    result = subprocess.run([program], capture_output=True, text=True)
                    
                logger.info(f"Uninstaller exit code: {result.returncode}")
                if result.stdout:
                    logger.debug(f"Uninstaller output: {result.stdout}")
                if result.stderr:
                    logger.warning(f"Uninstaller error: {result.stderr}")
                    
                return result.returncode == 0
            except Exception as e:
                logger.error(f"Failed to run uninstaller: {e}")
                return False
        else:
            # Format: C:\path\to\uninstaller.exe /arguments
            try:
                result = subprocess.run(uninstall_string, shell=True, capture_output=True, text=True)
                logger.info(f"Uninstaller exit code: {result.returncode}")
                return result.returncode == 0
            except Exception as e:
                logger.error(f"Failed to run uninstaller: {e}")
                return False
    
    def backup_registry_key(self, key_path: str) -> bool:
        """Backup a registry key to a file."""
        if not self.backup:
            return True
            
        # Create the backup directory if it doesn't exist
        os.makedirs(self.backup_dir / "registry", exist_ok=True)
        
        # Generate a safe filename from the registry path
        key_filename = key_path.replace("\\", "_").replace("/", "_") + ".reg"
        backup_file = self.backup_dir / "registry" / key_filename
        
        if self.dry_run:
            logger.info(f"DRY RUN: Would backup registry key {key_path} to {backup_file}")
            return True
            
        try:
            # Use reg export to backup the key
            cmd = f'reg export "{key_path}" "{backup_file}" /y'
            result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                logger.info(f"Successfully backed up registry key to {backup_file}")
                return True
            else:
                logger.warning(f"Failed to backup registry key {key_path}: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Error backing up registry key {key_path}: {e}")
            return False
    
    def backup_file_or_directory(self, path: Path) -> bool:
        """Backup a file or directory before deletion."""
        if not self.backup or not path.exists():
            return True
            
        # Create the backup directory if it doesn't exist
        backup_path = self.backup_dir / "files" / path.relative_to(path.anchor)
        os.makedirs(backup_path.parent, exist_ok=True)
        
        if self.dry_run:
            logger.info(f"DRY RUN: Would backup {path} to {backup_path}")
            return True
            
        try:
            if path.is_file():
                shutil.copy2(path, backup_path)
            else:
                shutil.copytree(path, backup_path)
                
            logger.info(f"Successfully backed up {path} to {backup_path}")
            return True
        except Exception as e:
            logger.error(f"Error backing up {path}: {e}")
            return False
    
    def remove_registry_entries(self, entries: List[Dict]) -> int:
        """Remove registry entries related to the application."""
        count = 0
        
        for entry in entries:
            reg_path = entry["Registry"]
            
            # Backup the registry key before deletion
            if self.backup:
                self.backup_registry_key(reg_path)
                
            if self.dry_run:
                logger.info(f"DRY RUN: Would delete registry key: {reg_path}")
                count += 1
                continue
                
            try:
                # Parse the registry path to get the root key and subkey path
                parts = reg_path.split("\\", 1)
                if len(parts) != 2:
                    logger.warning(f"Invalid registry path format: {reg_path}")
                    continue
                    
                root_str, subkey = parts
                
                # Convert string representation to actual HKEY constant
                root_key = None
                if "HKEY_CURRENT_USER" in root_str:
                    root_key = winreg.HKEY_CURRENT_USER
                elif "HKEY_LOCAL_MACHINE" in root_str:
                    root_key = winreg.HKEY_LOCAL_MACHINE
                elif "HKEY_CLASSES_ROOT" in root_str:
                    root_key = winreg.HKEY_CLASSES_ROOT
                else:
                    logger.warning(f"Unsupported registry root key: {root_str}")
                    continue
                
                # Use reg delete command to remove the key
                cmd = f'reg delete "{reg_path}" /f'
                result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                
                if result.returncode == 0:
                    logger.info(f"Successfully deleted registry key: {reg_path}")
                    count += 1
                else:
                    logger.warning(f"Failed to delete registry key {reg_path}: {result.stderr}")
            except Exception as e:
                logger.error(f"Error deleting registry key {reg_path}: {e}")
                
        return count
    
    def find_app_directories(self) -> List[Path]:
        """Find directories related to the application."""
        app_dirs = []
        pattern = re.compile(rf"{re.escape(self.app_name)}", re.IGNORECASE)
        
        for location in self.common_data_locations:
            if not location.exists():
                continue
                
            for path in location.glob("*"):
                if pattern.search(path.name) and path.is_dir():
                    app_dirs.append(path)
                    
        return app_dirs
    
    def find_app_files(self) -> List[Path]:
        """Find files related to the application."""
        app_files = []
        pattern = re.compile(rf"{re.escape(self.app_name)}", re.IGNORECASE)
        
        for location in self.common_data_locations:
            if not location.exists():
                continue
                
            for path in location.rglob("*"):
                if pattern.search(path.name) and path.is_file():
                    app_files.append(path)
                    
        return app_files
    
    def remove_directories(self, directories: List[Path]) -> int:
        """Remove directories related to the application."""
        count = 0
        
        for directory in directories:
            if not directory.exists():
                continue
                
            # Backup directory before deletion
            if self.backup:
                self.backup_file_or_directory(directory)
                
            if self.dry_run:
                logger.info(f"DRY RUN: Would remove directory: {directory}")
                count += 1
                continue
                
            try:
                shutil.rmtree(directory)
                logger.info(f"Successfully removed directory: {directory}")
                count += 1
            except Exception as e:
                logger.error(f"Error removing directory {directory}: {e}")
                
        return count
    
    def remove_files(self, files: List[Path]) -> int:
        """Remove files related to the application."""
        count = 0
        
        for file_path in files:
            if not file_path.exists():
                continue
                
            # Backup file before deletion
            if self.backup:
                self.backup_file_or_directory(file_path)
                
            if self.dry_run:
                logger.info(f"DRY RUN: Would remove file: {file_path}")
                count += 1
                continue
                
            try:
                file_path.unlink()
                logger.info(f"Successfully removed file: {file_path}")
                count += 1
            except Exception as e:
                logger.error(f"Error removing file {file_path}: {e}")
                
        return count
    
    def clean_registry(self) -> int:
        """Clean registry entries that might contain references to the app."""
        count = 0
        pattern = re.compile(rf"{re.escape(self.app_name)}", re.IGNORECASE)
        
        if not self.thorough:
            return 0
            
        # Additional registry locations to check for thorough cleaning
        locations = [
            (winreg.HKEY_CURRENT_USER, "Software"),
            (winreg.HKEY_LOCAL_MACHINE, "Software"),
            (winreg.HKEY_CURRENT_USER, "Software\\Classes"),
            (winreg.HKEY_LOCAL_MACHINE, "Software\\Classes")
        ]
        
        for hkey, base_path in locations:
            try:
                with winreg.OpenKey(hkey, base_path) as key:
                    self._scan_registry_recursively(hkey, base_path, pattern, depth=0)
            except Exception as e:
                logger.debug(f"Error accessing registry key {hkey}\\{base_path}: {e}")
                
        return count
    
    def _scan_registry_recursively(self, hkey, path, pattern, depth=0, max_depth=2):
        """Scan registry recursively for app references."""
        if depth > max_depth:
            return 0
            
        count = 0
        
        try:
            with winreg.OpenKey(hkey, path) as key:
                # Check if the current key name matches the pattern
                if pattern.search(path.split("\\")[-1]):
                    # Found a matching key
                    full_path = f"{hkey}\\{path}"
                    
                    # Backup the registry key before deletion
                    if self.backup:
                        self.backup_registry_key(full_path)
                        
                    if self.dry_run:
                        logger.info(f"DRY RUN: Would delete registry key (deep scan): {full_path}")
                        return 1
                        
                    try:
                        cmd = f'reg delete "{full_path}" /f'
                        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
                        
                        if result.returncode == 0:
                            logger.info(f"Successfully deleted registry key (deep scan): {full_path}")
                            return 1
                        else:
                            logger.warning(f"Failed to delete registry key {full_path}: {result.stderr}")
                    except Exception as e:
                        logger.error(f"Error deleting registry key {full_path}: {e}")
                
                # Enumerate subkeys
                subkey_count = winreg.QueryInfoKey(key)[0]
                for i in range(subkey_count):
                    try:
                        subkey_name = winreg.EnumKey(key, i)
                        subpath = f"{path}\\{subkey_name}"
                        count += self._scan_registry_recursively(hkey, subpath, pattern, depth + 1, max_depth)
                    except WindowsError:
                        continue
        except Exception as e:
            logger.debug(f"Error accessing registry key {hkey}\\{path}: {e}")
            
        return count
    
    def uninstall(self) -> Dict:
        """Perform the complete uninstallation process."""
        results = {
            "registry_entries_removed": 0,
            "directories_removed": 0,
            "files_removed": 0,
            "uninstaller_executed": False
        }
        
        # Step 1: Find uninstall entries in registry
        logger.info(f"Searching for {self.app_name} in Windows registry...")
        uninstall_entries = self.find_uninstall_string()
        
        if not uninstall_entries:
            logger.warning(f"No uninstall entries found for {self.app_name}")
        else:
            logger.info(f"Found {len(uninstall_entries)} uninstall entries")
            
            # Step 2: Run the uninstaller if found
            for entry in uninstall_entries:
                logger.info(f"Found application: {entry.get('DisplayName', 'Unknown')}")
                
                if "UninstallString" in entry and entry["UninstallString"]:
                    if self.run_uninstaller(entry["UninstallString"]):
                        results["uninstaller_executed"] = True
                        
        # Step 3: Remove registry entries
        if uninstall_entries:
            results["registry_entries_removed"] = self.remove_registry_entries(uninstall_entries)
            
        # Step 4: Find and remove application directories
        logger.info(f"Searching for {self.app_name} directories...")
        app_dirs = self.find_app_directories()
        
        if app_dirs:
            logger.info(f"Found {len(app_dirs)} directories")
            results["directories_removed"] = self.remove_directories(app_dirs)
        else:
            logger.info(f"No directories found for {self.app_name}")
            
        # Step 5: Find and remove application files
        if self.thorough:
            logger.info(f"Searching for {self.app_name} files (thorough mode)...")
            app_files = self.find_app_files()
            
            if app_files:
                logger.info(f"Found {len(app_files)} files")
                results["files_removed"] = self.remove_files(app_files)
            else:
                logger.info(f"No files found for {self.app_name}")
                
        # Step 6: Clean registry (thorough mode)
        if self.thorough:
            logger.info(f"Scanning registry for additional {self.app_name} entries (thorough mode)...")
            self.clean_registry()
            
        return results
    
    def generate_report(self, results: Dict) -> str:
        """Generate a detailed report of the uninstallation process."""
        report = [
            "==============================================",
            f"Uninstallation Report for {self.app_name}",
            "==============================================",
            f"Mode: {'Dry Run (No Changes Made)' if self.dry_run else 'Real Uninstallation'}",
            f"Thorough Cleaning: {'Enabled' if self.thorough else 'Disabled'}",
            f"Backup Created: {'Yes' if self.backup else 'No'}",
            "",
            "Results:",
            f"- Registry Entries Removed: {results['registry_entries_removed']}",
            f"- Directories Removed: {results['directories_removed']}",
            f"- Files Removed: {results['files_removed']}",
            f"- Official Uninstaller Executed: {'Yes' if results['uninstaller_executed'] else 'No'}",
            "",
            "Summary:",
        ]
        
        # Calculate total items removed
        total_removed = (results['registry_entries_removed'] + 
                          results['directories_removed'] + 
                          results['files_removed'])
        
        if total_removed > 0 or results['uninstaller_executed']:
            if self.dry_run:
                report.append(f"Would have removed {total_removed} items related to {self.app_name}")
            else:
                report.append(f"Successfully removed {total_removed} items related to {self.app_name}")
                
            if results['uninstaller_executed']:
                report.append("Successfully executed the application's official uninstaller")
        else:
            report.append(f"No items related to {self.app_name} were found or removed")
            
        report.extend([
            "",
            "==============================================",
            f"Log file: {os.path.abspath('uninstaller_log.txt')}",
            "==============================================",
        ])
        
        if self.backup:
            report.extend([
                f"Backup location: {os.path.abspath(str(self.backup_dir))}",
                "==============================================",
            ])
            
        return "\n".join(report)

def parse_arguments():
    parser = argparse.ArgumentParser(description="Advanced Application Uninstaller and Cleaner")
    parser.add_argument("--app-name", help="Name of the application to uninstall (optional)")
    parser.add_argument("--thorough", "-t", action="store_true", help="Enable thorough cleaning mode")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Preview changes without actually deleting anything")
    parser.add_argument("--no-backup", "-n", action="store_true", help="Disable backup creation")
    parser.add_argument("--list-only", "-l", action="store_true", help="Only list installed applications without uninstalling")
    return parser.parse_args()

def display_app_selection_menu(apps: List[Dict]) -> List[int]:
    """Display a menu of installed applications and return the selected indices."""
    # Sort applications by name
    sorted_apps = apps.copy()
    
    # Calculate the maximum width needed for each column
    max_name_len = max(len(app.get("DisplayName", "Unknown")[:50]) for app in sorted_apps)
    max_version_len = max(len(str(app.get("DisplayVersion", ""))) for app in sorted_apps)
    max_publisher_len = max(len(str(app.get("Publisher", ""))) for app in sorted_apps)
    
    # Make sure column widths are at least the header length
    max_name_len = max(max_name_len, len("Application Name"))
    max_version_len = max(max_version_len, len("Version"))
    max_publisher_len = max(max_publisher_len, len("Publisher"))
    
    # Limit column widths to reasonable values
    max_name_len = min(max_name_len, 50)
    max_version_len = min(max_version_len, 15)
    max_publisher_len = min(max_publisher_len, 30)
    
    # Terminal width check
    try:
        terminal_width = os.get_terminal_size().columns
    except:
        terminal_width = 100  # Default if we can't determine terminal width
    
    # Adjust column widths to fit terminal
    total_width = 4 + max_name_len + 2 + max_version_len + 2 + max_publisher_len
    if total_width > terminal_width:
        # Reduce columns proportionally
        excess = total_width - terminal_width + 5  # Add some margin
        name_ratio = max_name_len / total_width
        version_ratio = max_version_len / total_width
        publisher_ratio = max_publisher_len / total_width
        
        max_name_len = max(20, int(max_name_len - excess * name_ratio))
        max_version_len = max(8, int(max_version_len - excess * version_ratio))
        max_publisher_len = max(10, int(max_publisher_len - excess * publisher_ratio))
    
    # Display the header with pretty formatting
    header_line = f"{'#':<4} {'Application Name':<{max_name_len}} {'Version':<{max_version_len}} {'Publisher':<{max_publisher_len}}"
    separator = "-" * len(header_line)
    
    print("\n" + "=" * len(header_line))
    print("INSTALLED APPLICATIONS")
    print("=" * len(header_line))
    print(header_line)
    print(separator)
    
    # Display applications in groups of 20 with pagination
    page_size = 20
    total_pages = (len(sorted_apps) + page_size - 1) // page_size
    current_page = 1
    
    while True:
        # Calculate start and end indices for the current page
        start_idx = (current_page - 1) * page_size
        end_idx = min(start_idx + page_size, len(sorted_apps))
        
        # Display the applications for the current page
        for i in range(start_idx, end_idx):
            app = sorted_apps[i]
            
            # Truncate long values to fit columns
            name = (app.get("DisplayName", "Unknown")[:max_name_len-3] + "...") if len(app.get("DisplayName", "Unknown")) > max_name_len else app.get("DisplayName", "Unknown")
            version = (str(app.get("DisplayVersion", ""))[:max_version_len-3] + "...") if len(str(app.get("DisplayVersion", ""))) > max_version_len else app.get("DisplayVersion", "")
            publisher = (str(app.get("Publisher", ""))[:max_publisher_len-3] + "...") if len(str(app.get("Publisher", ""))) > max_publisher_len else app.get("Publisher", "")
            
            print(f"{i+1:<4} {name:<{max_name_len}} {version:<{max_version_len}} {publisher:<{max_publisher_len}}")
        
        # Show pagination info if needed
        if total_pages > 1:
            print(f"\nPage {current_page} of {total_pages}")
            print("(p: previous page, n: next page)")
        
        # Prompt for selection
        print("\nEnter the numbers of applications you want to uninstall (comma-separated) or 'all' for all apps:")
        print("Examples: 1,3,5 or 5-10 or all")
        print("Commands: q/quit/exit to exit, help for help")
        
        if total_pages > 1:
            selection = input(f"[Page {current_page}/{total_pages}] > ").strip().lower()
        else:
            selection = input("> ").strip().lower()
        
        # Handle pagination commands
        if selection == 'n' and current_page < total_pages:
            current_page += 1
            print("\n" * 5)  # Add some space before showing the next page
            continue
        elif selection == 'p' and current_page > 1:
            current_page -= 1
            print("\n" * 5)  # Add some space before showing the previous page
            continue
        elif selection == 'help':
            print("\nHelp:")
            print("  - Enter numbers separated by commas (e.g., 1,3,5)")
            print("  - Enter a range with a dash (e.g., 5-10)")
            print("  - Type 'all' to select all applications")
            print("  - Type 'n' for the next page, 'p' for the previous page")
            print("  - Type 'q', 'quit', or 'exit' to exit")
            print("  - Type 'help' to see this help message")
            continue
        elif selection in ('q', 'quit', 'exit'):
            return []
        elif selection == 'all':
            return list(range(len(sorted_apps)))
            
        # Parse user selection
        try:
            selected_indices = []
            parts = selection.split(',')
            
            for part in parts:
                part = part.strip()
                if '-' in part:
                    # Range selection (e.g., 5-9)
                    try:
                        start, end = map(int, part.split('-'))
                        if start < 1 or end > len(sorted_apps):
                            print(f"Invalid range {start}-{end}. Please use numbers between 1 and {len(sorted_apps)}.")
                            continue
                        selected_indices.extend(range(start-1, end))
                    except ValueError:
                        print(f"Invalid range format: {part}")
                else:
                    # Single number
                    try:
                        idx = int(part) - 1
                        if idx < 0 or idx >= len(sorted_apps):
                            print(f"Invalid selection {part}. Please use numbers between 1 and {len(sorted_apps)}.")
                            continue
                        selected_indices.append(idx)
                    except ValueError:
                        if part:  # Only show error if part is not empty
                            print(f"Invalid number: {part}")
            
            if not selected_indices:
                print("No valid selections. Please try again.")
                continue
                
            # Show a summary of selections and confirm
            print("\nYou selected:")
            for idx in selected_indices:
                print(f" - {sorted_apps[idx]['DisplayName']}")
            
            confirm = input("\nIs this correct? (y/n): ").strip().lower()
            if confirm == 'y':
                return selected_indices
            else:
                print("Selection cancelled. Please try again.")
                
        except ValueError:
            print("Invalid input. Please enter comma-separated numbers or 'all'.")

def main():
    # Check if running on Windows
    if not sys.platform.startswith('win'):
        logger.error("This script only supports Windows systems")
        sys.exit(1)
    
    # Keep running until user chooses to exit
    while True:
        # Parse command line arguments
        args = parse_arguments()
        
        # Skip admin check for list-only mode
        need_admin = not args.list_only
        
        # Request admin privileges if needed (except for list-only mode)
        if need_admin and not is_admin():
            logger.info("Requesting administrator privileges...")
            request_admin()
        
        # Print banner
        print("""
        ╔═══════════════════════════════════════════════╗
        ║                                               ║
        ║  Advanced Application Uninstaller and Cleaner ║
        ║                                               ║
        ╚═══════════════════════════════════════════════╝
        """)
        
        # Get list of installed applications
        print("\nScanning for installed applications...")
        installed_apps = get_installed_applications()
        
        if args.list_only:
            print(f"\nFound {len(installed_apps)} installed applications:")
            for i, app in enumerate(installed_apps, 1):
                print(f"{i:3}. {app.get('DisplayName', 'Unknown')} "
                    f"({app.get('DisplayVersion', 'Unknown Version')})")
            sys.exit(0)
        
        # If app_name is specified, use it; otherwise, show selection menu
        if args.app_name:
            app_names = [args.app_name]
            # Use command line arguments for mode options
            thorough = args.thorough
            dry_run = args.dry_run
            backup = not args.no_backup
        else:
            selected_indices = display_app_selection_menu(installed_apps)
            if not selected_indices:
                print("No applications selected. Exiting.")
                sys.exit(0)
                
            app_names = [installed_apps[i]["DisplayName"] for i in selected_indices]
            
            # Add interactive mode selection if no command line arguments were provided
            if not (args.thorough or args.dry_run or args.no_backup):
                print("\n=== Uninstallation Mode Selection ===")
                
                # Thorough mode selection
                while True:
                    thorough_choice = input("Enable thorough cleaning? (y/N): ").strip().lower()
                    if thorough_choice in ['y', 'yes', 'n', 'no', '']:
                        thorough = thorough_choice in ['y', 'yes']
                        break
                    print("Please enter 'y' or 'n'")
                
                # Dry run mode selection
                while True:
                    dry_run_choice = input("Simulation mode (no actual changes)? (y/N): ").strip().lower()
                    if dry_run_choice in ['y', 'yes', 'n', 'no', '']:
                        dry_run = dry_run_choice in ['y', 'yes']
                        break
                    print("Please enter 'y' or 'n'")
                
                # Backup mode selection
                while True:
                    backup_choice = input("Create backups before deletion? (Y/n): ").strip().lower()
                    if backup_choice in ['y', 'yes', 'n', 'no', '']:
                        backup = backup_choice in ['y', 'yes', '']  # Default is Yes
                        break
                    print("Please enter 'y' or 'n'")
                    
                print("\n=== Selected Options ===")
                print(f"Thorough Cleaning: {'Enabled' if thorough else 'Disabled'}")
                print(f"Simulation Mode: {'Enabled' if dry_run else 'Disabled'}")
                print(f"Create Backups: {'Enabled' if backup else 'Disabled'}")
            else:
                # Use command line arguments
                thorough = args.thorough
                dry_run = args.dry_run
                backup = not args.no_backup
        
        # Confirm with user
        if not dry_run:
            print(f"\nWarning: You are about to uninstall {len(app_names)} application(s):")
            for name in app_names:
                print(f" - {name}")
            print("This operation cannot be undone" + (" (although backups will be created)" if backup else ""))
            confirmation = input("\nDo you want to continue? (y/N): ")
            
            if confirmation.lower() != 'y':
                print("Operation cancelled")
                
                # Ask if user wants to start over or exit
                continue_choice = input("\nDo you want to start over? (Y/n): ").strip().lower()
                if continue_choice in ['n', 'no']:
                    sys.exit(0)
                # Continue the loop to start over
                continue
        
        # Process each selected application
        for app_name in app_names:
            print(f"\n{'='*60}")
            print(f"Processing: {app_name}")
            print(f"{'='*60}")
            
            # Initialize and run the uninstaller
            uninstaller = AppUninstaller(
                app_name,
                thorough=thorough,
                dry_run=dry_run,
                backup=backup
            )
            
            print(f"\nStarting uninstallation process for {app_name}...")
            print(f"Mode: {'Dry Run (no actual changes)' if dry_run else 'Real Uninstallation'}")
            print(f"Thorough cleaning: {'Enabled' if thorough else 'Disabled'}")
            print(f"Backup creation: {'Disabled' if not backup else 'Enabled'}")
            
            try:
                # Perform the uninstallation
                results = uninstaller.uninstall()
                
                # Generate and display the report
                report = uninstaller.generate_report(results)
                print("\n" + report)
                
                # Save the report to a file
                report_file = f"uninstall_report_{app_name.replace(' ', '_').replace('/', '_').replace('\\', '_')}.txt"
                with open(report_file, "w") as f:
                    f.write(report)
                    
                print(f"\nDetailed report saved to: {os.path.abspath(report_file)}")
                
            except KeyboardInterrupt:
                print("\nOperation cancelled by user")
                break
            except Exception as e:
                logger.error(f"An unexpected error occurred while uninstalling {app_name}: {e}")
                print(f"\nAn unexpected error occurred while uninstalling {app_name}: {e}")
                continue
        
        print("\nAll selected applications have been processed.")
        
        # Ask if user wants to uninstall more applications or exit
        continue_choice = input("\nDo you want to uninstall more applications? (y/N): ").strip().lower()
        if continue_choice not in ['y', 'yes']:
            print("Thank you for using Advanced Application Uninstaller and Cleaner!")
            break
            
        # If we get here, the loop will continue and start over

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nOperation cancelled by user. Exiting...")
        sys.exit(0) 