"""Protocol fixtures test replay and failure boundaries, not model intelligence."""

import json

import httpx
import pytest

from chapters.ch17b_responses import dispatch, run_agent


def call(call_id="call_1", arguments='{"operation":"multiply","a":17,"b":23}'):
    return {"type": "function_call", "id": "fc_" + call_id, "call_id": call_id,
            "name": "arithmetic", "arguments": arguments, "status": "completed"}


def fixture_client(responses, requests):
    def handle(request):
        requests.append(json.loads(request.content))
        return httpx.Response(200, json=responses.pop(0))
    return httpx.Client(transport=httpx.MockTransport(handle))


def test_continuation_uses_call_id_and_keeps_server_state():
    requests = []
    responses = [
        {"id": "resp_1", "status": "completed", "output": [
            {"type": "reasoning", "id": "rs_1", "summary": []}, call(), call("call_2")]},
        {"id": "resp_2", "status": "completed", "output": [
            {"type": "message", "content": [{"type": "output_text", "text": "391"}]}]},
    ]
    with fixture_client(responses, requests) as client:
        assert run_agent(client, "fixture-model", "multiply") == "391"
    assert requests[1]["previous_response_id"] == "resp_1"
    assert [item["call_id"] for item in requests[1]["input"]] == ["call_1", "call_2"]
    assert json.loads(requests[1]["input"][0]["output"]) == {"result": 391}
    assert requests[1]["instructions"] == requests[0]["instructions"]
    assert requests[0]["store"] is True


@pytest.mark.parametrize("arguments", ["{", "[]", '{"operation":"multiply","a":true,"b":2}',
                                     '{"operation":"multiply","a":1e1000,"b":2}',
                                     '{"operation":"divide","a":2,"b":1}'])
def test_bad_arguments_return_tool_errors(arguments):
    assert "error" in json.loads(dispatch(call(arguments=arguments)))


@pytest.mark.parametrize("status", ["incomplete", "failed", "cancelled", "unknown"])
def test_noncompleted_response_never_dispatches(status, monkeypatch):
    def forbidden(_):
        pytest.fail("must not dispatch tools from a non-completed response")
    monkeypatch.setattr("chapters.ch17b_responses.dispatch", forbidden)
    with fixture_client([{"id": "r", "status": status, "output": [call()]}], []) as client:
        with pytest.raises(RuntimeError, match="not completed"):
            run_agent(client, "fixture-model", "test")


def test_tool_budget_checked_before_any_dispatch(monkeypatch):
    monkeypatch.setattr("chapters.ch17b_responses.dispatch", lambda _: pytest.fail("dispatch"))
    with fixture_client([{"id": "r", "status": "completed", "output": [call(), call()]}], []) as client:
        with pytest.raises(RuntimeError, match="budget"):
            run_agent(client, "fixture-model", "test", max_tool_calls=1)


def test_http_error_is_not_parsed_as_a_model_response():
    with httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(429))) as client:
        with pytest.raises(httpx.HTTPStatusError):
            run_agent(client, "fixture-model", "test")


def test_refusal_is_not_an_empty_success():
    result = {"id": "r", "status": "completed", "output": [
        {"type": "message", "content": [{"type": "refusal", "refusal": "No"}]}]}
    with fixture_client([result], []) as client:
        with pytest.raises(RuntimeError, match="refused"):
            run_agent(client, "fixture-model", "test")


def test_turn_limit_stops_a_repeating_model():
    with fixture_client([{"id": "r", "status": "completed", "output": [call()]}], []) as client:
        with pytest.raises(RuntimeError, match="turn budget"):
            run_agent(client, "fixture-model", "test", max_turns=1)
