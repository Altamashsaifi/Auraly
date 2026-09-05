<div align="center">
  <img src="logo.png" width="180" alt="Auraly Logo" />
  <h1>Auraly 🎵</h1>
  <p><b>A sleek, lightweight desktop lyrics overlay for Windows 10 & 11 that displays real-time synchronized music lyrics directly on your taskbar.</b></p>

  <a href="https://github.com/Altamashsaifi/Auraly/releases">
    <img src="https://img.shields.io/badge/Download-Latest%20Release-blue?style=for-the-badge&logo=windows&logoColor=white" alt="Download Latest Release" />
  </a>
</div>

<br />

---

## 🚀 Instant Download & Run (No Python Required)
You can directly download the pre-compiled application from the **[Releases Section](https://github.com/Altamashsaifi/Auraly/releases)**:

- 📦 **`Auraly-Portable.zip`** (*Recommended — Extract & double-click `Auraly.exe`*)
- 📥 **`Auraly.exe`** (*Standalone single executable*)

> [!TIP]
> **If Windows Defender Blocks Single `.exe`**:  
> Download **`Auraly-Portable.zip`** from Releases! Zip releases bypass Windows Defender false-positive packer warnings completely.

---

## ✨ Features
- **Taskbar Integration**: Clean, transparent overlay anchored seamlessly to your taskbar.
- **System Media Support (GSMTC)**: Automatically detects playing music from Spotify, Apple Music, YouTube (Chrome/Edge), Tidal, VLC, and Windows Media Player.
- **Live Synchronized Lyrics**: Fetches synchronized `.lrc` lyrics automatically via LRCLIB.
- **Customizable Appearance**: Soothing geometric typography, adjustable opacity, dark/light adaptation.
- **Low Footprint**: Ultra-lightweight background process.

## 📋 Requirements (Only for running from source)
- Windows 10 / Windows 11
- Python 3.10+ (Optional if using pre-built release)

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

## 📄 License
MIT
