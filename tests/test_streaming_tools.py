"""Exercise chapter 16 with event fixtures; no model or shell calls."""

import importlib
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


@pytest.fixture
def chapter(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "offline-test-key")
    module = importlib.import_module("chapters.ch16_streaming_tools")
    monkeypatch.setattr(module, "client", MagicMock())
    return module


def stream_events(inputs, stop_reason):
    event = SimpleNamespace
    events = []
    for index, fragments in enumerate(inputs):
        events.append(event(type="content_block_start", index=index,
                            content_block=event(type="tool_use", id=f"call-{index}",
                                                name="calculator")))
        for raw in fragments:
            events.append(event(type="content_block_delta", index=index,
                                delta=event(type="input_json_delta", partial_json=raw)))
        events.append(event(type="content_block_stop", index=index))
    events.extend([event(type="message_delta", delta=event(stop_reason=stop_reason)),
                   event(type="message_stop")])
    return events


def set_stream(chapter, events):
    chapter.client.messages.stream.return_value.__enter__.return_value = events


def test_fragmented_inputs_reassemble_in_block_order(chapter):
    set_stream(chapter, stream_events([
        ['{"expr', 'ession":"1+', '2"}'], ['{"expression":"3*4"}'],
    ], "tool_use"))
    blocks, reason = chapter.stream_one_turn([{"role": "user", "content": "calculate"}])
    assert reason == "tool_use"
    assert [block["id"] for block in blocks] == ["call-0", "call-1"]
    assert [block["input"] for block in blocks] == [{"expression": "1+2"},
                                                   {"expression": "3*4"}]
    assert all("_partial_json" not in block for block in blocks)


@pytest.mark.parametrize("reason", ["max_tokens", "model_context_window_exceeded"])
def test_truncation_is_detected_before_json_parse(chapter, reason):
    set_stream(chapter, stream_events([['{"expression":"1+']], reason))
    with pytest.raises(RuntimeError, match=f"truncated \\({reason}\\)"):
        chapter.stream_one_turn([{"role": "user", "content": "calculate"}])


@pytest.mark.parametrize("bad_input,notice", [
    ('{"expression":', "invalid JSON"),
    ("[]", "must be a JSON object"),
])
def test_bad_second_call_prevents_entire_batch(chapter, monkeypatch, bad_input, notice):
    set_stream(chapter, stream_events([
        ['{"expression":"1+2"}'], [bad_input],
    ], "tool_use"))
    dispatch = MagicMock()
    monkeypatch.setattr(chapter, "run_tool", dispatch)
    with pytest.raises(RuntimeError, match=notice):
        chapter.agent_loop("calculate")
    dispatch.assert_not_called()


@pytest.mark.parametrize("reason", [None, "pause_turn", "refusal", "future_reason"])
def test_unsupported_stop_is_reported(chapter, reason):
    set_stream(chapter, stream_events([], reason))
    with pytest.raises(RuntimeError, match="unexpected stop_reason"):
        chapter.stream_one_turn([{"role": "user", "content": "calculate"}])


def test_agent_dispatches_valid_tools_then_finishes(chapter, monkeypatch):
    chapter.client.messages.stream.return_value.__enter__.side_effect = [
        stream_events([['{"expression":"1+2"}']], "tool_use"),
        stream_events([], "end_turn"),
    ]
    dispatch = MagicMock(return_value="3")
    monkeypatch.setattr(chapter, "run_tool", dispatch)
    chapter.agent_loop("calculate")
    dispatch.assert_called_once_with("calculator", {"expression": "1+2"})
    assert chapter.client.messages.stream.call_count == 2
