# 🧹 Advanced Application Uninstaller and Cleaner

<div align="center">

![GitHub license](https://img.shields.io/badge/license-MIT-blue.svg)
![Python Version](https://img.shields.io/badge/python-3.6%2B-brightgreen)
![Platform](https://img.shields.io/badge/platform-Windows-lightgrey)
![Status](https://img.shields.io/badge/status-active-success)

**A powerful tool for completely uninstalling Windows applications and cleaning up leftover data**

[Features](#-features) •
[Requirements](#-requirements) •
[Installation](#-installation) •
[Usage](#-usage) •
[Safety](#-safety-features) •
[How It Works](#-how-it-works) •
[Contributing](#-contributing)

<img src="https://i.imgur.com/5B1Cj1u.png" alt="Terminal App Preview" width="680"/>

</div>

---

## ✨ Features

- 🔍 **Auto-Detection**: Automatically detects all installed applications
- 📋 **Batch Uninstallation**: Remove multiple applications at once
- 🎛️ **Interactive Mode**: Choose uninstallation options interactively
- 🧹 **Thorough Cleaning**: Removes applications and all associated data
- 🗄️ **Registry Cleaning**: Scans and removes registry entries
- 📂 **File System Cleaning**: Locates and removes leftover files
- 💾 **Backup Creation**: Creates backups before deletion
- 🔬 **Dry Run Mode**: Preview changes without making modifications
- 📊 **Detailed Reporting**: Generates comprehensive reports
- 🔑 **Admin Mode**: Automatically requests necessary permissions

---

## 🔧 Requirements

- Windows operating system
- Python 3.6 or higher
- Administrator privileges

---

## 📥 Installation

No installation is required. Simply download the script and run it with Python.

```bash
git clone https://github.com/AdamOfficialDev/app-uninstaller-cleaner.git
cd app-uninstaller-cleaner
```

---

## 📖 Usage

### Basic Commands

```bash
# 🚀 Launch interactive mode to select and uninstall applications
python uninstaller.py

# 📋 List all installed applications without uninstalling
python uninstaller.py --list-only

# 🎯 Uninstall a specific application by name
python uninstaller.py --app-name "App Name"
```

### Command-line Options

| Option | Description |
|--------|-------------|
| `--app-name "App Name"` | Target a specific application |
| `--list-only` or `-l` | List applications only |
| `--thorough` or `-t` | Enable thorough cleaning mode |
| `--dry-run` or `-d` | Preview without making changes |
| `--no-backup` or `-n` | Disable automatic backups |

### Example Use Cases

<details>
<summary>👉 Click to expand examples</summary>

```bash
# Interactive selection menu
python uninstaller.py

# List installed applications
python uninstaller.py --list-only

# Basic uninstall by name
python uninstaller.py --app-name "Google Chrome"

# Thorough uninstallation with backups
python uninstaller.py --app-name "Adobe Photoshop" --thorough

# Preview what would be removed
python uninstaller.py --app-name "Microsoft Office" --dry-run

# Uninstall without backups
python uninstaller.py --app-name "Spotify" --no-backup

# Full thorough uninstallation without backups
python uninstaller.py --app-name "Dropbox" --thorough --no-backup
```
</details>

### Interactive Mode
When you run the tool in interactive mode, you'll be able to:
- Browse through a paginated list of applications
- Select multiple applications using comma-separated numbers
- Choose ranges of applications (e.g., 5-10)
- Configure uninstallation options with guided prompts

---

## 🔒 Safety Features

- **💾 Automatic Backups**: Registry keys and files are backed up before deletion
- **🔎 Simulation Mode**: Dry run mode to preview changes before making them
- **✅ Confirmation Prompts**: Multiple confirmations to prevent accidental deletions
- **⚠️ Error Handling**: Graceful error handling and detailed logging

---

## ⚙️ How It Works

1. **🔍 Application Detection**: Scans Windows registry for installed applications
2. **👆 User Selection**: Displays applications for selection with pagination
3. **⚙️ Mode Configuration**: Choose between thorough, dry-run, and backup options
4. **🔎 Registry Scanning**: Finds uninstall entries in the registry
5. **🚀 Uninstaller Execution**: Runs the application's official uninstaller
6. **🧹 Registry Cleaning**: Removes related registry entries
7. **📂 Directory Cleanup**: Identifies and removes application directories
8. **🔬 Deep Scan**: Performs thorough scanning for leftovers (optional)
9. **📊 Reporting**: Generates detailed reports of the process

<details>
<summary>🔄 Process Flow Diagram</summary>

```
┌─────────────────────┐     ┌─────────────────────┐     ┌────────────────────┐
│  Detect Apps        │────>│  Select Apps        │────>│  Choose Mode       │
└─────────────────────┘     └─────────────────────┘     └────────────────────┘
           │                                                      │
           │                                                      ▼
┌─────────────────────┐     ┌─────────────────────┐     ┌────────────────────┐
│  Generate Report    │<────│  Clean Up Files     │<────│  Run Uninstaller   │
└─────────────────────┘     └─────────────────────┘     └────────────────────┘
```
</details>

---

## ⚠️ Warning

Use this tool at your own risk. Always run with `--dry-run` first to preview changes. While the tool includes safety features like backups and simulation mode, improper use could potentially cause system issues.

---

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

---

<div align="center">
⭐ Don't forget to star this repository if you found it useful! ⭐
</div> 