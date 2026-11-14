"""Reconciliation report rendered by code from tool output. Synthetic data only.

Every figure below is copied from a tool result. The model's narrative is
included only if `finalize` found no figure in it that a tool did not return.
"""
from .checks import CHECKS, SUMMARY_TOOL

MAX_LISTED = 50


def cell(value):
    return str(value).replace("\\", "\\\\").replace("|", "\\|").replace("\n", " ").replace("\r", " ").replace("`", "'")


def check_row(tool, result):
    if result and "summary" in result:
        return f"| {tool} | ran | {result['summary']['flag_count']} | {result['summary']['flagged_records']} |"
    state = "NOT RUN" if result is None else "REFUSED" if result.get("refused") else "FAILED"
    return f"| {tool} | {state} | - | - |"


def render(record):
    results = record["results"]
    lines = ["# Claims reconciliation report", "",
             "**Synthetic data only.** No real members, providers, payers or claims. Flags are leads for investigation, not confirmed errors, fraud or recoverable money.",
             "", f"**Status: {record['status']}** (runner: {record['runner']})", ""]
    if record["refusal"]:
        lines += ["## Refused", "", "The checks were not run because the data does not meet the required contract.", "", "- " + cell(record["refusal"]["detail"]), ""]
    if record["status"] == "INCOMPLETE":
        lines += ["This report is incomplete. Checks listed under \"Not checked\" produced no result, so the data is NOT shown to be free of those defects.", ""]
    lines += ["## Checks", "", "| Check | State | Check-level flags | Records flagged |", "|---|---|---:|---:|"]
    lines += [check_row(tool, results.get(tool)) for tool in CHECKS]
    lines += ["", "One source defect can raise flags in more than one check (a duplicated line also breaks its header total). Counts are not deduplicated across checks and no cause is inferred."]
    totals = (results.get("reconcile_header_to_line") or {}).get("summary", {}).get("totals")
    if totals:
        lines += ["", "## Header-to-line reconciliation (integer cents)", "", "| Total | Cents |", "|---|---:|",
                  f"| Paid, summed at header grain | {totals['header_paid_cents']} |",
                  f"| Paid, summed at line grain | {totals['line_paid_cents']} |",
                  f"| Header minus line | {totals['header_minus_line_cents']} |",
                  f"| Paid after a naive header-to-line join (overstated, shown as a warning) | {totals['naive_join_paid_cents']} |"]
    summary = results.get(SUMMARY_TOOL)
    if summary and "tables" in summary:
        lines += ["", "## Tables", "", "| Table | Present | Rows |", "|---|---|---:|"]
        lines += [f"| {name} | {'yes' if t['present'] else 'NO'} | {t.get('rows', '-')} |" for name, t in summary["tables"].items()]
    for tool in CHECKS:
        flags = (results.get(tool) or {}).get("flags") or []
        if flags:
            lines += ["", f"## Flagged records: {tool}", "", "| Table | Physical record ID | Check |", "|---|---|---|"]
            lines += [f"| {cell(f['table'])} | {cell(f['record_id'])} | {cell(f['check_name'])} |" for f in flags[:MAX_LISTED]]
            if len(flags) > MAX_LISTED:
                lines.append(f"\n{len(flags) - MAX_LISTED} more are in the JSON run record.")
    lines += ["", "## Not checked", ""]
    lines += [f"- {item['tool']}: {item['reason']}" for item in record["not_run"]] or ["Nothing was skipped."]
    lines += ["", "## Model narrative", "", cell(record["narrative"]) if record["narrative"] else
              ("Rejected: " + record["narrative_rejected"] if record["narrative_rejected"] else "None.")]
    unchanged = record["hashes_before"] == record["hashes_after"]
    lines += ["", "## Run", "", f"- Tool calls (retries included): {record['tool_calls']} of {record['limits']['max_tool_calls']} allowed",
              f"- Model calls: {record['model_calls']}",
              f"- Simulated model cost: ${record['cost_usd']:.4f} of ${record['limits']['cost_cap_usd']:.2f} allowed (not billed; no live model was run)",
              f"- Stop reason: {record['stop_reason'] or 'finished'}",
              f"- Source files unchanged (SHA-256 before and after): {'yes' if unchanged else 'NO'}", ""]
    return "\n".join(lines)


def figures_match(record, text):
    """Every check row in the report equals what the tool returned."""
    for tool in CHECKS:
        result = record["results"].get(tool)
        if check_row(tool, result) not in text:
            return False
        if result and "summary" in result and result["summary"]["flag_count"] != len(result["flags"]):
            return False
    return True
