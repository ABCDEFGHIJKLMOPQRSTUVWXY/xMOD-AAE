# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from character_engine.speaker_normalizer import normalize_speakers
from text_processor.dialogue import DialogueSegment


def _seg(text, speaker):
    return DialogueSegment(text=text, speaker=speaker, is_dialogue=True)


def test_merges_generic_to_cooccurring_formal_in_same_paragraph():
    paragraphs = [
        [_seg("李耀看过来。", "李耀"), _seg("这事交给我。", "少年")],
        [_seg("", "李耀"), _seg("", "少年")],
    ]
    normalize_speakers(paragraphs)
    assert paragraphs[0][1].speaker == "李耀"
    assert paragraphs[1][1].speaker == "李耀"


def test_falls_back_to_global_most_frequent_formal():
    paragraphs = [
        [_seg("", "李耀"), _seg("", "李耀")],
        [_seg("", "赵敏"), _seg("", "赵敏")],
        [_seg("", "少年")],
    ]
    normalize_speakers(paragraphs)
    assert paragraphs[2][0].speaker == "李耀"


def test_cooccurrence_beats_global_frequency():
    paragraphs = [
        [_seg("", "李耀"), _seg("", "李耀")],
        [_seg("", "赵敏"), _seg("", "少年")],
    ]
    normalize_speakers(paragraphs)
    assert paragraphs[1][1].speaker == "赵敏"


def test_keeps_original_when_no_formal_present():
    segments = [_seg("", "少年"), _seg("", "老者")]
    normalize_speakers(segments)
    assert segments[0].speaker == "少年"
    assert segments[1].speaker == "老者"


def test_preserves_unknown_and_narrator():
    segments = [_seg("", "未知"), _seg("", "旁白"), _seg("", "李耀")]
    normalize_speakers(segments)
    assert segments[0].speaker == "未知"
    assert segments[1].speaker == "旁白"


def test_leaves_formal_names_unchanged():
    segments = [_seg("", "李耀"), _seg("", "赵敏")]
    normalize_speakers(segments)
    assert segments[0].speaker == "李耀"
    assert segments[1].speaker == "赵敏"


def test_accepts_flat_list():
    segments = [_seg("", "李耀"), _seg("", "李耀"), _seg("", "少年")]
    normalize_speakers(segments)
    assert segments[2].speaker == "李耀"
