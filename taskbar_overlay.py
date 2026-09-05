import sys
import os
import ctypes
import time
from typing import Optional, List

from PyQt6.QtCore import Qt, QTimer, QPoint, QRect, pyqtSignal
from PyQt6.QtGui import QFont, QColor, QPainter, QLinearGradient, QPen, QAction, QIcon, QFontMetrics, QMouseEvent, QFontDatabase, QCursor
from PyQt6.QtWidgets import (
    QWidget, QLabel, QVBoxLayout, QHBoxLayout, QMenu, QSystemTrayIcon,
    QApplication, QInputDialog, QColorDialog
)

from lrc_parser import LyricLine, LRCParser
from media_listener import MediaInfo
from lyrics_fetcher import LyricsFetcher

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

SWP_FRAMECHANGED = 0x0020
SWP_NOMOVE = 0x0002
SWP_NOSIZE = 0x0001
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010

def get_geometric_sans_font() -> str:
    """Finds available Geometric Sans-Serif font on Windows."""
    geo_fonts = ["Century Gothic", "Montserrat", "Poppins", "Outfit", "AvantGarde", "Segoe UI"]
    try:
        available = QFontDatabase.families()
        for gf in geo_fonts:
            if gf in available:
                return gf
    except Exception:
        pass
    return "Century Gothic"

class TaskbarOverlayWindow(QWidget):
    """
    Auraly: Transparent, frameless, always-on-top lyrics overlay positioned 
    on the left side of the Windows Taskbar.
    Clean, sleek menu without repetitive icons.
    """
    refresh_requested_signal = pyqtSignal()

    def __init__(self):
        super().__init__()

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.WindowStaysOnTopHint |
            Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)

        self.song_info = "Auraly - Waiting for music..."
        self.current_lyric = "Play a song on Spotify / YouTube / Media Player"
        self.next_lyric = ""
        self.is_synced = False
        self.is_fetching = False
        self.click_through = False
        self.is_locked = True

        # Font & Opacity defaults
        self.font_family = get_geometric_sans_font()
        self.font_size = 11
        self.opacity_percent = 80

        self.default_width = 440
        self.default_height = 46
        self.drag_position = QPoint()

        self._setup_ui()
        self.position_on_left_taskbar()

        self.sync_timer = QTimer(self)
        self.sync_timer.setInterval(50)
        self.sync_timer.timeout.connect(self._on_sync_tick)
        self.sync_timer.start()

        self.lrc_lines: List[LyricLine] = []
        self.playback_position = 0.0
        self.last_position_update = time.time()
        self.is_playing = False

        self._apply_win32_styles()

    def _setup_ui(self):
        self.resize(self.default_width, self.default_height)
        self.setMinimumSize(250, 36)

    def position_on_left_taskbar(self):
        screen = QApplication.primaryScreen()
        if not screen:
            return

        geo = screen.availableGeometry()
        full_geo = screen.geometry()

        taskbar_height = full_geo.height() - geo.height()
        if taskbar_height <= 0:
            taskbar_height = 48

        x = 12
        y = full_geo.height() - taskbar_height + (taskbar_height - self.default_height) // 2
        
        self.move(x, y)

    def _apply_win32_styles(self):
        if sys.platform != 'win32':
            return
        
        try:
            hwnd = int(self.winId())
            user32 = ctypes.windll.user32
            
            ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ex_style |= WS_EX_TOOLWINDOW | WS_EX_LAYERED
            
            if self.click_through:
                ex_style |= WS_EX_TRANSPARENT | WS_EX_NOACTIVATE
            else:
                ex_style &= ~WS_EX_TRANSPARENT
                ex_style &= ~WS_EX_NOACTIVATE

            user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)

            flags = SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_FRAMECHANGED | SWP_NOACTIVATE
            user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, flags)
        except Exception as e:
            print(f"[Auraly] Win32 style error: {e}")

    def set_click_through(self, enabled: bool):
        self.click_through = enabled
        self._apply_win32_styles()
        self.update()

    def set_fetching_state(self, is_fetching: bool):
        self.is_fetching = is_fetching
        if is_fetching:
            self.current_lyric = "Refreshing lyrics..."
        self.update()

    def update_media(self, info: MediaInfo, lrc_lines: List[LyricLine], is_synced: bool):
        self.is_playing = info.is_playing
        self.lrc_lines = lrc_lines
        self.is_synced = is_synced

        if info.title:
            self.song_info = f"{info.title} - {info.artist}" if info.artist else info.title
        else:
            self.song_info = "Auraly - Waiting for music..."
            self.current_lyric = "Play a song to see lyrics"
            self.next_lyric = ""

        # Direct instant seek snapping
        now = time.time()
        self.playback_position = info.position
        self.last_position_update = now

        if not lrc_lines and info.title and not self.is_fetching:
            self.current_lyric = "(Lyrics not found for this track)"
            self.next_lyric = ""

        self.update()

    def _on_sync_tick(self):
        if not self.is_playing or not self.lrc_lines:
            self.update()
            return

        now = time.time()
        elapsed_since_update = now - self.last_position_update
        current_time = self.playback_position + elapsed_since_update

        curr, nxt, idx = LRCParser.get_current_line(self.lrc_lines, current_time)
        if curr:
            self.current_lyric = curr.text
        elif idx == -1:
            self.current_lyric = self.song_info

        if nxt:
            self.next_lyric = nxt.text
        else:
            self.next_lyric = ""

        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if not self.is_locked:
            painter.fillRect(self.rect(), QColor(20, 20, 20, 180))
            pen = QPen(QColor(0, 230, 118, 220), 1, Qt.PenStyle.DashLine)
            painter.setPen(pen)
            painter.drawRect(0, 0, self.width() - 1, self.height() - 1)

        w = self.width()
        h = self.height()

        alpha_val = int(255 * (self.opacity_percent / 100.0))
        shadow_alpha = int(220 * (self.opacity_percent / 100.0))

        primary_color = QColor(255, 255, 255, alpha_val)
        accent_color = QColor(29, 185, 84, alpha_val)
        shadow_color = QColor(0, 0, 0, shadow_alpha)

        # Line 1: Header (Song Title - Artist) at y=0, height=16
        font_header = QFont(self.font_family, max(8, self.font_size - 2), QFont.Weight.Bold)
        font_header.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.4)
        painter.setFont(font_header)
        
        metrics_header = QFontMetrics(font_header)
        elided_header = metrics_header.elidedText(self.song_info, Qt.TextElideMode.ElideRight, w - 10)

        painter.setPen(shadow_color)
        painter.drawText(2, 1, w - 10, 16, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextSingleLine, elided_header)

        painter.setPen(accent_color)
        painter.drawText(1, 0, w - 10, 16, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextSingleLine, elided_header)

        # Line 2: Active Synced Lyric Line at y=18, height=24
        font_main = QFont(self.font_family, self.font_size, QFont.Weight.Bold)
        font_main.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 0.4)
        painter.setFont(font_main)

        metrics_main = QFontMetrics(font_main)
        elided_lyric = metrics_main.elidedText(self.current_lyric, Qt.TextElideMode.ElideRight, w - 10)

        painter.setPen(shadow_color)
        painter.drawText(2, 19, w - 10, 24, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextSingleLine, elided_lyric)

        painter.setPen(primary_color)
        painter.drawText(1, 18, w - 10, 24, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter | Qt.TextFlag.TextSingleLine, elided_lyric)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.MouseButton.LeftButton and not self.is_locked:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == Qt.MouseButton.RightButton:
            self._show_context_menu_at_pos(QCursor.pos())
            event.accept()

    def mouseMoveEvent(self, event: QMouseEvent):
        if event.buttons() == Qt.MouseButton.LeftButton and not self.is_locked:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        self.is_locked = not self.is_locked
        self.update()

    def contextMenuEvent(self, event):
        self._show_context_menu_at_pos(QCursor.pos())

    def _show_context_menu_at_pos(self, global_pos: QPoint):
        menu = QMenu(self)

        # Clean text menu items without repetitive green A icons
        refresh_act = menu.addAction("Refresh / Resync Lyrics")
        refresh_act.triggered.connect(lambda: self.refresh_requested_signal.emit())

        menu.addSeparator()

        lock_act = menu.addAction("Unlocked (Drag enabled)" if not self.is_locked else "Lock Position")
        lock_act.triggered.connect(self._toggle_lock)

        click_act = menu.addAction("Click-Through Mode ON" if self.click_through else "Enable Click-Through Mode")
        click_act.triggered.connect(lambda: self.set_click_through(not self.click_through))

        reset_act = menu.addAction("Reset to Left Taskbar")
        reset_act.triggered.connect(self.position_on_left_taskbar)

        menu.addSeparator()

        op_menu = menu.addMenu(f"Opacity ({self.opacity_percent}%)")
        for val in [10, 25, 50, 80, 100]:
            act = op_menu.addAction(f"{val}% Opacity" + (" (Active)" if val == self.opacity_percent else ""))
            act.triggered.connect(lambda checked, v=val: self._set_opacity(v))
        
        font_menu = menu.addMenu(f"Font ({self.font_family})")
        for f in ["Century Gothic", "Montserrat", "Poppins", "Outfit", "Segoe UI", "Arial"]:
            act = font_menu.addAction(f)
            act.triggered.connect(lambda checked, fname=f: self._set_font(fname))

        font_size_act = menu.addAction("Change Font Size")
        font_size_act.triggered.connect(self._change_font_size)

        menu.exec(global_pos)

    def _toggle_lock(self):
        self.is_locked = not self.is_locked
        self.update()

    def _set_opacity(self, percent: int):
        self.opacity_percent = percent
        self.update()

    def _set_font(self, font_name: str):
        self.font_family = font_name
        self.update()

    def _change_font_size(self):
        size, ok = QInputDialog.getInt(self, "Font Size", "Select Lyric Font Size:", self.font_size, 8, 24)
        if ok:
            self.font_size = size
            self.update()
