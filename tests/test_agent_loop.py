"""Tests for the canonical agent loop pattern (chapters 5-7).
We test loop CONTROL FLOW with a mock LLM — no API calls."""

from dataclasses import dataclass


@dataclass
class _Block:
    type: str
    text: str = ""
    name: str = ""
    id: str = ""
    input: dict = None


@dataclass
class _Response:
    content: list
    stop_reason: str


class MockLLM:
    """A fake `client.messages.create` that returns scripted responses."""
    def __init__(self, scripted: list[_Response]):
        self.scripted = list(scripted)
        self.calls = 0
    def messages_create(self, **kwargs):
        self.calls += 1
        return self.scripted.pop(0)


def _agent_loop(client, msgs, tools, dispatch, max_turns=10):
    """Reference implementation under test — same shape as ch05."""
    for _ in range(max_turns):
        r = client.messages_create(messages=msgs, tools=tools)
        msgs.append({"role": "assistant", "content": r.content})
        if r.stop_reason != "tool_use":
            return r
        results = [{"type": "tool_result",
                    "tool_use_id": b.id,
                    "content": dispatch(b.name, b.input)}
                   for b in r.content if b.type == "tool_use"]
        msgs.append({"role": "user", "content": results})
    raise RuntimeError("max_turns exceeded")


def test_loop_exits_on_end_turn():
    client = MockLLM([
        _Response([_Block("text", text="hello")], "end_turn"),
    ])
    r = _agent_loop(client, [{"role": "user", "content": "hi"}], [], lambda *_: "")
    assert r.stop_reason == "end_turn"
    assert client.calls == 1


def test_loop_dispatches_tool_use():
    seen = []
    def dispatch(name, args):
        seen.append((name, args))
        return "42"

    client = MockLLM([
        _Response([_Block("tool_use", name="calc", id="t1", input={"x": 1})],
                  "tool_use"),
        _Response([_Block("text", text="answer is 42")], "end_turn"),
    ])
    msgs = [{"role": "user", "content": "go"}]
    r = _agent_loop(client, msgs, [], dispatch)
    assert r.stop_reason == "end_turn"
    assert seen == [("calc", {"x": 1})]
    # messages array shape: user, assistant(tool_use), user(tool_result), assistant(text)
    assert len(msgs) == 4
    assert msgs[2]["role"] == "user"
    assert msgs[2]["content"][0]["type"] == "tool_result"


def test_parallel_tool_calls_in_one_turn():
    client = MockLLM([
        _Response([
            _Block("tool_use", name="a", id="1", input={}),
            _Block("tool_use", name="b", id="2", input={}),
            _Block("tool_use", name="c", id="3", input={}),
        ], "tool_use"),
        _Response([_Block("text", text="done")], "end_turn"),
    ])
    msgs = [{"role": "user", "content": "go"}]
    _agent_loop(client, msgs, [], lambda n, _: f"r-{n}")
    # all three results land in ONE user message — the parallel-tool rule
    user_msg_with_results = msgs[2]
    assert user_msg_with_results["role"] == "user"
    assert len(user_msg_with_results["content"]) == 3


def test_max_turns_guard():
    """A pathological model that never stops calling tools must hit the cap."""
    bad = [_Response([_Block("tool_use", name="loop", id=str(i), input={})],
                     "tool_use") for i in range(50)]
    client = MockLLM(bad)
    msgs = [{"role": "user", "content": "go"}]
    import pytest
    with pytest.raises(RuntimeError):
        _agent_loop(client, msgs, [], lambda *_: "x", max_turns=5)
