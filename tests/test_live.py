"""Mock tests for the live Claude adapter. No network, no API key, no live call. All data is SYNTHETIC."""
import asyncio
from types import SimpleNamespace as NS

import pytest

from claims_agent.agent import run_agent
from claims_agent.checks import CHECKS, SUMMARY_TOOL
from claims_agent.live import FALLBACK_BETA, AnthropicModel


def usage(i=100, o=20):
    return NS(input_tokens=i, output_tokens=o, cache_creation_input_tokens=0, cache_read_input_tokens=0)


def tool_turn(*names):
    blocks = [NS(type="thinking", thinking="", signature="sig")] + [NS(type="tool_use", id=f"toolu_{n}", name=n, input={}) for n in names]
    return NS(content=blocks, stop_reason="tool_use", usage=usage())


def text_turn(text, stop_reason="end_turn"):
    return NS(content=[NS(type="text", text=text)], stop_reason=stop_reason, usage=usage())


class FakeClient:
    """Stands in for anthropic.Anthropic(): records every request and replays scripted responses."""

    def __init__(self, responses, count=500, count_fails=False):
        self.requests, self.responses = [], list(responses)
        self.count_requests = []

        def create(**kwargs):
            self.requests.append({**kwargs, "messages": list(kwargs["messages"])})
            return self.responses.pop(0)

        def count_tokens(**kwargs):
            if count_fails:
                raise RuntimeError("offline")
            self.count_requests.append(kwargs)
            return NS(input_tokens=count)

        self.beta = NS(messages=NS(create=create))
        self.messages = NS(count_tokens=count_tokens)


FULL_RUN = [tool_turn(SUMMARY_TOOL), tool_turn(*CHECKS), text_turn("All four checks ran.")]


def test_request_shape_and_tool_round_trip(case_dir):
    client = FakeClient(FULL_RUN)
    record = asyncio.run(run_agent(case_dir("mixed_standard"), model=AnthropicModel(client=client)))
    assert record["status"] == "COMPLETE" and record["model_calls"] == 3
    first, second, third = client.requests
    assert first["model"] == "claude-opus-5-5" and first["betas"] == [FALLBACK_BETA] and first["fallbacks"] == "default"
    assert "thinking" not in first and "temperature" not in first and "tool_choice" not in first
    assert {t["name"] for t in first["tools"]} == {SUMMARY_TOOL, *CHECKS}
    assert all(t["input_schema"]["additionalProperties"] is False for t in first["tools"])
    assert [m["role"] for m in first["messages"]] == ["user"]
    # Assistant blocks (thinking included) go back unchanged, and results answer every tool_use id in one user message.
    assert second["messages"][1]["content"] is FULL_RUN[0].content
    assert [m["role"] for m in third["messages"]] == ["user", "assistant", "user", "assistant", "user"]
    results = third["messages"][4]["content"]
    assert [r["tool_use_id"] for r in results] == [f"toolu_{name}" for name in CHECKS]
    assert all(r["type"] == "tool_result" for r in results)


def test_history_is_append_only(case_dir):
    client = FakeClient(FULL_RUN)
    asyncio.run(run_agent(case_dir("clean"), model=AnthropicModel(client=client)))
    for earlier, later in zip(client.requests, client.requests[1:]):
        assert later["messages"][:len(earlier["messages"])] == earlier["messages"]


def test_planted_text_never_sent_to_the_api(case_dir):
    from claims_agent.seeds import PLANTED_TEXT
    client = FakeClient(FULL_RUN)
    record = asyncio.run(run_agent(case_dir("planted_instruction"), model=AnthropicModel(client=client)))
    assert PLANTED_TEXT in str(record["results"]["detect_duplicates"]["flags"])
    assert PLANTED_TEXT not in str([r["messages"] for r in client.requests])


def test_cost_uses_reported_usage_and_model_prices(case_dir):
    client = FakeClient(FULL_RUN)
    record = asyncio.run(run_agent(case_dir("clean"), model=AnthropicModel(client=client)))
    assert record["cost_usd"] == pytest.approx(3 * (100 * 4.0 / 1e6 + 20 * 20.0 / 1e6))


def test_cost_cap_blocks_the_call_before_it_is_made(case_dir):
    client = FakeClient(FULL_RUN, count=500)  # worst case: 500 * $4/M + 4000 * $20/M = $0.082
    record = asyncio.run(run_agent(case_dir("clean"), model=AnthropicModel(client=client), cost_cap=0.08))
    assert client.requests == [] and record["model_calls"] == 0
    assert record["status"] == "INCOMPLETE" and record["stop_reason"] == "cost cap reached"


def test_count_tokens_failure_falls_back_and_leaves_history_alone(case_dir):
    client = FakeClient(FULL_RUN, count_fails=True)
    record = asyncio.run(run_agent(case_dir("clean"), model=AnthropicModel(client=client)))
    assert record["status"] == "COMPLETE" and len(client.requests) == 3


@pytest.mark.parametrize("stop_reason", ["refusal", "max_tokens"])
def test_refusal_or_truncation_ends_the_run_incomplete(case_dir, stop_reason):
    client = FakeClient([tool_turn(SUMMARY_TOOL), text_turn("partial", stop_reason)])
    record = asyncio.run(run_agent(case_dir("clean"), model=AnthropicModel(client=client)))
    assert record["status"] == "INCOMPLETE" and record["narrative"] is None
    assert {item["tool"] for item in record["not_run"]} == set(CHECKS)


def test_unknown_model_is_rejected_without_a_price():
    with pytest.raises(ValueError):
        AnthropicModel(client=FakeClient([]), model="some-other-model")
