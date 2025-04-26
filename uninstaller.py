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
    parser.add_argument("app_name", help="Name of the application to uninstall")
    parser.add_argument("--thorough", "-t", action="store_true", help="Enable thorough cleaning mode")
    parser.add_argument("--dry-run", "-d", action="store_true", help="Preview changes without actually deleting anything")
    parser.add_argument("--no-backup", "-n", action="store_true", help="Disable backup creation")
    return parser.parse_args()

def main():
    # Check if running on Windows
    if not sys.platform.startswith('win'):
        logger.error("This script only supports Windows systems")
        sys.exit(1)
        
    # Parse command line arguments
    args = parse_arguments()
    
    # Request admin privileges (required for many operations)
    request_admin()
    
    # Print banner
    print("""
    ╔═══════════════════════════════════════════════╗
    ║                                               ║
    ║  Advanced Application Uninstaller and Cleaner ║
    ║                                               ║
    ╚═══════════════════════════════════════════════╝
    """)
    
    # Confirm with user
    if not args.dry_run:
        print(f"\nWarning: You are about to uninstall {args.app_name} and remove associated data.")
        print("This operation cannot be undone" + (" (although backups will be created)" if not args.no_backup else ""))
        confirmation = input("\nDo you want to continue? (y/N): ")
        
        if confirmation.lower() != 'y':
            print("Operation cancelled")
            sys.exit(0)
    
    # Initialize and run the uninstaller
    uninstaller = AppUninstaller(
        args.app_name,
        thorough=args.thorough,
        dry_run=args.dry_run,
        backup=not args.no_backup
    )
    
    print(f"\nStarting uninstallation process for {args.app_name}...")
    print(f"Mode: {'Dry Run (no actual changes)' if args.dry_run else 'Real Uninstallation'}")
    print(f"Thorough cleaning: {'Enabled' if args.thorough else 'Disabled'}")
    print(f"Backup creation: {'Disabled' if args.no_backup else 'Enabled'}")
    
    try:
        # Perform the uninstallation
        results = uninstaller.uninstall()
        
        # Generate and display the report
        report = uninstaller.generate_report(results)
        print("\n" + report)
        
        # Save the report to a file
        report_file = f"uninstall_report_{args.app_name}.txt"
        with open(report_file, "w") as f:
            f.write(report)
            
        print(f"\nDetailed report saved to: {os.path.abspath(report_file)}")
        
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e}")
        print(f"\nAn unexpected error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 