import re
import requests
import urllib.parse
from typing import Optional, Dict, Any, List, Tuple
from lrc_parser import LRCParser, LyricLine

Tuple_Lyrics_Result = Dict[str, Any]

def safe_log(msg: str):
    """Safely prints log messages preventing UnicodeEncodeError on Windows console."""
    try:
        print(msg)
    except UnicodeEncodeError:
        print(msg.encode('ascii', errors='replace').decode('ascii'))

class LyricsFetcher:
    """Standard, clean LRCLIB lyrics fetcher."""
    
    BASE_URL = "https://lrclib.net/api"

    @classmethod
    def clean_title(cls, title: str) -> str:
        if not title:
            return ""
        # Remove parenthetical noise like (Official Video), [Lyrics], (feat. XYZ)
        t = re.sub(r'[\(\[\{].*?[\)\]\}]', '', title)
        # Split on keywords like official, video, lyrics, remastered, etc.
        t = re.split(r'\b(ft\.?|feat\.?|official|video|audio|remastered|lyrics|hd|4k)\b', t, flags=re.IGNORECASE)[0]
        return t.strip(' -_')

    @classmethod
    def clean_artist(cls, artist: str) -> str:
        if not artist:
            return ""
        a = re.split(r'\b(vevo|feat\.?|ft\.?)\b', artist, flags=re.IGNORECASE)[0]
        return a.strip(' -_')

    @classmethod
    def get_lyrics(cls, track_name: str, artist_name: str, duration: Optional[float] = None) -> Tuple_Lyrics_Result:
        if not track_name:
            return {"synced_lyrics": [], "plain_lyrics": "No track playing", "is_synced": False}

        clean_t = cls.clean_title(track_name)
        clean_a = cls.clean_artist(artist_name)
        dur = int(duration) if duration and duration > 0 else None

        safe_log(f"[LyricsFetcher] Fetching lyrics for: '{clean_t}' by '{clean_a}' (raw: '{track_name}')")

        # 1. Try LRCLIB exact GET with cleaned title
        params = {"track_name": clean_t, "artist_name": clean_a}
        if dur:
            params["duration"] = dur

        try:
            resp = requests.get(f"{cls.BASE_URL}/get", params=params, timeout=4)
            if resp.status_code == 200:
                res = cls._process_response(resp.json(), duration)
                if res["synced_lyrics"]:
                    return res
        except Exception as e:
            safe_log(f"[LyricsFetcher] Exact GET error: {e}")

        # 2. Try LRCLIB search query with cleaned title & artist
        query_cleaned = f"{clean_t} {clean_a}".strip()
        try:
            resp = requests.get(f"{cls.BASE_URL}/search", params={"q": query_cleaned}, timeout=4)
            if resp.status_code == 200:
                results = resp.json()
                if isinstance(results, list) and len(results) > 0:
                    best = next((r for r in results if r.get("syncedLyrics")), results[0])
                    res = cls._process_response(best, duration)
                    if res["synced_lyrics"]:
                        return res
        except Exception as e:
            safe_log(f"[LyricsFetcher] Search cleaned error: {e}")

        # 3. Try LRCLIB search query with raw track title
        if track_name != clean_t:
            try:
                resp = requests.get(f"{cls.BASE_URL}/search", params={"q": f"{track_name} {artist_name}".strip()}, timeout=4)
                if resp.status_code == 200:
                    results = resp.json()
                    if isinstance(results, list) and len(results) > 0:
                        best = next((r for r in results if r.get("syncedLyrics")), results[0])
                        res = cls._process_response(best, duration)
                        if res["synced_lyrics"]:
                            return res
            except Exception as e:
                pass

        # 4. Fallback API: lyrics.ovh for plain text lyrics
        if clean_t and clean_a:
            try:
                ovh_url = f"https://api.lyrics.ovh/v1/{urllib.parse.quote(clean_a)}/{urllib.parse.quote(clean_t)}"
                resp = requests.get(ovh_url, timeout=4)
                if resp.status_code == 200:
                    lyrics_txt = resp.json().get("lyrics", "")
                    if lyrics_txt:
                        parsed_plain = LRCParser.parse_plain_text(lyrics_txt, duration or 180.0)
                        return {
                            "synced_lyrics": parsed_plain,
                            "plain_lyrics": lyrics_txt,
                            "is_synced": True
                        }
            except Exception as e:
                safe_log(f"[LyricsFetcher] OVH fallback error: {e}")

        return {"synced_lyrics": [], "plain_lyrics": "Lyrics not found", "is_synced": False}

    @classmethod
    def _process_response(cls, data: Dict[str, Any], duration: Optional[float] = None) -> Dict[str, Any]:
        synced_raw = data.get("syncedLyrics")
        plain_raw = data.get("plainLyrics")

        if synced_raw:
            parsed = LRCParser.parse(synced_raw)
            if parsed:
                return {
                    "synced_lyrics": parsed,
                    "plain_lyrics": synced_raw,
                    "is_synced": True
                }

        if plain_raw:
            parsed_plain = LRCParser.parse_plain_text(plain_raw, duration or 180.0)
            return {
                "synced_lyrics": parsed_plain,
                "plain_lyrics": plain_raw,
                "is_synced": True
            }

        return {"synced_lyrics": [], "plain_lyrics": "No lyrics available", "is_synced": False}
