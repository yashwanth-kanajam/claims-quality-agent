"""Read-only checks over the five synthetic claims tables. Synthetic data only.

No SQL or validation logic lives here: detection is `claims_quality.detect`
(duplicates.sql, checks.sql, analytics.sql) and loading is
`claims_quality.model.read_dataset`. This module only splits the detector's
output per tool and decides when to refuse.
"""
import csv
import hashlib
from collections import Counter
from pathlib import Path

import duckdb
from claims_quality.detect import detect, query
from claims_quality.model import SCHEMA, read_dataset

SUMMARY_TOOL = "summarize_data_quality"
CHECKS = {
    "detect_duplicates": "exact_duplicate",
    "check_broken_keys": "broken_foreign_key",
    "check_date_sequences": "invalid_date_sequence",
    "reconcile_header_to_line": "financial_reconciliation",
}
TOOL_NAMES = (SUMMARY_TOOL,) + tuple(CHECKS)


class Refusal(Exception):
    """The data does not meet the contract the checks need. Never retried."""

    def __init__(self, code, detail):
        super().__init__(detail)
        self.code, self.detail = code, detail

    def as_result(self, tool):
        return {"tool": tool, "refused": True, "code": self.code, "detail": self.detail}


def source_hashes(data_dir):
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(Path(data_dir).glob("*.csv"))}


def profile(data_dir):
    """Header-only shape check. Reports schema names and counts, never data values."""
    tables, missing = {}, []
    for table, fields in SCHEMA.items():
        path = Path(data_dir) / (table + ".csv")
        if not path.is_file():
            tables[table] = {"present": False}
            missing.append(table + " (table)")
            continue
        with path.open(newline="") as handle:
            reader = csv.reader(handle)
            columns = next(reader, [])
            rows = sum(1 for _ in reader)
        absent = [name for name in fields if name not in columns]
        tables[table] = {"present": True, "rows": rows, "missing_columns": absent,
                         "unexpected_column_count": len([c for c in columns if c not in fields])}
        missing += [f"{table}.{name}" for name in absent]
        if not absent and tables[table]["unexpected_column_count"]:
            missing.append(f"{table} (unexpected columns)")
    return {"tables": tables, "missing": missing}


def load(data_dir):
    shape = profile(data_dir)
    if shape["missing"]:
        raise Refusal("missing_columns", "Required tables or columns are missing: " + ", ".join(shape["missing"]))
    try:
        return read_dataset(data_dir)
    except ValueError as error:  # message names table/column/line only
        raise Refusal("invalid_data", str(error)) from error


def _flags(data):
    try:
        return detect(data)
    except duckdb.Error as error:  # engine messages can echo data values: do not forward them
        raise Refusal("invalid_data", "A value could not be loaded under the declared column types or record_id is repeated.") from error


def summarize(data_dir):
    shape = profile(data_dir)
    result = {"tool": SUMMARY_TOOL, "tables": shape["tables"], "runnable": False, "checks_available": []}
    try:
        flags = _flags(load(data_dir))
    except Refusal as refusal:
        result["refusal"] = {"code": refusal.code, "detail": refusal.detail}
        return result
    counts = Counter(flag["category"] for flag in flags)
    result.update(runnable=True, checks_available=list(CHECKS), check_level_flags=len(flags),
                  flags_by_check={tool: counts[category] for tool, category in CHECKS.items()})
    return result


def run_check(data_dir, tool):
    category = CHECKS[tool]
    data = load(data_dir)
    flags = [flag for flag in _flags(data) if flag["category"] == category]
    summary = {"check": tool, "category": category, "flag_count": len(flags),
               "flagged_records": len({(f["table"], f["record_id"]) for f in flags}),
               "by_table": dict(Counter(f["table"] for f in flags)),
               "by_check_name": dict(Counter(f["check_name"] for f in flags))}
    if tool == "reconcile_header_to_line":
        totals = query(data, "analytics.sql")[0]
        header, line = totals["correct_header_paid_cents"], totals["correct_line_paid_cents"]
        summary["totals"] = {"header_paid_cents": header, "line_paid_cents": line,
                             "header_minus_line_cents": None if header is None or line is None else header - line,
                             "naive_join_paid_cents": totals["incorrect_join_paid_cents"]}
    return {"tool": tool, "summary": summary, "flags": flags}


def run_tool(data_dir, tool):
    """Single entry point used by the MCP server. Refusals are results, not errors."""
    try:
        return summarize(data_dir) if tool == SUMMARY_TOOL else run_check(data_dir, tool)
    except Refusal as refusal:
        return refusal.as_result(tool)


def model_view(result):
    """What the model is allowed to see: counts and schema names, never record-level values."""
    if "summary" in result:
        return result["summary"]
    return {key: value for key, value in result.items() if key != "flags"}
