# Claims reconciliation report

**Synthetic data only.** No real members, providers, payers or claims. Flags are leads for investigation, not confirmed errors, fraud or recoverable money.

**Status: REFUSED** (runner: agent)

## Refused

The checks were not run because the data does not meet the required contract.

- Required tables or columns are missing: providers (table)

## Checks

| Check | State | Check-level flags | Records flagged |
|---|---|---:|---:|
| detect_duplicates | NOT RUN | - | - |
| check_broken_keys | NOT RUN | - | - |
| check_date_sequences | NOT RUN | - | - |
| reconcile_header_to_line | NOT RUN | - | - |

One source defect can raise flags in more than one check (a duplicated line also breaks its header total). Counts are not deduplicated across checks and no cause is inferred.

## Tables

| Table | Present | Rows |
|---|---|---:|
| claim_headers | yes | 101 |
| claim_lines | yes | 197 |
| enrollment | yes | 24 |
| members | yes | 24 |
| providers | NO | - |

## Not checked

- detect_duplicates: not requested
- check_broken_keys: not requested
- check_date_sequences: not requested
- reconcile_header_to_line: not requested

## Model narrative

I cannot run the checks on this data. Required tables or columns are missing: providers (table)

## Run

- Tool calls (retries included): 1 of 12 allowed
- Model calls: 2
- Simulated model cost: $0.0040 of $0.50 allowed (not billed; no live model was run)
- Stop reason: finished
- Source files unchanged (SHA-256 before and after): yes
