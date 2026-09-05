import asyncio
import threading
import time
import datetime
import re
from typing import Callable, Optional, Dict, Any

try:
    import winrt.windows.media.control as wmc
    HAS_WINRT = True
except ImportError:
    HAS_WINRT = False

try:
    import win32gui
    import win32process
    import pywintypes
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

class MediaInfo:
    def __init__(self, title: str = "", artist: str = "", album: str = "", is_playing: bool = False, position: float = 0.0, duration: float = 0.0):
        self.title = title
        self.artist = artist
        self.album = album
        self.is_playing = is_playing
        self.position = position  # in seconds
        self.duration = duration  # in seconds

    def __eq__(self, other):
        if not isinstance(other, MediaInfo):
            return False
        return (self.title == other.title and 
                self.artist == other.artist and 
                self.is_playing == other.is_playing)

NON_MUSIC_KEYWORDS = [
    "google search", "new tab", "settings", "gmail", "github", 
    "stack overflow", "wikipedia", "reddit", "facebook", "twitter", 
    "instagram", "linkedin", "amazon", "bing", "yahoo", "duckduckgo",
    "search -", "- search", "inbox", "mail", "drive", "docs"
]

def is_valid_music_title(title: str, artist: str = "") -> bool:
    """Checks if a detected title is genuine music rather than a web search or browser tab."""
    if not title or len(title.strip()) < 2:
        return False

    t_lower = title.lower()
    for kw in NON_MUSIC_KEYWORDS:
        if kw in t_lower:
            return False

    return True

class MediaListener(threading.Thread):
    """
    Background thread querying Windows System Media Transport Controls (WinRT GSMTC)
    to get real-time track metadata and accurate live timeline positions.
    Handles initial track load delay and stale GSMTC timestamps.
    """
    def __init__(self, callback: Callable[[MediaInfo], None], poll_interval: float = 0.25):
        super().__init__(daemon=True)
        self.callback = callback
        self.poll_interval = poll_interval
        self._running = True
        self.current_info = MediaInfo()
        self.last_valid_info = MediaInfo(title="No music playing", artist="", is_playing=False)
        self.last_track_key = ""
        self.track_start_time = time.time()

    def stop(self):
        self._running = False

    def run(self):
        while self._running:
            try:
                if HAS_WINRT:
                    try:
                        asyncio.run(self._async_loop())
                    except Exception as e:
                        print(f"[MediaListener] Async loop error: {e}")
                else:
                    self._fallback_loop()
            except Exception as outer_e:
                print(f"[MediaListener] Outer thread guard caught error: {outer_e}")
                time.sleep(1.0)

    async def _async_loop(self):
        manager = None
        while self._running:
            try:
                if manager is None:
                    manager = await wmc.GlobalSystemMediaTransportControlsSessionManager.request_async()
                
                session = manager.get_current_session()
                if session:
                    props = await session.try_get_media_properties_async()
                    playback_info = session.get_playback_info()
                    timeline = session.get_timeline_properties()

                    is_playing = False
                    if playback_info:
                        status = playback_info.playback_status
                        is_playing = (status == 4 or getattr(status, "value", None) == 4 or str(status).endswith("PLAYING"))

                    title = props.title if props and props.title else ""
                    artist = props.artist if props and props.artist else ""
                    album = props.album_title if props and props.album_title else ""

                    pos_sec = 0.0
                    dur_sec = 0.0
                    if timeline:
                        if timeline.position:
                            base_pos = timeline.position.total_seconds()
                            if timeline.last_updated_time and is_playing:
                                now_utc = datetime.datetime.now(datetime.timezone.utc)
                                elapsed = (now_utc - timeline.last_updated_time).total_seconds()
                                # If base_pos is 0.0 (track just started) but last_updated_time is old, ignore stale offset
                                if base_pos == 0.0 and elapsed > 2.0:
                                    pos_sec = 0.0
                                elif 0 <= elapsed < 3600:
                                    pos_sec = base_pos + elapsed
                                else:
                                    pos_sec = base_pos
                            else:
                                pos_sec = base_pos

                        if timeline.end_time:
                            dur_sec = timeline.end_time.total_seconds()

                    if is_valid_music_title(title, artist):
                        info = MediaInfo(
                            title=title,
                            artist=artist,
                            album=album,
                            is_playing=is_playing,
                            position=pos_sec,
                            duration=dur_sec
                        )
                        self.last_valid_info = info
                        self.callback(info)
                    else:
                        fallback_info = self._scan_window_titles()
                        if fallback_info and is_valid_music_title(fallback_info.title, fallback_info.artist):
                            self.last_valid_info = fallback_info
                            self.callback(fallback_info)
                        elif self.last_valid_info and self.last_valid_info.title != "No music playing":
                            self.last_valid_info.is_playing = is_playing
                            self.callback(self.last_valid_info)
                        else:
                            self.callback(MediaInfo(title="No music playing", artist="", is_playing=False))
                else:
                    fallback_info = self._scan_window_titles()
                    if fallback_info and is_valid_music_title(fallback_info.title, fallback_info.artist):
                        self.last_valid_info = fallback_info
                        self.callback(fallback_info)
                    elif self.last_valid_info and self.last_valid_info.title != "No music playing":
                        self.callback(self.last_valid_info)
                    else:
                        self.callback(MediaInfo(title="No music playing", artist="", is_playing=False))

            except Exception as e:
                manager = None
                try:
                    fallback_info = self._scan_window_titles()
                    if fallback_info and is_valid_music_title(fallback_info.title, fallback_info.artist):
                        self.callback(fallback_info)
                    elif self.last_valid_info and self.last_valid_info.title != "No music playing":
                        self.callback(self.last_valid_info)
                except Exception:
                    pass

            await asyncio.sleep(self.poll_interval)

    def _fallback_loop(self):
        while self._running:
            try:
                info = self._scan_window_titles()
                if info and is_valid_music_title(info.title, info.artist):
                    self.last_valid_info = info
                    self.callback(info)
                elif self.last_valid_info and self.last_valid_info.title != "No music playing":
                    self.callback(self.last_valid_info)
                else:
                    self.callback(MediaInfo(title="No music playing", artist="", is_playing=False))
            except Exception as e:
                print(f"[MediaListener] Fallback loop error: {e}")
            time.sleep(self.poll_interval)

    def _scan_spotify_window(self) -> Optional[MediaInfo]:
        """Scans dedicated Spotify desktop application window with Win32 timeout protection."""
        if not HAS_WIN32:
            return None

        found_title = ""
        found_artist = ""

        def enum_windows_callback(hwnd, extra):
            nonlocal found_title, found_artist
            try:
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if not title:
                        return True

                    if ("Spotify" in title or "spotify" in title.lower()) and " - " in title:
                        if title not in ["Spotify Premium", "Spotify Free", "Spotify"]:
                            parts = title.split(" - ", 1)
                            found_artist = parts[0].strip()
                            found_title = parts[1].strip()
                            return False
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(enum_windows_callback, None)
        except Exception:
            pass

        if found_title:
            key = f"{found_title}||{found_artist}"
            if key != self.last_track_key:
                self.last_track_key = key
                self.track_start_time = time.time()
                self.estimated_position = 0.0
            else:
                self.estimated_position = time.time() - self.track_start_time

            return MediaInfo(
                title=found_title,
                artist=found_artist,
                is_playing=True,
                position=self.estimated_position
            )
        return None

    def _scan_window_titles(self) -> Optional[MediaInfo]:
        """Scans Spotify and music player window titles with Win32 timeout protection."""
        spotify_info = self._scan_spotify_window()
        if spotify_info:
            return spotify_info

        if not HAS_WIN32:
            return None

        found_title = ""
        found_artist = ""

        def enum_windows_callback(hwnd, extra):
            nonlocal found_title, found_artist
            try:
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if not title:
                        return True

                    if " - YouTube" in title or "YouTube Music" in title:
                        clean = title.replace(" - YouTube", "").replace(" - YouTube Music", "").strip()
                        if " - " in clean:
                            parts = clean.split(" - ", 1)
                            found_artist = parts[0].strip()
                            found_title = parts[1].strip()
                        else:
                            found_title = clean
                        return False
            except Exception:
                pass
            return True

        try:
            win32gui.EnumWindows(enum_windows_callback, None)
        except Exception:
            pass

        if found_title and is_valid_music_title(found_title, found_artist):
            key = f"{found_title}||{found_artist}"
            if key != self.last_track_key:
                self.last_track_key = key
                self.track_start_time = time.time()
                self.estimated_position = 0.0
            else:
                self.estimated_position = time.time() - self.track_start_time

            return MediaInfo(
                title=found_title,
                artist=found_artist,
                is_playing=True,
                position=self.estimated_position
            )
        return None
