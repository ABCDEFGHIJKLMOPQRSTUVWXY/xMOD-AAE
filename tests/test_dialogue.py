# -*- coding: utf-8 -*-
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from text_processor.dialogue import extract_spans, DialogueSegment


def test_simple_quote():
    """Quote-paired dialogue creates a dialogue span with correct position."""
    para = '张三说：\u201c今天天气真好。\u201d'
    result = extract_spans(para)
    speaker_none = all(seg.speaker is None for seg in result)
    assert speaker_none, f"Expected all speakers None, got: {[(seg.text, seg.speaker) for seg in result]}"
    dialogue_segs = [seg for seg in result if seg.is_dialogue]
    assert len(dialogue_segs) == 1, f"Expected 1 dialogue segment, got {len(dialogue_segs)}"
    assert dialogue_segs[0].text == "今天天气真好。"


def test_chinese_book_quotes():
    """Dialogue with \u300c\u300d book quotes."""
    para = '李四道：\u300c此事不可声张。\u300d'
    result = extract_spans(para)
    dialogue_segs = [seg for seg in result if seg.is_dialogue]
    assert len(dialogue_segs) == 1, f"Expected 1 dialogue segment, got {len(dialogue_segs)}"
    assert dialogue_segs[0].text == "此事不可声张。"


def test_narration_between_dialogues():
    """Two dialogue spans with narration between them."""
    para = '张三说：\u201c你好。\u201d李四说：\u201c你也好。\u201d'
    result = extract_spans(para)
    dialogue_segs = [seg for seg in result if seg.is_dialogue]
    assert len(dialogue_segs) == 2, f"Expected 2 dialogue segments, got {len(dialogue_segs)}"
    assert dialogue_segs[0].text == "你好。"
    assert dialogue_segs[1].text == "你也好。"


def test_pure_narration():
    """Paragraph with no dialogue."""
    para = '清晨的阳光透过窗户洒在地板上。'
    result = extract_spans(para)
    assert len(result) == 1, f"Expected 1 segment, got {len(result)}"
    assert result[0].speaker is None
    assert result[0].is_dialogue is False
    assert result[0].text == para
    assert result[0].start == 0
    assert result[0].end == len(para)


def test_segments_cover_full_paragraph():
    """All segments together must equal the original paragraph."""
    para = '张三推门进来，喊道：\u201c快来看！\u201d李四转过头，问：\u201c怎么了？\u201d'
    result = extract_spans(para)
    cursor = 0
    for seg in result:
        found = para.find(seg.text, cursor)
        assert found == cursor, f"Gap at offset {cursor}: '{seg.text}'"
        assert seg.start == cursor, f"start mismatch: {seg.start} vs {cursor}"
        cursor += len(seg.text)
        assert seg.end == cursor, f"end mismatch: {seg.end} vs {cursor}"
    assert cursor == len(para), f"Total mismatch: {cursor} vs {len(para)}"


def test_colon_dialogue():
    """Colon-prefixed dialogue creates spans at correct positions."""
    para = '张三：我们走吧。李四：等一下。'
    result = extract_spans(para)
    dialogue_segs = [seg for seg in result if seg.is_dialogue]
    assert len(dialogue_segs) >= 2, f"Expected at least 2 dialogue segments, got {len(dialogue_segs)}: {[(s.text, s.start, s.end) for s in result]}"
    assert any("我们走吧" in seg.text for seg in dialogue_segs), f"First dialog not found in {[seg.text for seg in dialogue_segs]}"
    assert any("等一下" in seg.text for seg in dialogue_segs), f"Second dialog not found in {[seg.text for seg in dialogue_segs]}"


def test_all_speakers_none_initially():
    """After extract_spans, all speaker fields should be None."""
    para = '张三说：\u201c你好。\u201d李四道：\u300c再见。\u300d老王：明天见。'
    result = extract_spans(para)
    for seg in result:
        assert seg.speaker is None, f"Expected speaker=None, got '{seg.speaker}' for '{seg.text}'"


def test_colon_followed_by_text():
    """Colon followed by dialogue content should create a dialogue span."""
    para = '张三：我们走吧。'
    result = extract_spans(para)
    dialogue_segs = [seg for seg in result if seg.is_dialogue]
    assert len(dialogue_segs) >= 1, f"Expected at least 1 dialogue span, got {len(dialogue_segs)}"


if __name__ == "__main__":
    all_tests = [
        test_simple_quote,
        test_chinese_book_quotes,
        test_narration_between_dialogues,
        test_pure_narration,
        test_segments_cover_full_paragraph,
        test_colon_dialogue,
        test_all_speakers_none_initially,
        test_colon_followed_by_text,
    ]

    passed = 0
    failed = 0

    for test_fn in all_tests:
        try:
            test_fn()
            passed += 1
            print(f"  PASS: {test_fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  FAIL: {test_fn.__name__} -- {e}")
        except Exception as e:
            failed += 1
            print(f"  ERROR: {test_fn.__name__} -- {e}")

    print(f"\n{passed} passed, {failed} failed out of {len(all_tests)}")
    sys.exit(0 if failed == 0 else 1)
