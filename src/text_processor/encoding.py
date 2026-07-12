from __future__ import annotations

import chardet


_COMMON_ENCODINGS = ["GBK", "GB2312", "GB18030", "UTF-8", "UTF-16"]


def load(filepath: str) -> str:
    with open(filepath, "rb") as f:
        raw = f.read()

    result = chardet.detect(raw)
    encoding = result.get("encoding")
    confidence = result.get("confidence", 0.0)

    if encoding and confidence >= 0.7:
        try:
            return raw.decode(encoding)
        except (UnicodeDecodeError, LookupError):
            pass

    for enc in _COMMON_ENCODINGS:
        try:
            return raw.decode(enc)
        except (UnicodeDecodeError, LookupError):
            continue

    raise UnicodeDecodeError(
        "unknown",
        b"",
        0,
        1,
        "Failed to decode file with any known encoding",
    )
