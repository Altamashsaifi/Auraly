import sys
import os
import socket
import threading
from typing import Optional, List

# Single Instance Socket Lock (Prevents duplicate instances)
SINGLE_INSTANCE_PORT = 54321
_instance_socket = None

def ensure_single_instance() -> bool:
    global _instance_socket
    try:
        _instance_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        _instance_socket.bind(("127.0.0.1", SINGLE_INSTANCE_PORT))
        _instance_socket.listen(1)
        return True
    except socket.error:
        print("[Auraly] Another instance is already running. Exiting cleanly.")
        return False

def get_asset_path(filename: str) -> str:
    """Resolves asset file path for both normal execution and PyInstaller frozen bundles."""
    if getattr(sys, 'frozen', False):
        base_dir = sys._MEIPASS
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))
    
    p1 = os.path.join(r"D:\Auraly", filename)
    if os.path.exists(p1):
        return p1

    p2 = os.path.join(base_dir, filename)
    if os.path.exists(p2):
        return p2

    return ""

from media_listener import MediaListener, MediaInfo
from lyrics_fetcher import LyricsFetcher
from lrc_parser import LyricLine

HAS_PYQT6 = False
try:
    from PyQt6.QtCore import Qt, QObject, pyqtSignal, QTimer
    from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QFont
    from PyQt6.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QInputDialog
    from taskbar_overlay import TaskbarOverlayWindow
    HAS_PYQT6 = True
except ImportError:
    pass

if not HAS_PYQT6:
    from taskbar_overlay_tk import TaskbarLyricsTkOverlay

class ControllerCore(QObject if HAS_PYQT6 else object):
    if HAS_PYQT6:
        media_changed_signal = pyqtSignal(object)
        lyrics_loaded_signal = pyqtSignal(object, object, bool)

    def __init__(self, overlay):
        if HAS_PYQT6:
            super().__init__()
        self.overlay = overlay
        self.current_song_key = ""
        self.cached_lyrics: List[LyricLine] = []
        self.is_synced = False
        self.current_info = MediaInfo()

        if HAS_PYQT6:
            self.media_changed_signal.connect(self._on_media_changed)
            self.lyrics_loaded_signal.connect(self._on_lyrics_loaded)
            if hasattr(self.overlay, 'refresh_requested_signal'):
                self.overlay.refresh_requested_signal.connect(self.force_refresh_lyrics)

        self.listener = MediaListener(callback=self._on_media_update, poll_interval=0.25)
        self.listener.start()

    def force_refresh_lyrics(self):
        """1-Click Refresh: Clears lyric cache and re-fetches fresh lyrics & position."""
        self.current_song_key = ""
        self.cached_lyrics = []
        self.is_synced = False
        self.overlay.set_fetching_state(True)
        if self.current_info and self.current_info.title:
            threading.Thread(
                target=self._fetch_lyrics_worker,
                args=(self.current_info.title, self.current_info.artist, self.current_info.duration),
                daemon=True
            ).start()

    def _on_media_update(self, info: MediaInfo):
        if HAS_PYQT6:
            self.media_changed_signal.emit(info)
        else:
            self._on_media_changed(info)

    def _on_media_changed(self, info: MediaInfo):
        song_key = f"{info.title}||{info.artist}"

        if song_key != self.current_song_key:
            self.current_song_key = song_key
            self.current_info = info
            if info.title:
                self.overlay.set_fetching_state(True)
                threading.Thread(
                    target=self._fetch_lyrics_worker,
                    args=(info.title, info.artist, info.duration),
                    daemon=True
                ).start()
            else:
                self.cached_lyrics = []
                self.is_synced = False
                self.overlay.update_media(info, [], False)
        else:
            # Same song key, but check if artist just got populated by Windows!
            if info.artist and not self.current_info.artist and not self.cached_lyrics:
                self.current_info = info
                self.overlay.set_fetching_state(True)
                threading.Thread(
                    target=self._fetch_lyrics_worker,
                    args=(info.title, info.artist, info.duration),
                    daemon=True
                ).start()
            else:
                self.current_info = info
                self.overlay.update_media(info, self.cached_lyrics, self.is_synced)

    def _fetch_lyrics_worker(self, title: str, artist: str, duration: float):
        result = LyricsFetcher.get_lyrics(title, artist, duration)
        synced = result.get("synced_lyrics", [])
        is_synced = result.get("is_synced", False)

        if HAS_PYQT6:
            self.lyrics_loaded_signal.emit(synced, result, is_synced)
        else:
            self._on_lyrics_loaded(synced, result, is_synced)

    def _on_lyrics_loaded(self, synced: List[LyricLine], result: dict, is_synced: bool):
        self.cached_lyrics = synced
        self.is_synced = is_synced
        self.overlay.update_media(self.current_info, self.cached_lyrics, self.is_synced)

    def stop(self):
        if hasattr(self, 'listener'):
            self.listener.stop()

def create_tray_icon(app: QApplication, overlay: TaskbarOverlayWindow, controller: ControllerCore) -> QSystemTrayIcon:
    """Creates a system tray icon for Auraly using transparent white quaver icon."""
    icon_path = get_asset_path("app_icon.png")

    if icon_path and os.path.exists(icon_path):
        icon = QIcon(icon_path)
    else:
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(255, 255, 255))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 28, 28)
        painter.end()
        icon = QIcon(pixmap)

    tray_icon = QSystemTrayIcon(icon, app)
    tray_icon.setToolTip("Auraly - Real-time Taskbar Lyrics")

    menu = QMenu()
    
    refresh_act = menu.addAction("Refresh / Resync Lyrics")
    refresh_act.triggered.connect(controller.force_refresh_lyrics)

    menu.addSeparator()

    show_hide_act = menu.addAction("Toggle Show/Hide")
    show_hide_act.triggered.connect(lambda: overlay.setVisible(not overlay.isVisible()))

    lock_act = menu.addAction("Unlock/Lock Position")
    lock_act.triggered.connect(overlay._toggle_lock)

    click_act = menu.addAction("Toggle Click-Through Mode")
    click_act.triggered.connect(lambda: overlay.set_click_through(not overlay.click_through))

    reposition_act = menu.addAction("Reset to Left Taskbar")
    reposition_act.triggered.connect(overlay.position_on_left_taskbar)

    menu.addSeparator()

    op_menu = menu.addMenu("Opacity Settings")
    for val in [10, 25, 50, 80, 100]:
        act = op_menu.addAction(f"{val}% Opacity")
        act.triggered.connect(lambda checked, v=val: overlay._set_opacity(v))

    font_menu = menu.addMenu("Font Settings")
    for f in ["Century Gothic", "Montserrat", "Poppins", "Outfit", "Segoe UI", "Arial"]:
        act = font_menu.addAction(f)
        act.triggered.connect(lambda checked, fname=f: overlay._set_font(fname))

    menu.addSeparator()

    manual_search_act = menu.addAction("Search Lyrics Manually")
    def _search_manual():
        query, ok = QInputDialog.getText(None, "Manual Lyrics Search", "Enter Song Title - Artist:")
        if ok and query:
            parts = query.split("-", 1)
            title = parts[0].strip()
            artist = parts[1].strip() if len(parts) > 1 else ""
            overlay.set_fetching_state(True)
            threading.Thread(
                target=controller._fetch_lyrics_worker,
                args=(title, artist, 0.0),
                daemon=True
            ).start()
    manual_search_act.triggered.connect(_search_manual)

    menu.addSeparator()

    exit_act = menu.addAction("Exit Auraly")
    def _exit():
        controller.stop()
        app.quit()
    exit_act.triggered.connect(_exit)

    tray_icon.setContextMenu(menu)
    tray_icon.show()
    return tray_icon

def run_pyqt6():
    app = QApplication(sys.argv)
    app.setApplicationName("Auraly")
    app.setQuitOnLastWindowClosed(False)

    icon_path = get_asset_path("app_icon.png")
    if icon_path and os.path.exists(icon_path):
        app.setWindowIcon(QIcon(icon_path))

    overlay = TaskbarOverlayWindow()
    overlay.show()

    controller = ControllerCore(overlay)
    tray = create_tray_icon(app, overlay, controller)
    print("[Auraly] Started with transparent white quaver icon!")
    sys.exit(app.exec())

def run_tkinter():
    print("[Auraly] Started with Tkinter lightweight engine!")
    overlay = TaskbarLyricsTkOverlay()
    controller = ControllerCore(overlay)
    overlay.run()

def main():
    if not ensure_single_instance():
        sys.exit(0)

    if HAS_PYQT6:
        run_pyqt6()
    else:
        run_tkinter()

if __name__ == "__main__":
    main()
