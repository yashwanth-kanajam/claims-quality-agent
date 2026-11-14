"""In-process tests of claims_agent.checks, server tool list and seeds. All data is SYNTHETIC."""
import asyncio
import json

import pytest
from claims_quality.detect import detect_directory

from claims_agent import checks, seeds, server

CHECK_TOOLS = tuple(checks.CHECKS)


def key(flag):
    return (flag["category"], flag["table"], flag["record_id"], flag["check_name"])


def test_clean_case_has_no_flags_and_is_runnable(case_dir):
    d = case_dir("clean")
    for tool in CHECK_TOOLS:
        assert checks.run_tool(d, tool)["flags"] == []
    summary = checks.run_tool(d, checks.SUMMARY_TOOL)
    assert summary["runnable"] is True
    assert summary["checks_available"] == list(CHECK_TOOLS)


def test_mixed_standard_union_equals_detector_and_categories_disjoint(case_dir):
    d = case_dir("mixed_standard")
    union = []
    for tool, category in checks.CHECKS.items():
        flags = checks.run_tool(d, tool)["flags"]
        assert {f["category"] for f in flags} <= {category}
        union += [key(f) for f in flags]
    expected = [key(f) for f in detect_directory(d)]
    assert expected
    assert sorted(union) == sorted(expected)


@pytest.mark.parametrize("case,code,needle", [
    ("missing_column", "missing_columns", "claim_headers.paid_cents"),
    ("missing_table", "missing_columns", "providers (table)"),
    ("empty_value", "invalid_data", None),
])
def test_refusals(case_dir, case, code, needle):
    d = case_dir(case)
    for tool in CHECK_TOOLS:
        result = checks.run_tool(d, tool)
        assert result["refused"] is True
        assert result["code"] == code
        if needle:
            assert needle in result["detail"]


def test_reconcile_totals_on_clean_data(case_dir):
    totals = checks.run_tool(case_dir("clean"), "reconcile_header_to_line")["summary"]["totals"]
    assert totals["header_paid_cents"] == totals["line_paid_cents"]
    assert totals["header_minus_line_cents"] == 0
    assert totals["naive_join_paid_cents"] > totals["header_paid_cents"]


def test_model_view_hides_flags_and_planted_text(case_dir):
    d = case_dir("planted_instruction")
    full = {t: checks.run_tool(d, t) for t in CHECK_TOOLS}
    for tool, result in full.items():
        view = checks.model_view(result)
        assert "flags" not in view
        assert seeds.PLANTED_TEXT not in json.dumps(view)
    assert seeds.PLANTED_TEXT in json.dumps(full["detect_duplicates"]["flags"])


def test_source_hashes_unchanged_by_all_tools(case_dir):
    d = case_dir("mixed_standard")
    before = checks.source_hashes(d)
    for tool in checks.TOOL_NAMES:
        checks.run_tool(d, tool)
    assert checks.source_hashes(d) == before


def test_server_exposes_exactly_the_five_tools_and_no_manifest_written(case_dir):
    names = {t.name for t in asyncio.run(server.mcp.list_tools())}
    assert names == set(checks.TOOL_NAMES) and len(names) == 5
    files = sorted(p.name for p in case_dir("mixed_standard").iterdir())
    assert files == sorted(t + ".csv" for t in checks.SCHEMA)
