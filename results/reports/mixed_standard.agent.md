# Claims reconciliation report

**Synthetic data only.** No real members, providers, payers or claims. Flags are leads for investigation, not confirmed errors, fraud or recoverable money.

**Status: COMPLETE** (runner: agent)

## Checks

| Check | State | Check-level flags | Records flagged |
|---|---|---:|---:|
| detect_duplicates | ran | 4 | 4 |
| check_broken_keys | ran | 2 | 2 |
| check_date_sequences | ran | 2 | 2 |
| reconcile_header_to_line | ran | 4 | 2 |

One source defect can raise flags in more than one check (a duplicated line also breaks its header total). Counts are not deduplicated across checks and no cause is inferred.

## Header-to-line reconciliation (integer cents)

| Total | Cents |
|---|---:|
| Paid, summed at header grain | 1545467 |
| Paid, summed at line grain | 1498190 |
| Header minus line | 47277 |
| Paid after a naive header-to-line join (overstated, shown as a warning) | 3563164 |

## Tables

| Table | Present | Rows |
|---|---|---:|
| claim_headers | yes | 103 |
| claim_lines | yes | 197 |
| enrollment | yes | 24 |
| members | yes | 24 |
| providers | yes | 6 |

## Flagged records: detect_duplicates

| Table | Physical record ID | Check |
|---|---|---|
| claim_headers | H030 | all_business_fields_identical |
| claim_headers | H030_COPY | all_business_fields_identical |
| claim_headers | H095 | all_business_fields_identical |
| claim_headers | H095_COPY | all_business_fields_identical |

## Flagged records: check_broken_keys

| Table | Physical record ID | Check |
|---|---|---|
| claim_headers | H039 | header_provider_exists |
| claim_headers | H084 | header_provider_exists |

## Flagged records: check_date_sequences

| Table | Physical record ID | Check |
|---|---|---|
| claim_headers | H032 | header_dates_ordered |
| claim_headers | H048 | header_dates_ordered |

## Flagged records: reconcile_header_to_line

| Table | Physical record ID | Check |
|---|---|---|
| claim_headers | H065 | header_amount_contract |
| claim_headers | H065 | header_line_totals |
| claim_headers | H077 | header_amount_contract |
| claim_headers | H077 | header_line_totals |

## Not checked

Nothing was skipped.

## Model narrative

Checks run: detect_duplicates: 4 flags on 4 records; check_broken_keys: 2 flags on 2 records; check_date_sequences: 2 flags on 2 records; reconcile_header_to_line: 4 flags on 2 records. Flags are leads for investigation, not confirmed errors.

## Run

- Tool calls (retries included): 5 of 12 allowed
- Model calls: 6
- Simulated model cost: $0.0179 of $0.50 allowed (not billed; no live model was run)
- Stop reason: finished
- Source files unchanged (SHA-256 before and after): yes
