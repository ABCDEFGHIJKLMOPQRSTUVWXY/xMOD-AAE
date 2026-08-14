# -*- coding: utf-8 -*-
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

import pytest

import httpx

from character_engine.llm_analyzer import LLMAnalyzer


def _make_analyzer(settings):
    return LLMAnalyzer(settings)


def test_mode_cloud_routes_to_cloud_api(monkeypatch):
    analyzer = _make_analyzer({"llm_mode": "cloud"})

    def boom():
        raise AssertionError("probe_ollama should not be called in cloud mode")

    monkeypatch.setattr(analyzer, "probe_ollama", boom)
    monkeypatch.setattr(
        analyzer, "_call_ollama", lambda messages, timeout_sec=60.0: "ollama-sentinel"
    )
    monkeypatch.setattr(
        analyzer, "_call_cloud_api", lambda messages, timeout_sec=30.0: "cloud-result"
    )

    result = analyzer._call_llm([{"role": "user", "content": "hi"}])
    assert result == "cloud-result"


def test_mode_ollama_routes_to_ollama(monkeypatch):
    analyzer = _make_analyzer({"llm_mode": "ollama"})
    monkeypatch.setattr(analyzer, "probe_ollama", lambda: True)
    monkeypatch.setattr(
        analyzer, "_call_ollama", lambda messages, timeout_sec=60.0: "ollama-result"
    )
    monkeypatch.setattr(
        analyzer, "_call_cloud_api", lambda messages, timeout_sec=30.0: "cloud-sentinel"
    )

    result = analyzer._call_llm([{"role": "user", "content": "hi"}])
    assert result == "ollama-result"


def test_mode_ollama_raises_when_ollama_unavailable(monkeypatch):
    analyzer = _make_analyzer({"llm_mode": "ollama"})
    monkeypatch.setattr(analyzer, "probe_ollama", lambda: False)
    monkeypatch.setattr(
        analyzer, "_call_ollama", lambda messages, timeout_sec=60.0: "ollama-sentinel"
    )

    with pytest.raises(RuntimeError, match="Ollama"):
        analyzer._call_llm([{"role": "user", "content": "hi"}])


def test_mode_cloud_raises_when_not_configured(monkeypatch):
    analyzer = _make_analyzer({"llm_mode": "cloud"})
    monkeypatch.setattr(analyzer, "probe_ollama", lambda: True)

    def ollama_sentinel(messages, timeout_sec=60.0):
        raise AssertionError("_call_ollama should not be called in cloud mode")

    monkeypatch.setattr(analyzer, "_call_ollama", ollama_sentinel)

    with pytest.raises(RuntimeError, match="云端 API 未配置"):
        analyzer._call_llm([{"role": "user", "content": "hi"}])


def _make_cloud_response(content):
    class Resp:
        def raise_for_status(self):
            pass

        def json(self):
            return {"choices": [{"message": {"content": content}}]}

    return Resp()


def test_cloud_api_sends_response_format(monkeypatch):
    analyzer = _make_analyzer(
        {"llm_mode": "cloud", "llm_endpoint": "https://api.example.com/v1/chat/completions", "llm_api_key": "k"}
    )
    captured = {}

    def fake_post(url, json, headers, timeout):
        captured["payload"] = json
        return _make_cloud_response('{"name": "张三"}')

    monkeypatch.setattr(
        "character_engine.llm_analyzer.httpx.post", fake_post
    )

    result = analyzer._call_cloud_api([{"role": "user", "content": "hi"}])

    assert captured["payload"]["response_format"] == {"type": "json_object"}
    assert result == {"name": "张三"}


def test_cloud_api_retries_without_response_format_on_4xx(monkeypatch):
    analyzer = _make_analyzer(
        {"llm_mode": "cloud", "llm_endpoint": "https://api.example.com/v1/chat/completions", "llm_api_key": "k"}
    )
    calls = []

    def make_400_error():
        request = httpx.Request("POST", "https://api.example.com/v1/chat/completions")
        response = httpx.Response(400, request=request)
        return httpx.HTTPStatusError("400 Bad Request", request=request, response=response)

    def fake_post(url, json, headers, timeout):
        calls.append(json)
        if len(calls) == 1:
            raise make_400_error()
        return _make_cloud_response('{"name": "李四"}')

    monkeypatch.setattr(
        "character_engine.llm_analyzer.httpx.post", fake_post
    )

    result = analyzer._call_cloud_api([{"role": "user", "content": "hi"}])

    assert len(calls) == 2
    assert "response_format" in calls[0]
    assert "response_format" not in calls[1]
    assert result == {"name": "李四"}


def test_cloud_api_timeout_does_not_retry(monkeypatch):
    """超时等非 4xx 错误不应去掉 response_format 重试同一 payload。"""
    analyzer = _make_analyzer(
        {"llm_mode": "cloud", "llm_endpoint": "https://api.example.com/v1/chat/completions", "llm_api_key": "k"}
    )
    calls = []

    def fake_post(url, json, headers, timeout):
        calls.append(json)
        raise httpx.ReadTimeout("read timed out", request=httpx.Request("POST", url))

    monkeypatch.setattr(
        "character_engine.llm_analyzer.httpx.post", fake_post
    )

    result = analyzer._call_cloud_api([{"role": "user", "content": "hi"}])

    assert len(calls) == 1
    assert result is None


def test_default_mode_is_ollama(monkeypatch):
    analyzer = _make_analyzer({})
    monkeypatch.setattr(analyzer, "probe_ollama", lambda: True)
    monkeypatch.setattr(
        analyzer, "_call_ollama", lambda messages, timeout_sec=60.0: "ollama-result"
    )
    monkeypatch.setattr(
        analyzer, "_call_cloud_api", lambda messages: "cloud-sentinel"
    )

    result = analyzer._call_llm([{"role": "user", "content": "hi"}])
    assert result == "ollama-result"
