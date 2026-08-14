from __future__ import annotations

import os
import subprocess
import sys


def wav_to_mp3(
    wav_path: str,
    mp3_path: str,
    ffmpeg_path: str = "ffmpeg",
) -> bool:
    """Convert a WAV file to MP3 using system ffmpeg.

    Args:
        wav_path: Source WAV file.
        mp3_path: Destination MP3 file.
        ffmpeg_path: Path to ffmpeg executable. If empty, tries PATH.

    Returns:
        True if the conversion produced a non-empty MP3 file, False otherwise.
    """
    ffmpeg = ffmpeg_path.strip() if ffmpeg_path and ffmpeg_path.strip() else "ffmpeg"
    cmd = [
        ffmpeg,
        "-y",
        "-i", wav_path,
        "-codec:a", "libmp3lame",
        "-q:a", "2",
        mp3_path,
    ]
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            timeout=180,
        )
        if result.returncode != 0:
            print(
                f"[AudioConverter] ffmpeg failed: {result.stderr.decode('utf-8', errors='replace')[:500]}",
                file=sys.stderr,
            )
            return False
        return os.path.exists(mp3_path) and os.path.getsize(mp3_path) > 0
    except FileNotFoundError:
        print(
            f"[AudioConverter] ffmpeg not found: '{ffmpeg}'. "
            "Install ffmpeg or configure its path in settings.",
            file=sys.stderr,
        )
        return False
    except subprocess.TimeoutExpired:
        print("[AudioConverter] ffmpeg timed out", file=sys.stderr)
        return False
