import os
import sys
import subprocess

def create_windows_shortcut(target_path, shortcut_path, description="Auraly", working_dir=None, icon_path=None):
    """Creates a native Windows .lnk shortcut using VBScript / WScript.Shell with custom ICO icon."""
    if working_dir is None:
        working_dir = os.path.dirname(target_path)
    
    vbs_script = f"""
    Set WshShell = CreateObject("WScript.Shell")
    Set shortcut = WshShell.CreateShortcut("{shortcut_path}")
    shortcut.TargetPath = "{target_path}"
    shortcut.WorkingDirectory = "{working_dir}"
    shortcut.Description = "{description}"
    """
    if icon_path and os.path.exists(icon_path):
        vbs_script += f'\nshortcut.IconLocation = "{icon_path}"'
    vbs_script += '\nshortcut.Save'

    temp_vbs = os.path.join(working_dir, "_temp_shortcut.vbs")
    with open(temp_vbs, "w") as f:
        f.write(vbs_script)

    subprocess.run(["cscript", "//Nologo", temp_vbs], check=True)
    if os.path.exists(temp_vbs):
        os.remove(temp_vbs)
    print(f"Created shortcut: {shortcut_path}")

def setup_all_shortcuts():
    desktop_dir = os.path.join(os.path.expanduser("~"), "Desktop")
    startup_dir = os.path.join(os.path.expanduser("~"), "AppData", "Roaming", "Microsoft", "Windows", "Start Menu", "Programs", "Startup")
    
    target_exe = r"D:\Auraly\Auraly.exe"
    icon_ico = r"D:\Auraly\app_icon.ico"
    
    # 1. Create Desktop Shortcut: Auraly.lnk
    desktop_lnk = os.path.join(desktop_dir, "Auraly.lnk")
    create_windows_shortcut(target_exe, desktop_lnk, "Auraly - Real-Time Taskbar Lyrics", r"D:\Auraly", icon_ico)
    
    # 2. Create Auto-Startup Shortcut: Auraly.lnk
    startup_lnk = os.path.join(startup_dir, "Auraly.lnk")
    create_windows_shortcut(target_exe, startup_lnk, "Auraly - Auto-Start on Boot", r"D:\Auraly", icon_ico)

if __name__ == "__main__":
    setup_all_shortcuts()
