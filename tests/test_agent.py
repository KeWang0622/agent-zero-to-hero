"""Tests for agent.py — the production harness.
No API key required. Tests the integration logic with mocks."""

import importlib.util
import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

# the import requires ANTHROPIC_API_KEY in env at runtime, but only when main()
# runs. importing the module doesn't fail.
os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-fake-for-tests")


def _load_agent():
    spec = importlib.util.spec_from_file_location(
        "agent_under_test", Path(__file__).resolve().parent.parent / "agent.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["agent_under_test"] = m
    spec.loader.exec_module(m)
    return m


# ---- meter --------------------------------------------------------------

def test_meter_tracks_tokens_and_dollars():
    a = _load_agent()
    m = a.Meter()
    usage = MagicMock(input_tokens=1000, output_tokens=500,
                      cache_creation_input_tokens=200,
                      cache_read_input_tokens=800)
    spent = m.add(usage)
    # input 1000 * $3/1M + output 500 * $15/1M + cache_create 200 * $3.75/1M
    # + cache_read 800 * $0.30/1M = 0.003 + 0.0075 + 0.00075 + 0.00024 = 0.01149
    assert abs(spent - 0.01149) < 1e-6
    assert m.input == 1000
    assert m.output == 500
    assert m.cache_create == 200
    assert m.cache_read == 800
    assert m.turns == 1


def test_meter_status_string():
    a = _load_agent()
    m = a.Meter()
    s = m.status()
    assert "$0.0000" in s
    assert "in 0" in s


# ---- session ------------------------------------------------------------

def test_session_jsonl_roundtrip(tmp_path, monkeypatch):
    a = _load_agent()
    monkeypatch.setattr(a, "SESSION_DIR", tmp_path)

    s = a.Session()
    s.append_user("hi")
    s.append_assistant([{"type": "text", "text": "hello"}])
    s.append_tool_results([{"type": "tool_result",
                            "tool_use_id": "x", "content": "42"}])

    s2 = a.Session(s.id)
    assert len(s2.messages) == 3
    assert s2.messages[0] == {"role": "user", "content": "hi"}


def test_session_orphan_user_recovery(tmp_path, monkeypatch):
    """If the prior session crashed mid-turn (user message without assistant
    reply), --resume should drop the orphan."""
    a = _load_agent()
    monkeypatch.setattr(a, "SESSION_DIR", tmp_path)
    s = a.Session()
    s.append_user("first")
    s.append_assistant([{"type": "text", "text": "ok"}])
    s.append_user("second — this never got a reply (crash here)")

    # simulate restart: re-load and recover
    s2 = a.Session(s.id)
    assert len(s2.messages) == 3
    s2.truncate_orphan_user()
    assert len(s2.messages) == 2
    assert s2.messages[-1]["role"] == "assistant"


def test_session_compact_log_entry(tmp_path, monkeypatch):
    a = _load_agent()
    monkeypatch.setattr(a, "SESSION_DIR", tmp_path)
    s = a.Session()
    s.replace_messages([{"role": "user", "content": "summary..."}],
                       reason="manual test")
    # the compact entry must be on disk so audits can see it
    lines = s.path.read_text().splitlines()
    assert any(json.loads(l).get("type") == "compact" for l in lines)


def test_session_replays_compaction_and_later_turns(tmp_path, monkeypatch):
    a = _load_agent()
    monkeypatch.setattr(a, "SESSION_DIR", tmp_path)
    session = a.Session()
    session.append_user("old detailed context")
    session.append_assistant([{"type": "text", "text": "old reply"}])
    summary = [{"role": "user", "content": "summary of prior work"},
               {"role": "assistant", "content": [{"type": "text", "text": "ready"}]}]
    session.replace_messages(summary, reason="test")
    session.append_user("continue from the summary")
    session.append_assistant([{"type": "text", "text": "done"}])

    resumed = a.Session(session.id)
    assert resumed.messages == session.messages
    assert len(resumed.messages) == 4
    assert "old detailed context" not in str(resumed.messages)


def test_session_replays_old_compact_records_without_losing_history(tmp_path, monkeypatch):
    a = _load_agent()
    monkeypatch.setattr(a, "SESSION_DIR", tmp_path)
    session = a.Session()
    session.append_user("legacy history")
    session._write({"type": "compact", "len_after": 1, "reason": "old format"})
    assert a.Session(session.id).messages == session.messages


# ---- compaction safety -------------------------------------------------

def test_is_tool_use_assistant_detector():
    a = _load_agent()
    assert a._is_tool_use_assistant({"role": "assistant",
                                     "content": [{"type": "tool_use",
                                                  "id": "x", "name": "Bash",
                                                  "input": {}}]})
    assert not a._is_tool_use_assistant({"role": "assistant",
                                         "content": [{"type": "text",
                                                      "text": "hi"}]})
    assert not a._is_tool_use_assistant({"role": "user", "content": "hi"})


def test_compact_does_not_split_tool_use(tmp_path, monkeypatch):
    """The summarizer call must not END on a tool_use assistant message —
    that would violate the API's tool_use → tool_result rule."""
    a = _load_agent()
    monkeypatch.setattr(a, "SESSION_DIR", tmp_path)
    monkeypatch.setattr(a, "KEEP_RECENT", 1)

    captured_messages = {}
    fake_response = MagicMock()
    fake_response.content = [MagicMock(type="text", text="summary text")]
    fake_client = MagicMock()
    def fake_create(**kwargs):
        captured_messages["msgs"] = kwargs["messages"]
        return fake_response
    fake_client.messages.create = fake_create

    msgs = [
        {"role": "user", "content": "first"},
        {"role": "assistant", "content": [{"type": "text", "text": "ok"}]},
        {"role": "user", "content": "do this"},
        {"role": "assistant",
         "content": [{"type": "tool_use", "id": "t1", "name": "Bash",
                      "input": {"command": "ls"}}]},
        {"role": "user",
         "content": [{"type": "tool_result", "tool_use_id": "t1", "content": "ok"}]},
        {"role": "assistant", "content": [{"type": "text", "text": "done"}]},
    ]

    a.compact_messages(fake_client, msgs)
    sent = captured_messages["msgs"]
    # the LAST message before the summarizer instruction must NOT be an
    # assistant tool_use — otherwise the API rejects the call
    assert sent[-1]["role"] == "user"               # the "Summarize..." prompt
    assert not a._is_tool_use_assistant(sent[-2])


# ---- retries -----------------------------------------------------------

def test_with_retries_backs_off_on_rate_limit(monkeypatch):
    a = _load_agent()
    import anthropic
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise anthropic.APIConnectionError(request=MagicMock())
        return "ok"

    # patch sleep so the test is fast
    import time as _time
    monkeypatch.setattr(_time, "sleep", lambda *_: None)
    result = a.with_retries(flaky, max_attempts=5)
    assert result == "ok"
    assert calls["n"] == 3


def test_with_retries_eventually_raises(monkeypatch):
    a = _load_agent()
    import anthropic
    import time as _time
    monkeypatch.setattr(_time, "sleep", lambda *_: None)

    def always_fails():
        raise anthropic.APIConnectionError(request=MagicMock())

    import pytest
    with pytest.raises(anthropic.APIConnectionError):
        a.with_retries(always_fails, max_attempts=3)


# ---- caching wrappers --------------------------------------------------

def test_build_system_param_cached_when_enabled(monkeypatch):
    a = _load_agent()
    monkeypatch.setattr(a, "USE_CACHE", True)
    out = a._build_system_param("hi")
    assert isinstance(out, list)
    assert out[0]["cache_control"]["type"] == "ephemeral"


def test_build_system_param_string_when_disabled(monkeypatch):
    a = _load_agent()
    monkeypatch.setattr(a, "USE_CACHE", False)
    out = a._build_system_param("hi")
    assert out == "hi"


def test_build_tools_param_caches_last_tool(monkeypatch):
    a = _load_agent()
    monkeypatch.setattr(a, "USE_CACHE", True)
    tools = a._build_tools_param()
    assert "cache_control" in tools[-1]
    assert "cache_control" not in tools[0]


# ---- tool dispatch -----------------------------------------------------

def test_tool_read_existing_file(tmp_path):
    a = _load_agent()
    p = tmp_path / "x.txt"
    p.write_text("hello world")
    assert a.tool_read(str(p)) == "hello world"


def test_tool_read_missing_file(tmp_path):
    a = _load_agent()
    assert a.tool_read(str(tmp_path / "missing.txt")).startswith("ERROR")


def test_tool_edit_unique_match(tmp_path):
    a = _load_agent()
    p = tmp_path / "x.py"
    p.write_text("def foo():\n    pass\n")
    out = a.tool_edit(str(p), "    pass", "    return 42")
    assert "+    return 42" in out
    assert p.read_text() == "def foo():\n    return 42\n"


def test_tool_edit_ambiguous_match(tmp_path):
    a = _load_agent()
    p = tmp_path / "x.py"
    p.write_text("x = 1\nx = 1\n")
    out = a.tool_edit(str(p), "x = 1", "x = 2")
    assert out.startswith("ERROR")
    assert "appears 2 times" in out


def test_tool_edit_no_match(tmp_path):
    a = _load_agent()
    p = tmp_path / "x.py"
    p.write_text("x = 1\n")
    out = a.tool_edit(str(p), "y = 2", "y = 3")
    assert out.startswith("ERROR")
    assert "not found" in out


def test_tool_glob(tmp_path):
    a = _load_agent()
    (tmp_path / "a.py").touch()
    (tmp_path / "b.py").touch()
    (tmp_path / "c.txt").touch()
    out = a.tool_glob("*.py", str(tmp_path))
    assert out.count(".py") == 2
    assert ".txt" not in out
