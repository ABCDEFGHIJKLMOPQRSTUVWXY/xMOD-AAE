from __future__ import annotations

import asyncio
import sys
import time

import edge_tts


async def synthesize(text: str, voice: str, output_path: str, retries: int = 3) -> bool:
    """Synthesize text to mp3 file using edge-tts.

    Args:
        text: Text to synthesize
        voice: edge-tts voice short name (e.g. "zh-CN-YunxiNeural")
        output_path: Path to save the mp3 file
        retries: Number of retries on failure

    Returns:
        True if synthesis succeeded, False otherwise
    """
    for attempt in range(retries):
        try:
            communicate = edge_tts.Communicate(text, voice)
            await communicate.save(output_path)
            return True
        except Exception as e:
            if attempt < retries - 1:
                wait = 2 ** attempt
                print(
                    f"[TTS] synthesis failed (attempt {attempt + 1}/{retries}): {e}. "
                    f"Retrying in {wait}s...",
                    file=sys.stderr,
                )
                await asyncio.sleep(wait)
            else:
                print(
                    f"[TTS] synthesis failed after {retries} attempts: {e}",
                    file=sys.stderr,
                )
                return False
    return False


def synthesize_sync(text: str, voice: str, output_path: str, retries: int = 3) -> bool:
    """Synchronous wrapper. Creates and runs an event loop for each call.

    This is called from QThread workers. Each call creates/destroys an event loop.
    """
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(synthesize(text, voice, output_path, retries))
    finally:
        loop.close()
