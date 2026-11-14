# Claims reconciliation report

**Synthetic data only.** No real members, providers, payers or claims. Flags are leads for investigation, not confirmed errors, fraud or recoverable money.

**Status: INCOMPLETE** (runner: baseline)

This report is incomplete. Checks listed under "Not checked" produced no result, so the data is NOT shown to be free of those defects.

## Checks

| Check | State | Check-level flags | Records flagged |
|---|---|---:|---:|
| detect_duplicates | ran | 4 | 4 |
| check_broken_keys | ran | 2 | 2 |
| check_date_sequences | NOT RUN | - | - |
| reconcile_header_to_line | NOT RUN | - | - |

One source defect can raise flags in more than one check (a duplicated line also breaks its header total). Counts are not deduplicated across checks and no cause is inferred.

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

## Not checked

- check_date_sequences: tool-call limit reached
- reconcile_header_to_line: tool-call limit reached

## Model narrative

None.

## Run

- Tool calls (retries included): 3 of 3 allowed
- Model calls: 0
- Simulated model cost: $0.0000 of $0.50 allowed (not billed; no live model was run)
- Stop reason: tool-call limit reached
- Source files unchanged (SHA-256 before and after): yes
