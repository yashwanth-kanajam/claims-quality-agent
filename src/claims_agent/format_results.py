"""Render evaluation JSON as a Markdown results report (standard library only)."""
import json
import sys


def _cell(value):
    text = "" if value is None else str(value)
    return text.replace("|", "\\|").replace("\r", " ").replace("\n", " ")


def _yes(flag):
    return "yes" if flag else "NO"


def _table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |",
             "|" + "|".join("---" for _ in headers) + "|"]
    for row in rows:
        lines.append("| " + " | ".join(_cell(c) for c in row) + " |")
    return lines


def _get(entry, key):
    return "-" if entry is None else entry.get(key, "-")


def render(results: dict) -> str:
    model = results.get("model") or {}
    parity = results.get("parity") or {}
    cases = results.get("cases") or []
    guardrails = results.get("guardrail_cases") or []
    totals = results.get("totals") or {}

    out = ["# Evaluation results", "",
           "**Synthetic data only.** Scripted stand-in model; live-model runs: not run."]
    if model.get("price_basis"):
        out += ["", str(model["price_basis"])]

    out += ["", "## Tool parity", "",
            f"{parity.get('runs', 0)} seed-and-scenario runs "
            f"({parity.get('original_runs', 0)} original, {parity.get('expanded_runs', 0)} expanded) "
            f"compared with the existing detector: {parity.get('mismatches', 0)} mismatches.", ""]

    out += ["## Agent versus no-LLM baseline", ""]
    rows = []
    for runner in ("agent", "baseline"):
        t = totals.get(runner) or {}
        rows.append([runner, f"{t.get('passed', 0)}/{t.get('cases', 0)}",
                     t.get("tool_calls", 0), t.get("model_calls", 0),
                     f"{float(t.get('simulated_cost_usd', 0)):.4f}"])
    out += _table(["Runner", "Cases passed", "Tool calls", "Model calls",
                   "Simulated model cost (USD)"], rows)
    agent_passed = (totals.get("agent") or {}).get("passed", 0)
    base_passed = (totals.get("baseline") or {}).get("passed", 0)
    if agent_passed > base_passed:
        out += ["", "The scripted agent passed more cases than the baseline."]
    elif agent_passed == base_passed:
        out += ["", "The scripted agent and the baseline passed the same number of cases; "
                    "the agent did not beat the baseline."]
    else:
        out += ["", "The baseline passed more cases than the scripted agent."]

    # Group entries per case name, preserving first-seen order.
    order, grouped = [], {}
    for entry in cases:
        name = entry.get("case", "")
        if name not in grouped:
            order.append(name)
            grouped[name] = {}
        grouped[name][entry.get("runner", "")] = entry

    out += ["", "## Case results", ""]
    case_rows = []
    for name in order:
        a, b = grouped[name].get("agent"), grouped[name].get("baseline")
        case_rows.append([
            name, _get(a, "expected_status"), _get(a, "status"),
            _yes(a.get("passed")) if a else "-",
            _get(b, "expected_status"), _get(b, "status"),
            _yes(b.get("passed")) if b else "-",
            _get(a, "tool_calls"), _get(b, "tool_calls"),
        ])
    out += _table(["Case", "Expected (agent)", "Agent status", "Agent pass",
                   "Expected (baseline)", "Baseline status", "Baseline pass",
                   "Agent tool calls", "Baseline tool calls"], case_rows)
    out.append("")
    for entry in cases:
        if not entry.get("passed"):
            failed = [k for k, v in (entry.get("checks") or {}).items() if not v]
            out.append(f"- `{entry.get('case', '')}` ({entry.get('runner', '')}): "
                       f"failed checks: {', '.join(failed) if failed else '(none listed)'}")
    out.append("")

    out += ["## Guardrail cases (misbehaving scripted models)", ""]
    if guardrails:
        g_rows = [[g.get("case", ""), g.get("expected", ""), g.get("observed", ""),
                   _yes(g.get("passed"))] for g in guardrails]
        out += _table(["Case", "Expected", "Observed", "Pass"], g_rows)
    else:
        out.append("None recorded.")
    return "\n".join(out) + "\n"


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: python -m claims_agent.format_results INPUT.json OUTPUT.md")
    with open(sys.argv[1], encoding="utf-8") as fh:
        data = json.load(fh)
    with open(sys.argv[2], "w", encoding="utf-8") as fh:
        fh.write(render(data))


if __name__ == "__main__":
    main()
