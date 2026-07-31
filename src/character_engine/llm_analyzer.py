from __future__ import annotations

import json
import re
import sys
from dataclasses import dataclass, field

import httpx

from text_processor.dialogue import DialogueSegment
from .aggregator import SpeakerInfo


@dataclass
class CharacterProfile:
    name: str
    gender: str = "未知"
    age_group: str = "未知"
    personality: list[str] = field(default_factory=list)
    role_type: str = "未知"
    speaking_style: str = ""
    summary: str = ""
    voice_id: str = ""


_SYSTEM_PROMPT = """You are a literary analyst. Given dialogue lines from a character in a novel, analyze and return a JSON object:
{
    "name": "角色名",
    "gender": "男/女/未知",
    "age_group": "少年/青年/中年/老年/未知",
    "personality": ["标签1", "标签2"],
    "role_type": "主角/配角/龙套/未知",
    "speaking_style": "说话风格描述",
    "summary": "一句话角色描述"
}"""

_ATTRIBUTION_PROMPT = """You are a literary analyst. Given ambiguous dialogue quotes from a novel (with surrounding context), determine which known character most likely spoke each line. Known characters: {names}

Return a JSON array of assignments:
[{"index": 0, "speaker": "角色名"}, ...]

If you cannot determine the speaker, set speaker to "未知"."""

_SPEAKER_ID_PROMPT = """你是一个文学分析助手。以下是一段小说段落，标记了对话内容的位置（用 【对话】...【/对话】 包裹）。
请识别每段对话的说话人姓名。

规则：
1. 说话人可能是具体人名、常用称呼、或代词（他/她）
2. 如果同一个人在不同段落用了不同称呼（如"李耀"、"少年"、"他"），统一为最正式的人名
3. 如果无法判断，标注为"未知"
4. 只返回 JSON，不要 markdown 代码块，不要任何其他文字

返回格式：
{
  "assignments": [
    {"paragraph": 段落序号, "span": 对话序号, "speaker": "说话人"},
    ...
  ]
}"""

_JSON_BLOCK_RE = re.compile(r"\{[\s\S]*\}", re.MULTILINE)
_JSON_ARRAY_RE = re.compile(r"\[[\s\S]*\]", re.MULTILINE)


def _mark_dialogue_spans(
    para_text: str,
    spans: list[DialogueSegment],
    base_offset: int = 0,
) -> str:
    marked = ""
    cursor = 0
    for s_idx, span in enumerate(spans):
        local_start = base_offset + span.start
        local_end = base_offset + span.end
        marked += para_text[cursor:local_start]
        marked += f"【对话{s_idx + 1}】{para_text[local_start:local_end]}【/对话】"
        cursor = local_end
    marked += para_text[cursor:]
    return marked


class LLMAnalyzer:
    def __init__(self, settings: dict[str, str]):
        self._settings = settings
        self._ollama_available: bool | None = None
        self._client: httpx.Client | None = None
        self._available_ollama_models: list[str] = []

    def probe_ollama(self) -> bool:
        if self._ollama_available is not None:
            return self._ollama_available
        try:
            with httpx.Client(timeout=httpx.Timeout(5.0)) as client:
                resp = client.get("http://localhost:11434/api/tags")
                if resp.status_code == 200:
                    data = resp.json()
                    models = data.get("models", [])
                    self._available_ollama_models = [
                        m.get("name", m.get("model", ""))
                        for m in models
                    ]
                    self._ollama_available = True
                else:
                    self._ollama_available = False
        except Exception:
            self._ollama_available = False
        return self._ollama_available

    def _resolve_ollama_model(self) -> str:
        """Pick the best available Ollama model, preferring Chinese-capable ones."""
        configured = self._settings.get("llm_model", "")
        if configured and configured in self._available_ollama_models:
            return configured
        if configured:
            for m in self._available_ollama_models:
                if configured in m:
                    return m

        preferred = ["qwen2.5:7b", "qwen2.5:3b", "qwen2:7b", "qwen2:3b",
                     "qwen:7b", "qwen:4b", "qwen:3b", "llama3-chinese",
                     "yi:6b", "yi:9b", "llama3.1:8b", "llama3:8b",
                     "gemma2:9b", "mistral:7b"]
        for p in preferred:
            for m in self._available_ollama_models:
                if m == p or m.startswith(p):
                    return m

        if self._available_ollama_models:
            return self._available_ollama_models[0]
        return "qwen2.5:7b"

    def analyze_characters(
        self,
        speakers: dict[str, SpeakerInfo],
        progress_callback: object = None,
    ) -> list[CharacterProfile]:
        names = list(speakers.keys())
        profiles: list[CharacterProfile] = []
        total_batches = (len(names) + 4) // 5
        batch_num = 0

        for batch_start in range(0, len(names), 5):
            batch_num += 1
            batch_names = names[batch_start : batch_start + 5]

            if progress_callback:
                progress_callback(batch_num, total_batches, f"正在分析 {', '.join(batch_names[:3])}...")

            user_content_parts: list[str] = []
            print(f"[LLMAnalyzer] Batch {batch_num}/{total_batches}: {batch_names}", file=sys.stderr)

            for name in batch_names:
                info = speakers[name]
                lines_block = "\n".join(
                    f"  - {q}" for q in info.sample_quotes
                )
                user_content_parts.append(
                    f"角色: {name}\n"
                    f"台词数: {info.total_lines}\n"
                    f"总字数: {info.total_chars}\n"
                    f"示例台词:\n{lines_block}"
                )

            user_content = "\n\n---\n\n".join(user_content_parts)
            prompt_text = f"Analyze the following characters:\n\n{user_content}"

            result = self._call_llm(
                [{"role": "user", "content": prompt_text}],
                system_prompt=_SYSTEM_PROMPT,
            )

            if result is None:
                for name in batch_names:
                    profiles.append(CharacterProfile(name=name))
                continue

            if isinstance(result, list):
                for item in result:
                    if isinstance(item, dict):
                        profiles.append(self._dict_to_profile(item))
                continue

            if isinstance(result, dict):
                if any(k in result for k in ("gender", "personality", "name")):
                    profiles.append(self._dict_to_profile(result))
                else:
                    for name in batch_names:
                        profiles.append(CharacterProfile(name=name))
            else:
                for name in batch_names:
                    profiles.append(CharacterProfile(name=name))

        return profiles

    def attribute_ambiguous_quotes(
        self, unattributed: list[tuple[str, str]], known_names: list[str]
    ) -> list[dict[str, str | int]]:
        if not unattributed:
            return []

        quotes_block_parts: list[str] = []
        for idx, (quote_text, context) in enumerate(unattributed):
            ctx_str = f" [上下文: {context}]" if context else ""
            quotes_block_parts.append(f"{idx}. \"{quote_text}\"{ctx_str}")

        quotes_block = "\n".join(quotes_block_parts)
        user_content = f"Attribute each quote to a known speaker:\n\n{quotes_block}"

        result = self._call_llm(
            [{"role": "user", "content": user_content}],
            system_prompt=_ATTRIBUTION_PROMPT.format(
                names=", ".join(known_names)
            ),
        )

        if result is None:
            return [{"index": i, "speaker": "未知"} for i in range(len(unattributed))]

        assignments: list[dict[str, str | int]] = []
        try:
            if isinstance(result, list):
                for item in result:
                    if isinstance(item, dict) and "index" in item:
                        assignments.append(item)
            elif isinstance(result, dict):
                if "assignments" in result and isinstance(result["assignments"], list):
                    for item in result["assignments"]:
                        if isinstance(item, dict) and "index" in item:
                            assignments.append(item)
        except Exception:
            pass

        assigned_indices = {a.get("index") for a in assignments}
        for i in range(len(unattributed)):
            if i not in assigned_indices:
                assignments.append({"index": i, "speaker": "未知"})

        return assignments

    def identify_speakers(
        self,
        paragraph_batches: list[list[tuple[str, list[DialogueSegment], int]]],
        progress_callback: object = None,
    ) -> list[DialogueSegment]:
        """Identify speakers for dialogue spans using LLM.

        Args:
            paragraph_batches: List of batches, each batch is a list of
                (paragraph_text, list_of_dialogue_spans, base_offset) tuples.
                Max 10 paragraphs per batch.
            progress_callback: (current, total, message) -> None

        Returns:
            All segments with speaker fields populated.
        """
        all_segments: list[DialogueSegment] = []
        total_batches = len(paragraph_batches)

        for batch_idx, batch in enumerate(paragraph_batches):
            if progress_callback:
                progress_callback(batch_idx + 1, total_batches, f"正在识别第{batch_idx + 1}批对话...")

            prompt_parts: list[str] = []
            for para_idx, (para_text, spans, base_offset) in enumerate(batch):
                marked_para = _mark_dialogue_spans(para_text, spans, base_offset)
                prompt_parts.append(f"--- 段落 {para_idx + 1} ---\n{marked_para}")

            user_content = "\n".join(prompt_parts)

            print(
                f"[LLMAnalyzer] Speaker ID Batch {batch_idx + 1}/{total_batches}: "
                f"{len(batch)} paragraphs, {len(user_content)} chars",
                file=sys.stderr,
            )

            result = self._call_llm(
                [{"role": "user", "content": user_content}],
                system_prompt=_SPEAKER_ID_PROMPT,
                timeout_sec=120.0,
            )

            assignments_map: dict[tuple[int, int], str] = {}
            if result is not None:
                try:
                    items: list[dict] = []
                    if isinstance(result, list):
                        items = result
                    elif isinstance(result, dict):
                        items = result.get("assignments", []) or []
                    for item in items:
                        p = int(item.get("paragraph", item.get("p", 0)))
                        s = int(item.get("span", item.get("s", 0)))
                        speaker = str(item.get("speaker", ""))
                        if speaker:
                            assignments_map[(p, s)] = speaker
                except Exception:
                    pass

            for para_idx, (_para_text, spans, _base_offset) in enumerate(batch):
                for s_idx, span in enumerate(spans):
                    speaker = assignments_map.get((para_idx + 1, s_idx + 1))
                    span.speaker = speaker
                    all_segments.append(span)

        return all_segments

    @staticmethod
    def _dict_to_profile(data: dict) -> CharacterProfile:
        return CharacterProfile(
            name=data.get("name", "未知"),
            gender=data.get("gender", "未知"),
            age_group=data.get("age_group", "未知"),
            personality=data.get("personality", []) or [],
            role_type=data.get("role_type", "未知"),
            speaking_style=data.get("speaking_style", "") or "",
            summary=data.get("summary", "") or "",
        )

    def _call_llm(self, messages: list[dict], system_prompt: str = "", timeout_sec: float = 60.0) -> dict | list | None:
        if system_prompt:
            messages = [{"role": "system", "content": system_prompt}] + messages

        if self.probe_ollama():
            return self._call_ollama(messages, timeout_sec=timeout_sec)
        return self._call_cloud_api(messages)

    def _call_ollama(self, messages: list[dict], timeout_sec: float = 60.0) -> dict | list | None:
        model = self._resolve_ollama_model()
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        try:
            resp = httpx.post(
                "http://localhost:11434/api/chat",
                json=payload,
                timeout=httpx.Timeout(timeout_sec),
            )
            resp.raise_for_status()
            data = resp.json()
            content = data.get("message", {}).get("content", "")
            return self._parse_json_response(content)
        except Exception as exc:
            print(f"[LLMAnalyzer] Ollama call failed (model={model}): {exc}", file=sys.stderr)
            return None

    def _call_cloud_api(self, messages: list[dict]) -> dict | list | None:
        api_url = self._settings.get("api_url", "")
        api_key = self._settings.get("api_key", "")
        model_name = self._settings.get("model_name", "gpt-4o-mini")

        if not api_url or not api_key:
            print("[LLMAnalyzer] Cloud API not configured", file=sys.stderr)
            return None

        payload = {
            "model": model_name,
            "messages": messages,
            "temperature": 0.3,
        }
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        try:
            resp = httpx.post(
                api_url,
                json=payload,
                headers=headers,
                timeout=httpx.Timeout(30.0),
            )
            resp.raise_for_status()
            data = resp.json()
            content = ""
            if "choices" in data and len(data["choices"]) > 0:
                content = data["choices"][0].get("message", {}).get("content", "")
            elif "message" in data:
                content = data["message"].get("content", "")
            return self._parse_json_response(content)
        except Exception as exc:
            print(f"[LLMAnalyzer] Cloud API call failed: {exc}", file=sys.stderr)
            return None

    def _parse_json_response(self, text: str) -> dict | list | None:
        if not text:
            return None
        cleaned = text.strip()

        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)
            cleaned = cleaned.strip()

        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        array_match = _JSON_ARRAY_RE.search(cleaned)
        if array_match:
            try:
                return json.loads(array_match.group())
            except json.JSONDecodeError:
                pass

        object_match = _JSON_BLOCK_RE.search(cleaned)
        if object_match:
            try:
                return json.loads(object_match.group())
            except json.JSONDecodeError:
                pass

        print(
            f"[LLMAnalyzer] Failed to parse JSON response: {text[:200]}",
            file=sys.stderr,
        )
        return None
