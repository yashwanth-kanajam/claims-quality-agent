"""End-to-end tests of run_agent / run_baseline / report over a real MCP stdio server. All data is SYNTHETIC."""
import asyncio

import pytest

from claims_agent import report
from claims_agent.agent import ScriptedModel, run_agent, run_baseline

CHECK_TOOLS = ("detect_duplicates", "check_broken_keys", "check_date_sequences", "reconcile_header_to_line")


@pytest.fixture(scope="module")
def mixed(case_dir):
    return case_dir("mixed_standard")


@pytest.fixture(scope="module")
def mixed_record(mixed):
    return asyncio.run(run_agent(mixed))


def test_agent_mixed_standard_complete(mixed_record):
    r = mixed_record
    assert r["status"] == "COMPLETE"
    assert r["hashes_before"] == r["hashes_after"]
    assert r["tool_calls"] <= 12
    assert r["cost_usd"] <= 0.50
    text = report.render(r)
    assert report.figures_match(r, text)
    assert "Synthetic data only" in text


def test_agent_refuses_missing_column(case_dir):
    r = asyncio.run(run_agent(case_dir("missing_column")))
    assert r["status"] == "REFUSED"
    assert all("summary" not in res for res in r["results"].values())
    assert "paid_cents" in r["refusal"]["detail"]


def test_transient_fault_is_retried(case_dir):
    r = asyncio.run(run_agent(case_dir("clean"), faults={"check_broken_keys": 1}))
    assert r["status"] == "COMPLETE"
    outcomes = [e["outcome"] for e in r["tool_log"] if e["tool"] == "check_broken_keys"]
    assert outcomes == ["error", "ok"]


def test_persistent_fault_is_incomplete_after_three_attempts(case_dir):
    r = asyncio.run(run_agent(case_dir("clean"), faults={"check_date_sequences": 99}))
    assert r["status"] == "INCOMPLETE"
    assert "check_date_sequences" in [n["tool"] for n in r["not_run"]]
    assert len([e for e in r["tool_log"] if e["tool"] == "check_date_sequences"]) == 3


def test_cost_cap_stops_run(case_dir):
    r = asyncio.run(run_agent(case_dir("clean"), cost_cap=0.05))
    assert r["status"] == "INCOMPLETE"
    assert r["stop_reason"] == "cost cap reached"
    assert r["cost_usd"] <= 0.05


def test_tool_call_limit_stops_run(case_dir):
    r = asyncio.run(run_agent(case_dir("clean"), max_tool_calls=3))
    assert r["status"] == "INCOMPLETE"
    assert r["tool_calls"] == 3


def test_fabricated_figure_rejected(case_dir):
    r = asyncio.run(run_agent(case_dir("clean"), model=ScriptedModel(fabricate=True)))
    assert r["narrative"] is None
    assert r["narrative_rejected"]
    assert "9999 dollars" not in report.render(r)


def test_baseline_matches_agent_flags(mixed, mixed_record):
    b = asyncio.run(run_baseline(mixed))
    assert b["status"] == "COMPLETE"
    assert b["model_calls"] == 0
    for tool in CHECK_TOOLS:
        assert b["results"][tool]["flags"] == mixed_record["results"][tool]["flags"]
