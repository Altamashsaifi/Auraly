@echo off
title Auraly - Real-Time Taskbar Lyrics
cd /d "D:\Auraly"
if exist "Auraly.exe" (
    start "" "Auraly.exe"
) else (
    python main.py
)
exit
