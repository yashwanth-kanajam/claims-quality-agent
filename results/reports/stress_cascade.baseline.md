# Claims reconciliation report

**Synthetic data only.** No real members, providers, payers or claims. Flags are leads for investigation, not confirmed errors, fraud or recoverable money.

**Status: COMPLETE** (runner: baseline)

## Checks

| Check | State | Check-level flags | Records flagged |
|---|---|---:|---:|
| detect_duplicates | ran | 6 | 6 |
| check_broken_keys | ran | 3 | 3 |
| check_date_sequences | ran | 3 | 3 |
| reconcile_header_to_line | ran | 8 | 5 |

One source defect can raise flags in more than one check (a duplicated line also breaks its header total). Counts are not deduplicated across checks and no cause is inferred.

## Header-to-line reconciliation (integer cents)

| Total | Cents |
|---|---:|
| Paid, summed at header grain | 1688190 |
| Paid, summed at line grain | 1624090 |
| Header minus line | 64100 |
| Paid after a naive header-to-line join (overstated, shown as a warning) | 3962223 |

## Tables

| Table | Present | Rows |
|---|---|---:|
| claim_headers | yes | 104 |
| claim_lines | yes | 197 |
| enrollment | yes | 24 |
| members | yes | 24 |
| providers | yes | 6 |

## Flagged records: detect_duplicates

| Table | Physical record ID | Check |
|---|---|---|
| claim_headers | H047 | all_business_fields_identical |
| claim_headers | H047_COPY | all_business_fields_identical |
| claim_headers | H051 | all_business_fields_identical |
| claim_headers | H051_COPY | all_business_fields_identical |
| claim_headers | H059 | all_business_fields_identical |
| claim_headers | H059_COPY | all_business_fields_identical |

## Flagged records: check_broken_keys

| Table | Physical record ID | Check |
|---|---|---|
| claim_headers | H014 | header_provider_exists |
| claim_headers | H027 | header_provider_exists |
| claim_headers | H031 | header_provider_exists |

## Flagged records: check_date_sequences

| Table | Physical record ID | Check |
|---|---|---|
| claim_headers | H070 | header_dates_ordered |
| claim_headers | H075 | header_dates_ordered |
| claim_headers | H081 | header_dates_ordered |

## Flagged records: reconcile_header_to_line

| Table | Physical record ID | Check |
|---|---|---|
| claim_headers | H000 | header_line_totals |
| claim_headers | H018 | header_amount_contract |
| claim_headers | H018 | header_line_totals |
| claim_headers | H032 | header_amount_contract |
| claim_headers | H032 | header_line_totals |
| claim_headers | H078 | header_amount_contract |
| claim_headers | H078 | header_line_totals |
| claim_lines | L000_1 | line_amount_contract |

## Not checked

Nothing was skipped.

## Model narrative

None.

## Run

- Tool calls (retries included): 5 of 12 allowed
- Model calls: 0
- Simulated model cost: $0.0000 of $0.50 allowed (not billed; no live model was run)
- Stop reason: finished
- Source files unchanged (SHA-256 before and after): yes
