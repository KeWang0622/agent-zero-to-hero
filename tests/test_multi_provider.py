"""Tests for the multi-provider adapter (chapter 17).
No API calls — we test the message-conversion logic with mocked HTTP."""

import importlib.util
import sys
from pathlib import Path


def _load_ch17():
    spec = importlib.util.spec_from_file_location(
        "ch17", Path(__file__).resolve().parent.parent / "chapters" /
                "ch17_multi_provider.py")
    m = importlib.util.module_from_spec(spec)
    sys.modules["ch17"] = m
    spec.loader.exec_module(m)
    return m


def test_anthropic_msg_conversion():
    ch = _load_ch17()
    user = ch.AgentMessage("user", text="hi")
    converted = ch.AnthropicProvider._msg(user)
    assert converted == {"role": "user", "content": "hi"}


def test_anthropic_tool_result_conversion():
    ch = _load_ch17()
    tool = ch.AgentMessage("tool", text="42", tool_call_id="t1")
    converted = ch.AnthropicProvider._msg(tool)
    # anthropic tool results live in a USER role with tool_result content blocks
    assert converted["role"] == "user"
    assert converted["content"][0]["type"] == "tool_result"
    assert converted["content"][0]["tool_use_id"] == "t1"


def test_openai_args_are_string():
    """OpenAI's foot-gun: arguments MUST be a JSON string in tool_calls."""
    ch = _load_ch17()
    asst = ch.AgentMessage("assistant",
                           tool_calls=[ch.ToolCall("c1", "calc", {"a": 1})])
    converted = ch.OpenAIProvider._msg(asst)
    args = converted["tool_calls"][0]["function"]["arguments"]
    assert isinstance(args, str)              # JSON string, not dict
    import json
    assert json.loads(args) == {"a": 1}


def test_openai_parse_strings_to_dict():
    """When parsing OpenAI's response, args come back as strings — we json.loads them."""
    ch = _load_ch17()
    fake = {"choices": [{"finish_reason": "tool_calls",
                          "message": {"content": "thinking",
                                      "tool_calls": [{"id": "c1",
                                                     "type": "function",
                                                     "function": {"name": "calc",
                                                                  "arguments": '{"a":1}'}}]}}]}
    msg = ch.OpenAIProvider._parse(fake)
    assert msg.tool_calls[0].args == {"a": 1}      # parsed dict, not string
    assert msg.stop == "tool_use"


def test_gemini_no_dedicated_stop_reason():
    """Gemini's foot-gun: stop_reason is STOP even when tool was called.
    Detection requires scanning parts."""
    ch = _load_ch17()
    fake = {"candidates": [{"content": {"role": "model",
                                         "parts": [{"functionCall":
                                                    {"name": "calc", "args": {"a": 1}}}]},
                            "finishReason": "STOP"}]}
    msg = ch.GeminiProvider._parse(fake)
    assert msg.stop == "tool_use"               # detected via parts, not finishReason
    assert msg.tool_calls[0].args == {"a": 1}
