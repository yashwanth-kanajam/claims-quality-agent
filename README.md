# Claims Quality Agent

**An agent that reports on data quality should not be trusted to produce the numbers itself.** This project puts the checks from [healthcare-claims-quality](https://github.com/yashwanth-kanajam/healthcare-claims-quality) behind an MCP server, then tests whether a model-driven agent calling those tools does any better than a fixed script.

**All data are synthetic.** No real members, providers, payers or claims are used, and the results say nothing about accuracy on real data.

## Key finding

On 15 test cases the scripted agent passed 15 and a no-LLM baseline passed 15. **The agent did not beat the baseline.** The baseline is a script that calls all five tools in a fixed order; it made no model calls and cost nothing, while the agent's simulated model cost was $0.2071.

The input contract is fixed at five tables, so a fixed script does the same job without a model. These results give no evidence that an LLM adds value here. A live model might matter for the narrative, or for inputs with a looser shape, and neither was tested.

## What was and was not run

| Item | Status |
|---|---|
| Scripted stand-in model | Run. Results are in [results/RESULTS.md](results/RESULTS.md). |
| Live model (any LLM) | Not run. No API key was available. |
| Live model adapter | Written, and tested against a mock client only. |
| Docker image | Not built. The Dockerfile was never built or run. |
| Costs | Simulated. Nothing was billed. |

The "model" in every result below is a scripted stand-in: a fixed policy that asks for the summary, then each available check, then writes a narrative. It is not an LLM.

## How the agent is constrained

Detection is the deterministic SQL from `healthcare-claims-quality`, installed from a wheel in `vendor/` (version 0.3.0, built from commit `fcb3116` of that repository, SHA-256 `27188e59510a3ba0990e7559908b17fce21d5fb18a5183bde286664376a57075`). No SQL or validation logic is rewritten here; `checks.py` only splits the detector's output by tool and decides when to refuse.

The model picks and orders the checks and writes a short narrative, and that is all it does. Every figure in the report is copied from tool output by code. The model is sent counts and schema names, never record values, and a narrative containing a number that no tool returned is rejected.

| Guardrail | Rule |
|---|---|
| Cost cap | $0.50 per run. Before each model call, the worst-case cost of that call must fit in what is left, or the call is not made. |
| Tool calls | 12 per run, with retries counted. |
| Retries | 2 per call. |
| Refusal | Missing tables or columns, or values that cannot be loaded, are refused and not retried. |
| Source files | Hashed with SHA-256 before and after each run; a changed hash fails the run. |
| Unknown tools | Rejected before they reach the server. |
| Any limit reached | The report is marked INCOMPLETE and lists what was not checked. |

## MCP tools

All five tools are read-only and take no arguments. The server reads the dataset directory once, at start, from `CLAIMS_DATA_DIR`, so a caller cannot point it anywhere else.

| Tool | Returns |
|---|---|
| `summarize_data_quality` | Tables and columns present or missing, row counts, whether the checks can run, flag counts per check |
| `detect_duplicates` | Exact duplicate records (every business field repeated) |
| `check_broken_keys` | Rows whose member, provider or claim header does not exist |
| `check_date_sequences` | Dates out of order under the synthetic contract |
| `reconcile_header_to_line` | Money-contract flags, plus paid totals at header grain, at line grain, and after a naive join |

## Validation

The tools were first compared with the existing detector on 88 runs (16 from the original evaluation, 72 from the expanded one), with 0 mismatches. That comparison runs in process and does not go through the MCP transport; the agent and baseline cases below do.

The agent and the baseline were then scored on the same 15 cases: clean data, each defect category, mixed defects, a missing column, a missing table, an empty value, tool errors, limits set too low, and instruction text planted in data values. A case passes only if the status is right, the flags match the detector, the report figures match tool output, the source hashes are unchanged and the limits held.

| Measure | Agent | Baseline |
|---|---:|---:|
| Cases passed | 15 of 15 | 15 of 15 |
| Tool calls across the 15 cases | 63 | 76 |
| Simulated model cost | $0.2071 | $0 |

The agent makes fewer tool calls because it stops after one call when the data are refused, where the baseline calls all five tools and is refused five times. With the cost cap set to $0.05 the agent stops early and reports INCOMPLETE, as designed; the baseline has no model cost, so it finishes.

Four further cases use scripted models that misbehave on purpose, and all four were handled as intended.

| Model behaviour | What happened |
|---|---|
| Skips the date check | Report marked INCOMPLETE, with the date check listed as not run |
| Writes a figure no tool returned | Narrative rejected; the figure is not in the report |
| Asks for a tool that would change data | Call rejected before it reached the server |
| Repeats the same call without stopping | Stopped at 12 tool calls; report marked INCOMPLETE |

Because the scripted model is a fixed policy, it cannot be misled by text. The planted-instruction case therefore shows only that planted text does not reach the model. It does not show that a live model would ignore such text.

Full results: [results/RESULTS.md](results/RESULTS.md), with one report per case and runner under `results/reports/`.

## Reproduce

Requires Python 3.10+. Tested on macOS arm64 with Python 3.11 only.

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install vendor/healthcare_claims_quality-0.3.0-py3-none-any.whl
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python -m pytest -q
.venv/bin/python -m claims_agent.evaluate --out results
```

The suite has 26 tests and takes about 45 seconds; all 26 passed on 2026-11-13. Sixteen of them start a real MCP server over stdio, and nine test the live adapter against a mock client. The evaluation takes about five minutes and writes `results/evaluation.json`, `results/RESULTS.md` and the per-case reports.

To start the server on its own:

```sh
CLAIMS_DATA_DIR=/path/to/csvs .venv/bin/python -m claims_agent.server
```

The directory must hold `members.csv`, `providers.csv`, `enrollment.csv`, `claim_headers.csv` and `claim_lines.csv`.

## Running the live evaluation later

None of this has been run, and the steps are untested against the real API.

`src/claims_agent/live.py` holds `AnthropicModel`, an adapter for the Claude API with the same interface as the scripted model, so the loop, guardrails and report do not change. Its mock tests cover the request shape, the tool-result round trip, cost accounting, the cost cap, and what happens when a reply is refused or cut off.

```sh
.venv/bin/python -m pip install -e '.[live]'
export ANTHROPIC_API_KEY=...
.venv/bin/python -m claims_agent.evaluate --live claude-opus-5-5 --out results-live
```

Each run is capped at $0.50, so the 15 agent cases cost at most $7.50. The scripted runs suggest much less, but that is an estimate and not a measurement. Prices are on file for `claude-opus-5-5`, `claude-sonnet-5-5` and `claude-haiku-5-5`; any other model is refused until a price is added to `PRICES` in `live.py`.

Only the 15 agent cases use the live model; the baseline and the four misbehaving-model cases do not. Each request asks the API to retry on a fallback model if the first one declines, and if a reply is refused or cut off the run ends with the unrun checks listed. Write to a new directory, as above, so the scripted results are not overwritten, and read one request and one reply by hand before trusting the totals.

## Docker

The `Dockerfile` was written but not built or run, because Docker was not available. Treat it as untested.

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
| `src/claims_agent/seeds.py` | Builds the synthetic datasets for the test cases |
| `src/claims_agent/evaluate.py` | Detector comparison, agent and baseline cases, misbehaving-model cases |
| `src/claims_agent/format_results.py` | Writes `results/RESULTS.md` |
| `tests/` | 26 tests; no API key needed |
| `results/` | Evaluation output |
| `vendor/` | The pinned `healthcare-claims-quality` wheel |
| `SPEC.md` | The specification the project was built to |

## Limitations

The data are synthetic and the fixture is small, so nothing here estimates accuracy, cost or speed on real claims. The checks cover four defect categories only: exact duplicates, broken foreign keys, invalid date order, and header-to-line money reconciliation. Real claim formats such as X12 or FHIR are not handled.

All five tables are required. A missing table or column is refused, and there are no partial runs. Any tool exception is treated as transient and retried.

No live model was run. The simulated cost counts tokens as characters divided by 4, at list price, so it is a rough guide and not a bill.

A flag is a lead for investigation, not a confirmed error, fraud or recoverable money. This is not production software.

See [SPEC.md](SPEC.md) for the full design and its out-of-scope list.
