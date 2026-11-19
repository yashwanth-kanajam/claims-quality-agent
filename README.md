# Claims Quality Agent

Claims-validation checks made available through an MCP server, then tested to see whether an agent running them beats a plain script. It didn't.

The agent passed all 15 test cases, and so did a no-model baseline that calls all five checks in a fixed order. It made fewer tool calls, 63 to 76, but only because of rules written into it: it stops after one call when the data is refused, and stops early when the cost cap is set too low. The baseline made no model calls at all. With the input fixed at five tables, a script does the same job without a model.

| Measure | Agent | Baseline |
|---|---:|---:|
| Cases passed | 15 of 15 | 15 of 15 |
| Tool calls across the 15 cases | 63 | 76 |
| Simulated model cost | $0.2071 | $0 |

All data are synthetic. No real members, providers, payers or claims are used.

## How it works

The five SQL checks come from [healthcare-claims-quality](https://github.com/yashwanth-kanajam/healthcare-claims-quality), installed from a pinned wheel in `vendor/` (version 0.3.0, built from commit `fcb3116`). None of the check logic is rewritten here. The model picks which checks to run and writes a short summary. It never touches the numbers: code copies every figure in the report from the tool results, and a summary that quotes a number no tool returned is rejected. The model never sees the claims themselves, only counts and table names. The agent was evaluated with a scripted model that follows fixed rules, behind the same interface a live model would use.

Before testing the agent, the tools' output was matched against the original checks on 88 runs (16 from the original evaluation, 72 from the expanded one), with no differences. That comparison runs in process, not over the MCP transport. The agent and baseline cases do go over it.

The 15 cases cover clean data, each defect category, mixed defects, a missing column, a missing table, an empty value, tool errors, limits set too low, and instruction text planted in data values. Each case passes only if the status is right, the flags match the detector, the report figures match tool output, the source hashes are unchanged and the limits held.

| Tool | Returns |
|---|---|
| `summarize_data_quality` | Tables and columns present or missing, row counts, whether the checks can run, flag counts per check |
| `detect_duplicates` | Exact duplicate records (every business field repeated) |
| `check_broken_keys` | Rows whose member, provider or claim header does not exist |
| `check_date_sequences` | Dates out of order under the synthetic contract |
| `reconcile_header_to_line` | Money-contract flags, plus paid totals at header grain, at line grain, and after a naive join |

All five tools are read-only and take no arguments. The server reads the dataset directory once, at start, from `CLAIMS_DATA_DIR`, so a caller cannot point it anywhere else.

| Guardrail | Rule |
|---|---|
| Model cost | $0.50 per run. Before each model call, its worst-case cost has to fit in what is left, or the call is not made. |
| Tool calls | 12 per run, with retries counted. |
| Retries | 2 per call. |
| Refusal | Missing tables or columns, or values that cannot be loaded, are refused and not retried. |
| Source files | Hashed with SHA-256 before and after each run. A changed hash fails the run. |
| Unknown tools | Rejected before they reach the server. |
| Any limit reached | The report is marked INCOMPLETE and lists what was not checked. |

Four more cases use models built to misbehave on purpose, each aimed at one guardrail. All four were caught.

| Model behavior | What happened |
|---|---|
| Skips the date check | Report marked INCOMPLETE, with the date check listed as not run |
| Writes a figure no tool returned | Summary rejected; the figure is not in the report |
| Asks for a tool that would change data | Call rejected before it reached the server |
| Repeats the same call without stopping | Stopped at 12 tool calls; report marked INCOMPLETE |

## Run it

Requires Python 3.10+. Tested on macOS arm64 with Python 3.11 only.

```sh
python3.11 -m venv .venv
.venv/bin/python -m pip install vendor/healthcare_claims_quality-0.3.0-py3-none-any.whl
.venv/bin/python -m pip install -e '.[test]'
.venv/bin/python -m pytest -q
.venv/bin/python -m claims_agent.evaluate --out results
```

The suite has 26 tests and takes about 45 seconds. Sixteen of them start a real MCP server over stdio. The evaluation takes about five minutes and writes `results/evaluation.json`, `results/RESULTS.md` and one report per case under `results/reports/`.

To start the server on its own:

```sh
CLAIMS_DATA_DIR=/path/to/csvs .venv/bin/python -m claims_agent.server
```

The directory must hold `members.csv`, `providers.csv`, `enrollment.csv`, `claim_headers.csv` and `claim_lines.csv`.

## Limitations

The planted-instruction case shows only that the planted text never reached the model. It does not show that a model would ignore such text.

Made-up numbers are caught by the number check, but a real number attached to the wrong label is not. Equal pass rates say nothing about speed, how useful the summaries are, or inputs outside these 15 cases. The cost figure counts tokens as characters divided by 4, at list price, so it is a rough guide and not a bill.

Because the data are synthetic and small, nothing here estimates accuracy, cost or speed on real claims. The checks cover four defect categories only, and real claim formats such as X12 or FHIR are not handled. All five tables are required. Missing tables or columns are refused, with no partial runs. Any tool exception is treated as transient and retried.

Each flag is a lead for investigation, not a confirmed error, fraud or recoverable money. This is not production software. The full design and its out-of-scope list are in [SPEC.md](SPEC.md).

## Reference

| Path | Contents |
|---|---|
| `src/claims_agent/checks.py` | Shape check, refusal rules, and the split of detector output by tool |
| `src/claims_agent/server.py` | MCP server over stdio with the five tools |
| `src/claims_agent/toolclient.py` | MCP client with the tool-call limit, retries and unknown-tool rejection |
| `src/claims_agent/agent.py` | Agent loop, scripted model, cost accounting, no-model baseline |
| `src/claims_agent/live.py` | Adapter for a hosted language model API, with the same interface as the scripted model; set the API key environment variable to use it |
| `src/claims_agent/report.py` | Renders the report from tool output |
| `src/claims_agent/seeds.py` | Builds the synthetic datasets for the test cases |
| `src/claims_agent/evaluate.py` | Detector comparison, agent and baseline cases, misbehaving-model cases |
| `src/claims_agent/format_results.py` | Writes `results/RESULTS.md` |
| `tests/` | 26 tests |
| `results/` | Evaluation output |
| `vendor/` | The pinned `healthcare-claims-quality` wheel |
| `Dockerfile` | Included container definition for the MCP server |
| `SPEC.md` | The specification the project was built to |
