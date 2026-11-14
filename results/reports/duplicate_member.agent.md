# Claims reconciliation report

**Synthetic data only.** No real members, providers, payers or claims. Flags are leads for investigation, not confirmed errors, fraud or recoverable money.

**Status: COMPLETE** (runner: agent)

## Checks

| Check | State | Check-level flags | Records flagged |
|---|---|---:|---:|
| detect_duplicates | ran | 2 | 2 |
| check_broken_keys | ran | 0 | 0 |
| check_date_sequences | ran | 0 | 0 |
| reconcile_header_to_line | ran | 0 | 0 |

One source defect can raise flags in more than one check (a duplicated line also breaks its header total). Counts are not deduplicated across checks and no cause is inferred.

## Header-to-line reconciliation (integer cents)

| Total | Cents |
|---|---:|
| Paid, summed at header grain | 1590527 |
| Paid, summed at line grain | 1590527 |
| Header minus line | 0 |
| Paid after a naive header-to-line join (overstated, shown as a warning) | 3701102 |

## Tables

| Table | Present | Rows |
|---|---|---:|
| claim_headers | yes | 101 |
| claim_lines | yes | 197 |
| enrollment | yes | 24 |
| members | yes | 25 |
| providers | yes | 6 |

## Flagged records: detect_duplicates

| Table | Physical record ID | Check |
|---|---|---|
| members | M009 | all_business_fields_identical |
| members | M009_REPEAT | all_business_fields_identical |

## Not checked

Nothing was skipped.

## Model narrative

Checks run: detect_duplicates: 2 flags on 2 records; check_broken_keys: 0 flags on 0 records; check_date_sequences: 0 flags on 0 records; reconcile_header_to_line: 0 flags on 0 records. Flags are leads for investigation, not confirmed errors.

## Run

- Tool calls (retries included): 5 of 12 allowed
- Model calls: 6
- Simulated model cost: $0.0176 of $0.50 allowed (not billed; no live model was run)
- Stop reason: finished
- Source files unchanged (SHA-256 before and after): yes
