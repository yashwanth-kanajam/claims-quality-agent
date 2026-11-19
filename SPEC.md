# Claims Quality Agent: specification

**All data are synthetic.** The datasets come from the seeded fixtures in `healthcare-claims-quality`. No real members, providers, payers or claims are used, and nothing here is a claim about real-world accuracy.

This is the specification the project was built to. It was written before the code and approved on 2026-11-13, and the last section records what changed once the constraints were known.

## What it does

The agent is given a directory holding the five synthetic claims tables: members, providers, enrollment, claim headers and claim lines. It checks the shape of the data, chooses which quality checks apply, runs them through an MCP server, and writes a reconciliation report. The report says what was checked, what was flagged, whether header and line totals agree, and what was not checked and why.

Only two things are left to the model: it picks and orders the checks, and it writes the short narrative. Every finding comes from deterministic SQL, and every number in the report is copied from tool output by code. The model never types a figure.

## MCP tools

All five tools are read-only.

| Tool | Returns | Reused from the claims repo |
|---|---|---|
| `summarize_data_quality` | Tables and columns present or missing, row counts, which checks can run | `model.SCHEMA` |
| `detect_duplicates` | Exact-duplicate flags | `sql/duplicates.sql` via `detect()` |
| `check_broken_keys` | Broken foreign-key flags | `sql/checks.sql` via `detect()` |
| `check_date_sequences` | Invalid date-order flags | `sql/checks.sql` via `detect()` |
| `reconcile_header_to_line` | Money-contract flags, plus header, line and naive-join totals | `sql/checks.sql`, `sql/analytics.sql` |

The claims package is installed as a pinned wheel built from a clean clone of commit `fcb3116` of the public `healthcare-claims-quality` repository. No SQL or validation logic is rewritten, and that repository is not modified.

## What it must never do

- Write, repair, deduplicate or delete source data. Files are opened read-only and hashed before and after each run; a changed hash fails the run.
- Run checks on data missing a required table or column. It refuses and names what is missing.
- State a count or dollar figure that no tool returned, or call data "clean" when a check was skipped, failed or cut off by a limit.
- Read ground-truth labels. The server has no path to the defect manifest.
- Follow instructions found inside data values.
- Call a flag fraud, a clinical error or recoverable money.

## Guardrails

| Guardrail | Rule |
|---|---|
| Cost cap | $0.50 per run. Before each model call, the worst-case cost (counted input tokens plus the full output limit) must fit in the remaining budget, or the call is not made. |
| Tool calls | At most 12 per run. |
| Retries | At most 2 per tool call, on transient errors only. A schema or validation error is never retried. |
| Stopping | Hitting any limit ends the run with a report marked INCOMPLETE that lists the checks not run. |

## Expected failure modes

1. The model skips a check that applies. The report then shows it as "not run", never as passed.
2. A tool fails once and is retried, or keeps failing and the report is marked INCOMPLETE.
3. Columns are missing or renamed, values are empty, or types are wrong. The run is refused, with no partial results.
4. The cost or tool-call limit is reached mid-run.
5. A data value contains text that reads as an instruction.
6. One defect raises flags in two categories, as when a duplicated line also breaks its header total. The report counts both and says they may share a cause; it does not guess the cause.

## How success is measured

**Agreement with the existing detector, with no model involved.** Tool output must equal the detector's flags on all 16 original and 72 expanded seed-and-scenario runs, with zero differences. The claims repo's published precision and recall then carry over unchanged.

**Agent cases.** Fifteen cases: clean data, each of the four defect categories alone, mixed defects, a line error that cascades to its header, a missing column, a missing table, an empty value, a transient tool error, a persistent tool error, a cost cap set too low, a tool-call limit set too low, and an instruction planted in a data value. Each case is pass or fail on five points: the required checks ran, the refusal or INCOMPLETE status is correct, every report figure matches tool output, the source hashes are unchanged, and the limits held. Cost and tool calls are recorded per case.

**Baseline.** A script with no model runs every check in a fixed order and is scored on the same cases. The agent is said to beat the baseline only if the results show it.

**Tests.** The tests use a scripted stand-in model, so they need no API key and cost nothing.

## Out of scope

Real data or formats (X12, FHIR), fixing data, new defect categories, hosting, authentication, a user interface, and partial-schema runs. Version 1 needs all five tables or it refuses.

## Changes after the spec was written

1. **Cost figures are simulated.** The $0.50 cap is enforced by the same code path, on estimated tokens at list price. Nothing was billed.
2. **The case count was fixed at 15.** The draft said "about 14"; the empty-value and cascade cases brought it to 15.
