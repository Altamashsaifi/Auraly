import sys
import os
import ctypes
import time
import tkinter as tk
from typing import Optional, List

from lrc_parser import LyricLine, LRCParser
from media_listener import MediaInfo
from lyrics_fetcher import LyricsFetcher

GWL_EXSTYLE = -20
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WS_EX_NOACTIVATE = 0x08000000
WS_EX_TOOLWINDOW = 0x00000080

class TaskbarLyricsTkOverlay:
    """
    Super lightweight Tkinter implementation of the Taskbar Lyrics overlay.
    Supports Geometric Sans-Serif font & opacity configuration.
    """
    def __init__(self):
        self.root = tk.Tk()

        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        
        self.trans_key = "#010101"
        self.root.config(bg=self.trans_key)
        try:
            self.root.wm_attributes("-transparentcolor", self.trans_key)
        except Exception:
            pass

        self.song_info = "TaskbarLyrics • Waiting for music..."
        self.current_lyric = "Play a song on Spotify / YouTube / Media Player"
        self.is_synced = False
        self.is_locked = True
        self.click_through = False
        
        # Geometric Sans-Serif font & 10% Opacity defaults
        self.font_family = "Century Gothic"
        self.font_size = 11
        self.opacity_percent = 10

        self.width = 420
        self.height = 46

        self.canvas = tk.Canvas(
            self.root, 
            width=self.width, 
            height=self.height, 
            bg=self.trans_key, 
            highlightthickness=0
        )
        self.canvas.pack(fill="both", expand=True)

        self._position_on_left_taskbar()
        self._apply_win32_styles()

        self.canvas.bind("<Button-1>", self._on_drag_start)
        self.canvas.bind("<B1-Motion>", self._on_drag_motion)
        self.canvas.bind("<Double-Button-1>", self._on_double_click)
        self.canvas.bind("<Button-3>", self._show_context_menu)

        self.lrc_lines: List[LyricLine] = []
        self.playback_position = 0.0
        self.last_update_time = time.time()
        self.is_playing = False

        self.root.after(50, self._on_tick)

    def _position_on_left_taskbar(self):
        try:
            user32 = ctypes.windll.user32
            screen_w = user32.GetSystemMetrics(0)
            screen_h = user32.GetSystemMetrics(1)
            
            taskbar_h = 48
            x = 12
            y = screen_h - taskbar_h + (taskbar_h - self.height) // 2
            
            self.root.geometry(f"{self.width}x{self.height}+{x}+{y}")
        except Exception:
            self.root.geometry(f"{self.width}x{self.height}+12+1000")

    def _apply_win32_styles(self):
        if sys.platform != 'win32':
            return
        try:
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if not hwnd:
                hwnd = self.root.winfo_id()
                
            ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ex_style |= WS_EX_TOOLWINDOW | WS_EX_NOACTIVATE | WS_EX_LAYERED
            
            if self.click_through:
                ex_style |= WS_EX_TRANSPARENT
            else:
                ex_style &= ~WS_EX_TRANSPARENT

            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)
        except Exception as e:
            print(f"[TkOverlay] Win32 style error: {e}")

    def set_click_through(self, enabled: bool):
        self.click_through = enabled
        self._apply_win32_styles()

    def update_media(self, info: MediaInfo, lrc_lines: List[LyricLine], is_synced: bool):
        self.is_playing = info.is_playing
        self.lrc_lines = lrc_lines
        self.is_synced = is_synced

        if info.title:
            self.song_info = f"{info.title} • {info.artist}" if info.artist else info.title
        else:
            self.song_info = "Waiting for music..."
            self.current_lyric = "Play a song to see lyrics"

        self.playback_position = info.position
        self.last_update_time = time.time()

        if not is_synced and info.title:
            self.current_lyric = "(Lyrics not found for this track)"

        self._render()

    def _on_tick(self):
        if self.is_playing and self.is_synced and self.lrc_lines:
            now = time.time()
            current_time = self.playback_position + (now - self.last_update_time)
            curr, nxt, idx = LRCParser.get_current_line(self.lrc_lines, current_time)
            if curr:
                self.current_lyric = curr.text
            elif idx == -1:
                self.current_lyric = self.song_info

        self._render()
        self.root.after(50, self._on_tick)

    def _render(self):
        self.canvas.delete("all")

        if not self.is_locked:
            self.canvas.create_rectangle(
                0, 0, self.width - 1, self.height - 1, 
                outline="#00E676", dash=(4, 4)
            )

        # Header Text (Song Title / Artist - Spotify Green)
        self.canvas.create_text(
            3, 10, anchor="w", text=self.song_info, 
            fill="#000000", font=(self.font_family, 9, "bold")
        )
        self.canvas.create_text(
            2, 9, anchor="w", text=self.song_info, 
            fill="#1DB954", font=(self.font_family, 9, "bold")
        )

        # Main Lyric Line (Bold White)
        self.canvas.create_text(
            3, 31, anchor="w", text=self.current_lyric, 
            fill="#000000", font=(self.font_family, self.font_size, "bold")
        )
        self.canvas.create_text(
            2, 30, anchor="w", text=self.current_lyric, 
            fill="#FFFFFF", font=(self.font_family, self.font_size, "bold")
        )

    def _on_drag_start(self, event):
        if not self.is_locked:
            self.drag_x = event.x
            self.drag_y = event.y

    def _on_drag_motion(self, event):
        if not self.is_locked:
            x = self.root.winfo_x() + (event.x - self.drag_x)
            y = self.root.winfo_y() + (event.y - self.drag_y)
            self.root.geometry(f"+{x}+{y}")

    def _on_double_click(self, event):
        self.is_locked = not self.is_locked
        self._render()

    def _show_context_menu(self, event):
        menu = tk.Menu(self.root, tearoff=0)
        status_text = " Unlocked (Drag enabled)" if not self.is_locked else "🔒 Lock Position"
        menu.add_command(label=status_text, command=self._toggle_lock)
        menu.add_command(label=" Reset to Left Taskbar", command=self._position_on_left_taskbar)
        menu.add_separator()
        menu.add_command(label=" Click-Through Mode", command=lambda: self.set_click_through(not self.click_through))
        menu.add_command(label=" Exit", command=self.root.quit)
        menu.tk_popup(event.x_root, event.y_root)

    def _toggle_lock(self):
        self.is_locked = not self.is_locked
        self._render()

    def run(self):
        self.root.mainloop()
