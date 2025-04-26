# Advanced Application Uninstaller and Cleaner

A powerful tool for completely uninstalling Windows applications and cleaning up leftover data.

## Features

- **Thorough Uninstallation**: Removes applications and all associated data
- **Registry Cleaning**: Scans and removes registry entries related to the application
- **File System Cleaning**: Locates and removes leftover files and directories
- **Backup Creation**: Creates backups of registry keys and files before deletion
- **Dry Run Mode**: Preview changes without making any actual modifications
- **Detailed Reporting**: Generates comprehensive reports of the uninstallation process
- **Admin Mode**: Automatically requests necessary permissions

## Requirements

- Windows operating system
- Python 3.6 or higher
- Administrator privileges

## Installation

No installation is required. Simply download the script and run it with Python.

```bash
git clone https://github.com/AdamOfficialDev/app-uninstaller-cleaner.git
cd app-uninstaller-cleaner
```

## Usage

```bash
python uninstaller.py "App Name"
```

### Command-line Options

- `--thorough` or `-t`: Enable thorough cleaning mode (scans for all traces of the application)
- `--dry-run` or `-d`: Preview changes without actually deleting anything
- `--no-backup` or `-n`: Disable backup creation

### Examples

```bash
# Basic uninstallation
python uninstaller.py "Google Chrome"

# Thorough uninstallation with backups
python uninstaller.py "Adobe Photoshop" --thorough

# Preview what would be removed without making changes
python uninstaller.py "Microsoft Office" --dry-run

# Uninstall without creating backups
python uninstaller.py "Spotify" --no-backup

# Full thorough uninstallation without backups
python uninstaller.py "Dropbox" --thorough --no-backup
```

## How It Works

1. **Registry Scanning**: Searches the Windows registry for uninstall entries
2. **Uninstaller Execution**: Runs the application's official uninstaller if available
3. **Registry Cleaning**: Removes registry entries related to the application
4. **Directory Removal**: Identifies and removes application directories
5. **File Cleaning**: Locates and removes leftover files (in thorough mode)
6. **Deep Registry Scan**: Scans the registry for additional application references (in thorough mode)
7. **Reporting**: Generates a detailed report of the uninstallation process

## Safety Features

- **Backup Creation**: Creates backups of registry keys and files before deletion
- **Dry Run Mode**: Preview changes without making any actual modifications
- **Confirmation Prompt**: Requires user confirmation before proceeding with deletion
- **Error Handling**: Gracefully handles errors and provides detailed logging

## Warning

Use this tool at your own risk. While it includes safety features like backups and dry run mode, improper use could potentially cause system issues. Always run with `--dry-run` first to preview changes.

## License

MIT License

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. 