import re
from typing import List, Tuple, Optional

class LyricLine:
    def __init__(self, timestamp: float, text: str):
        self.timestamp = timestamp  # in seconds
        self.text = text.strip()

    def __repr__(self):
        return f"[{self.timestamp:.2f}s] {self.text}"

class LRCParser:
    """Parses .lrc lyrics strings or plain text into timed LyricLine objects."""
    
    # Matches [mm:ss.xx] or [mm:ss:xx] or [mm:ss.xxx]
    TIMESTAMP_REGEX = re.compile(r'\[(\d{2}):(\d{2})[.:](\d{2,3})\]')

    @classmethod
    def parse(cls, lrc_text: str) -> List[LyricLine]:
        if not lrc_text:
            return []

        lines: List[LyricLine] = []
        for raw_line in lrc_text.splitlines():
            raw_line = raw_line.strip()
            if not raw_line:
                continue

            matches = cls.TIMESTAMP_REGEX.findall(raw_line)
            if not matches:
                continue

            # Strip all timestamps from the line to extract lyric text
            clean_text = cls.TIMESTAMP_REGEX.sub('', raw_line).strip()

            for min_str, sec_str, ms_str in matches:
                minutes = int(min_str)
                seconds = int(sec_str)
                # Handle 2-digit vs 3-digit ms
                if len(ms_str) == 2:
                    milliseconds = int(ms_str) * 10
                else:
                    milliseconds = int(ms_str)

                total_seconds = minutes * 60 + seconds + milliseconds / 1000.0
                lines.append(LyricLine(total_seconds, clean_text))

        lines.sort(key=lambda x: x.timestamp)
        return lines

    @classmethod
    def parse_plain_text(cls, plain_text: str, total_duration: float = 180.0) -> List[LyricLine]:
        """
        Converts plain text lyrics into estimated timed lines by evenly distributing timestamps.
        """
        if not plain_text:
            return []

        raw_lines = [line.strip() for line in plain_text.splitlines() if line.strip()]
        if not raw_lines:
            return []

        if total_duration <= 0:
            total_duration = 180.0

        # Start lyrics slightly after song start (e.g. 5 seconds in)
        start_delay = 5.0
        available_time = max(10.0, total_duration - start_delay - 5.0)
        time_per_line = available_time / len(raw_lines)

        timed_lines: List[LyricLine] = []
        for i, text in enumerate(raw_lines):
            t = start_delay + (i * time_per_line)
            timed_lines.append(LyricLine(t, text))

        return timed_lines

    @classmethod
    def get_current_line(cls, lines: List[LyricLine], current_time: float) -> Tuple[Optional[LyricLine], Optional[LyricLine], int]:
        """
        Returns (current_line, next_line, index) based on current playback timestamp in seconds.
        """
        if not lines:
            return None, None, -1

        current_idx = -1
        for i, line in enumerate(lines):
            if current_time >= line.timestamp:
                current_idx = i
            else:
                break

        if current_idx == -1:
            # Before the first line
            return None, lines[0], -1

        current_line = lines[current_idx]
        next_line = lines[current_idx + 1] if current_idx + 1 < len(lines) else None
        return current_line, next_line, current_idx
