# Claims reconciliation report

**Synthetic data only.** No real members, providers, payers or claims. Flags are leads for investigation, not confirmed errors, fraud or recoverable money.

**Status: REFUSED** (runner: baseline)

## Refused

The checks were not run because the data does not meet the required contract.

- Required tables or columns are missing: claim_headers.paid_cents

## Checks

| Check | State | Check-level flags | Records flagged |
|---|---|---:|---:|
| detect_duplicates | REFUSED | - | - |
| check_broken_keys | REFUSED | - | - |
| check_date_sequences | REFUSED | - | - |
| reconcile_header_to_line | REFUSED | - | - |

One source defect can raise flags in more than one check (a duplicated line also breaks its header total). Counts are not deduplicated across checks and no cause is inferred.

## Tables

| Table | Present | Rows |
|---|---|---:|
| claim_headers | yes | 101 |
| claim_lines | yes | 197 |
| enrollment | yes | 24 |
| members | yes | 24 |
| providers | yes | 6 |

## Not checked

- detect_duplicates: refused
- check_broken_keys: refused
- check_date_sequences: refused
- reconcile_header_to_line: refused

## Model narrative

None.

## Run

- Tool calls (retries included): 5 of 12 allowed
- Model calls: 0
- Simulated model cost: $0.0000 of $0.50 allowed (not billed; no live model was run)
- Stop reason: finished
- Source files unchanged (SHA-256 before and after): yes
