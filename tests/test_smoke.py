"""Smoke tests for agent.py — proves the harness boots end-to-end with a
fake Anthropic client. Verifies the loop, tool dispatch, session writing,
permissions, and cost metering all integrate. No API key required."""

import importlib.util
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

os.environ.setdefault("ANTHROPIC_API_KEY", "sk-ant-fake-for-tests")
os.environ["AZH_PERMISSION"] = "allow"      # auto-approve in tests


def _load_agent():
    spec = importlib.util.spec_from_file_location(
        "agent_smoke", Path(__file__).resolve().parent.parent / "agent.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["agent_smoke"] = m
    spec.loader.exec_module(m)
    return m


def _fake_response(blocks, stop_reason, usage=None):
    """Build a fake Anthropic response object."""
    r = MagicMock()
    r.content = []
    for b in blocks:
        block = MagicMock()
        for k, v in b.items():
            setattr(block, k, v)
        block.type = b["type"]
        if b["type"] == "text":
            block.text = b["text"]
        elif b["type"] == "tool_use":
            block.name = b["name"]
            block.id = b["id"]
            block.input = b["input"]
        block.model_dump = lambda b=b: b
        r.content.append(block)
    r.stop_reason = stop_reason
    r.usage = usage or MagicMock(input_tokens=100, output_tokens=50,
                                 cache_creation_input_tokens=0,
                                 cache_read_input_tokens=0)
    return r


def test_smoke_one_turn_no_tools(tmp_path, monkeypatch):
    """Agent says hi, claude says hi, loop exits."""
    a = _load_agent()
    monkeypatch.setattr(a, "SESSION_DIR", tmp_path)
    monkeypatch.setattr(a, "USE_STREAM", False)

    fake_client = MagicMock()
    fake_client.messages.create.return_value = _fake_response(
        [{"type": "text", "text": "hello!"}], "end_turn")

    session = a.Session()
    meter = a.Meter()
    a.agent_turn(fake_client, session, "you are nice", meter, "hi")

    # session must have user msg + assistant msg
    assert len(session.messages) == 2
    assert session.messages[0]["content"] == "hi"
    assert session.messages[1]["role"] == "assistant"
    # meter must have logged one turn
    assert meter.turns == 1
    assert meter.input == 100
    assert meter.output == 50


def test_smoke_one_tool_round_trip(tmp_path, monkeypatch):
    """Claude calls a tool, gets a result, then ends."""
    a = _load_agent()
    monkeypatch.setattr(a, "SESSION_DIR", tmp_path)
    monkeypatch.setattr(a, "USE_STREAM", False)

    target = tmp_path / "x.txt"
    target.write_text("hello world")

    fake_client = MagicMock()
    fake_client.messages.create.side_effect = [
        # turn 1: tool_use
        _fake_response([{"type": "tool_use", "id": "t1", "name": "Read",
                         "input": {"file_path": str(target)}}], "tool_use"),
        # turn 2: end_turn with text
        _fake_response([{"type": "text", "text": "the file says hello world"}],
                       "end_turn"),
    ]

    session = a.Session()
    meter = a.Meter()
    a.agent_turn(fake_client, session, "be helpful", meter, "read x.txt")

    # session shape: user → assistant(tool_use) → user(tool_result) → assistant(text)
    assert len(session.messages) == 4
    assert session.messages[0]["content"] == "read x.txt"
    assert session.messages[1]["role"] == "assistant"
    assert session.messages[2]["role"] == "user"           # tool_results
    assert isinstance(session.messages[2]["content"], list)
    assert session.messages[2]["content"][0]["type"] == "tool_result"
    assert session.messages[3]["role"] == "assistant"
    assert meter.turns == 2


def test_smoke_parallel_tool_calls(tmp_path, monkeypatch):
    """Two tool_use blocks in one assistant turn → batched into one user message."""
    a = _load_agent()
    monkeypatch.setattr(a, "SESSION_DIR", tmp_path)
    monkeypatch.setattr(a, "USE_STREAM", False)

    fake_client = MagicMock()
    fake_client.messages.create.side_effect = [
        _fake_response([
            {"type": "tool_use", "id": "t1", "name": "Glob",
             "input": {"pattern": "*.py", "path": str(tmp_path)}},
            {"type": "tool_use", "id": "t2", "name": "Glob",
             "input": {"pattern": "*.md", "path": str(tmp_path)}},
        ], "tool_use"),
        _fake_response([{"type": "text", "text": "found stuff"}], "end_turn"),
    ]

    session = a.Session()
    meter = a.Meter()
    a.agent_turn(fake_client, session, "you are helpful", meter, "find files")

    # CRITICAL: both tool_results must be in ONE user message
    tool_result_msg = session.messages[2]
    assert tool_result_msg["role"] == "user"
    assert isinstance(tool_result_msg["content"], list)
    assert len(tool_result_msg["content"]) == 2
    ids = {b["tool_use_id"] for b in tool_result_msg["content"]}
    assert ids == {"t1", "t2"}


def test_smoke_permission_denied(tmp_path, monkeypatch):
    """When the user denies a Bash call, the harness sends back is_error=true."""
    a = _load_agent()
    monkeypatch.setattr(a, "SESSION_DIR", tmp_path)
    monkeypatch.setattr(a, "USE_STREAM", False)
    monkeypatch.setattr(a, "DEFAULT_PERMISSION", "deny")     # force deny

    fake_client = MagicMock()
    fake_client.messages.create.side_effect = [
        _fake_response([{"type": "tool_use", "id": "t1", "name": "Bash",
                         "input": {"command": "rm -rf /"}}], "tool_use"),
        _fake_response([{"type": "text", "text": "okay, I won't"}], "end_turn"),
    ]

    session = a.Session()
    meter = a.Meter()
    a.agent_turn(fake_client, session, "be safe", meter, "delete everything")

    tool_result = session.messages[2]["content"][0]
    assert tool_result["is_error"] is True
    assert "denied" in tool_result["content"].lower()


def test_smoke_unknown_tool(tmp_path, monkeypatch):
    """Hallucinated tool name returns a graceful error, doesn't crash."""
    a = _load_agent()
    monkeypatch.setattr(a, "SESSION_DIR", tmp_path)
    monkeypatch.setattr(a, "USE_STREAM", False)

    fake_client = MagicMock()
    fake_client.messages.create.side_effect = [
        _fake_response([{"type": "tool_use", "id": "t1", "name": "Hallucinated",
                         "input": {}}], "tool_use"),
        _fake_response([{"type": "text", "text": "sorry"}], "end_turn"),
    ]

    session = a.Session()
    meter = a.Meter()
    a.agent_turn(fake_client, session, "be helpful", meter, "use a fake tool")

    tool_result = session.messages[2]["content"][0]
    assert "unknown tool" in tool_result["content"].lower()
    assert meter.turns == 2          # both calls completed; loop didn't crash


def test_smoke_cli_session_dir_flag(tmp_path, monkeypatch, capsys):
    """`python agent.py --session-dir` works WITHOUT API key."""
    a = _load_agent()
    monkeypatch.setattr(a, "SESSION_DIR", tmp_path / "test_sessions")
    monkeypatch.setattr(sys, "argv", ["agent.py", "--session-dir"])
    a.main()
    captured = capsys.readouterr()
    assert str(tmp_path / "test_sessions") in captured.out
