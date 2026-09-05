<div align="center">
  <img src="logo.png" width="180" alt="Auraly Logo" />
  <h1>Auraly 🎵</h1>
  <p><b>A sleek, lightweight desktop lyrics overlay for Windows 10 & 11 that displays real-time synchronized music lyrics directly on your taskbar.</b></p>

  <a href="https://github.com/Altamashsaifi/Auraly/raw/main/Auraly.exe">
    <img src="https://img.shields.io/badge/Download-Auraly.exe-blue?style=for-the-badge&logo=windows&logoColor=white" alt="Download Auraly.exe" />
  </a>
</div>

<br />

---

## 🚀 Instant Download & Run (No Python Required)
You can directly download the pre-compiled executable and run it immediately:
- 📥 **[Download Auraly.exe](https://github.com/Altamashsaifi/Auraly/raw/main/Auraly.exe)** (Double-click to run!)

> [!NOTE]
> **Windows SmartScreen / Antivirus Warning?**  
> Because `Auraly.exe` is an open-source standalone binary compiled with PyInstaller and isn't signed with a paid digital certificate ($300+/year), Windows SmartScreen or Chrome may flag it as an "Unknown Publisher / Uncommonly downloaded" file. This is a standard false positive.  
> - **In Chrome / Edge**: Click `Keep` -> `Keep anyway`.  
> - **In Windows SmartScreen**: Click **"More info"** -> Click **"Run anyway"**.

## ✨ Features
- **Taskbar Integration**: Clean, transparent overlay anchored seamlessly to your taskbar.
- **System Media Support (GSMTC)**: Automatically detects playing music from Spotify, Apple Music, YouTube (Chrome/Edge), Tidal, VLC, and Windows Media Player.
- **Live Synchronized Lyrics**: Fetches synchronized `.lrc` lyrics automatically via LRCLIB.
- **Customizable Appearance**: Soothing geometric typography, adjustable opacity, dark/light adaptation.
- **Low Footprint**: Ultra-lightweight background process.

## 📋 Requirements (Only for running from source)
- Windows 10 / Windows 11
- Python 3.10+ (Optional if using `Auraly.exe`)

## 🛠️ Quick Start (Running from Source)

1. Clone this repository:
   ```bash
   git clone https://github.com/Altamashsaifi/Auraly.git
   cd Auraly
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python main.py
   ```

## 📦 Building Executable

To rebuild the standalone `.exe` using PyInstaller:
```bash
pyinstaller --noconfirm --onedir --windowed --icon=app_icon.ico --add-data "app_icon.ico;." --add-data "app_icon.png;." main.py
```

## 📄 License
MIT
