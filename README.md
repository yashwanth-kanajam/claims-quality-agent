# Claims Quality Agent

An MCP server with five read-only data-quality tools for synthetic claims tables, and a small agent loop that calls those tools and writes a reconciliation report. The report lists what was checked, what was flagged, whether header and line totals agree, and what was not checked.

**All data is synthetic.** Seeded fixtures generate it. There are no real members, providers, payers or claims. The results say nothing about accuracy on real data.

## Status

| Item | Status |
|---|---|
| Scripted stand-in model | Run. Results are in `results/RESULTS.md`. |
| Live model (any LLM) | Not run. No API key was available. |
| Live model adapter | Written. Tested against a mock client only. |
| Docker image | Not built. The Dockerfile was never built or run. |
| Costs | Simulated. Nothing was billed. |

## Results

All figures come from `results/RESULTS.md`.

| Measure | Result |
|---|---|
| Tool output against the existing detector | 88 runs, 0 mismatches |
| Scripted agent | 15 of 15 cases passed |
| No-LLM baseline | 15 of 15 cases passed |
| Guardrail cases with misbehaving scripted models | 4 of 4 behaved as expected |

**The scripted agent did not beat the baseline.** The baseline is a script that calls all five tools in a fixed order. It passed the same 15 cases and made no model calls.

The two differ in three ways:

- The agent made 63 tool calls across the 15 cases. The baseline made 76. The agent stops after one call when the data is refused. The baseline calls all five tools and is refused five times.
- The agent's simulated model cost was $0.2071. The baseline's was zero.
- With a cost cap of $0.05, the agent stops early and reports INCOMPLETE, as designed. The baseline has no model cost, so it finishes.

What this means: the input contract is fixed at five tables, so a fixed script does the same job without a model. These results give no evidence that an LLM adds value here. A live model might matter for the narrative, or for inputs with a looser shape. Neither was tested.

Three limits on these results:

- The parity check runs in process. It does not go through the MCP transport. The 15 agent and baseline cases do.
- The scripted model is a fixed policy, not an LLM. It cannot be misled by text.
- The planted-instruction case shows one thing only. Planted text does not reach the model, because the model receives counts and schema names and never record values. It does not show that a live model would ignore such text.

The four guardrail cases use scripted models that misbehave on purpose:

| Model behaviour | What happened |
|---|---|
| Skips the date check | Report marked INCOMPLETE. The date check is listed as not run. |
| Writes a figure no tool returned | Narrative rejected. The figure is not in the report. |
| Asks for a tool that would change data | Call rejected before it reached the server. |
| Repeats the same call without stopping | Stopped at 12 tool calls. Report marked INCOMPLETE. |

## Where the model is used

Detection is deterministic SQL from a sibling project, `healthcare-claims-quality`. That project is installed from a wheel in `vendor/` (version 0.3.0, built from commit `fcb3116` of the public repository https://github.com/yashwanth-kanajam/healthcare-claims-quality, SHA-256 `27188e59510a3ba0990e7559908b17fce21d5fb18a5183bde286664376a57075`). No SQL or validation logic is rewritten here. `checks.py` splits the detector's output by tool and decides when to refuse.

The model does two things. It picks and orders the checks, and it writes a short narrative. Code copies every figure in the report from tool output. A narrative that contains a number no tool returned is rejected.

## MCP tools

All five tools are read-only and take no arguments. The server reads the dataset directory once, at start, from `CLAIMS_DATA_DIR`. A caller cannot point it anywhere else.

| Tool | Returns |
|---|---|
| `summarize_data_quality` | Tables and columns present or missing, row counts, whether the checks can run, flag counts per check |
| `detect_duplicates` | Exact duplicate records (every business field repeated) |
| `check_broken_keys` | Rows whose member, provider or claim header does not exist |
| `check_date_sequences` | Dates out of order under the synthetic contract |
| `reconcile_header_to_line` | Money-contract flags, plus paid totals at header grain, at line grain, and after a naive join |

## Guardrails

| Guardrail | Rule |
|---|---|
| Cost cap | $0.50 per run. Before each model call, the worst-case cost of that call must fit in what is left. If not, the call is not made. |
| Tool calls | 12 per run. Retries count. |
| Retries | 2 per call. |
| Refusal | Missing tables or columns, or values that cannot be loaded, are refused. Refusals are not retried. |
| Source files | Hashed with SHA-256 before and after each run. A changed hash fails the run. |
| Unknown tools | Rejected before they reach the server. |
| Any limit reached | The report is marked INCOMPLETE and lists what was not checked. |

## Run it

Needs Python 3.10 or newer. Tested on macOS arm64 with Python 3.11 only.

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install vendor/healthcare_claims_quality-0.3.0-py3-none-any.whl
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python -m pytest -q
.venv/bin/python -m claims_agent.evaluate --out results
```

The suite has 26 tests and takes about 45 seconds. All 26 passed on 2026-11-13. Sixteen of them start a real MCP server over stdio. Nine test the live adapter against a mock client.

The evaluation takes about five minutes. It writes `results/evaluation.json`, `results/RESULTS.md`, and one report per case and runner under `results/reports/`.

To start the server alone:

```sh
CLAIMS_DATA_DIR=/path/to/csvs .venv/bin/python -m claims_agent.server
```

The directory must hold five CSV files: `members.csv`, `providers.csv`, `enrollment.csv`, `claim_headers.csv` and `claim_lines.csv`.

## Running the live evaluation later

This has not been run. The steps below are untested against the real API.

`src/claims_agent/live.py` holds `AnthropicModel`, an adapter for the Claude API with the same interface as the scripted model. The loop, guardrails and report are unchanged. The mock tests check the request shape, the tool-result round trip, the cost accounting, the cost cap, and what happens on a refusal or a truncated reply.

```sh
.venv/bin/python -m pip install -e '.[live]'
export ANTHROPIC_API_KEY=...
.venv/bin/python -m claims_agent.evaluate --live claude-opus-5-5 --out results-live
```

- **Cost.** Each run is capped at $0.50, so 15 agent cases cost at most $7.50. The scripted runs suggest much less, but that estimate is not a measurement.
- **Models.** Prices are on file for `claude-opus-5-5`, `claude-sonnet-5-5` and `claude-haiku-5-5`. Any other model is refused until a price is added to `PRICES` in `live.py`.
- **Output.** Write to a new directory, as above, so the scripted results are not overwritten.
- **Scope.** Only the 15 agent cases use the live model. The baseline and the four guardrail cases do not.
- **Requests.** Each request asks the API to retry on a fallback model if the first one declines. If a reply is refused or cut off, the run ends and the report lists the checks that did not run.
- **First thing to check.** Read one request and one reply by hand before trusting the totals. The adapter has never met the real API.

## Docker

The `Dockerfile` was written but not built or run. Docker was not available. Treat it as untested.

```sh
docker build -t claims-quality-agent .
docker run --rm -i -v "$PWD/data:/data:ro" claims-quality-agent
```

## Layout

| Path | Contents |
|---|---|
| `src/claims_agent/checks.py` | Shape check, refusal rules, and the split of detector output by tool |
| `src/claims_agent/server.py` | MCP server over stdio with the five tools |
| `src/claims_agent/toolclient.py` | MCP client with the tool-call limit, retries and unknown-tool rejection |
| `src/claims_agent/agent.py` | Agent loop, scripted model, cost accounting, no-LLM baseline |
| `src/claims_agent/live.py` | Claude API adapter (mock-tested, not run) |
| `src/claims_agent/report.py` | Renders the report from tool output |
| `src/claims_agent/seeds.py` | Builds the synthetic datasets for the evaluation cases |
| `src/claims_agent/evaluate.py` | Parity check, agent and baseline cases, guardrail cases |
| `src/claims_agent/format_results.py` | Writes `results/RESULTS.md` |
| `tests/` | 26 tests; no API key needed |
| `results/` | Evaluation output |
| `vendor/` | The pinned `healthcare-claims-quality` wheel |
| `SPEC.md` | The specification, with the changes made at approval |

## Limits

- Synthetic data only.
- Four defect categories: exact duplicates, broken foreign keys, invalid date order, and header-to-line money reconciliation.
- All five tables are required. A missing table or column is refused. There are no partial runs.
- No live model was run.
- Simulated cost counts tokens as characters divided by 4, at list price.
- Any tool exception is treated as transient and retried.
- No real claim formats such as X12 or FHIR.
- Not production software.
- A flag is a lead for investigation. It is not a confirmed error, fraud, or recoverable money.
