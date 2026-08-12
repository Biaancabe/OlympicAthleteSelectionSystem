---
editor_options: 
  markdown: 
    wrap: 72
---

# Plan: ETL Pipeline (Technical Implementation)

This plan describes *how* the ETL Pipeline spec
(`specs/etl-pipeline.md`) gets implemented. It is built directly on
Martin Rumo's existing code (`notebooks/main.ipynb`,
`notebooks/mainv2.ipynb`, `streamlit/utils.py`) — reusing what works,
and optimizing specific gaps identified against the spec and
constitution.

## Approach

Martin's notebooks currently mix ETL logic (loading, cleaning,
validating data) with rule-loading and rule-application logic in one
linear notebook flow. This plan separates the ETL concern into its own
reusable module, so it can be called independently of which sport/rule
file is being evaluated — ETL runs once per data export, not once per
sport.

## Source

The primary source is the daily CSV export from Swiss Olympic's Podium
platform (Gracenote-sourced), semicolon-separated (see
`specs/etl-pipeline.md`, "Inputs"). This is confirmed and working — no
database access is required. Martin's existing CSV loader is reused
directly for this path.

The ETL logic after loading is source-independent: once data has been
loaded (from the Podium export, a manual CSV, or the manual entry
form), all sources converge into the same cleaning, validation, and
output structure.

## Module Layout

```         
src/
  etl/
    __init__.py
    load.py          # reading raw sources (podium CSV, manual CSV, manual form)
    clean.py         # cleaning/normalization functions
    validate.py       # schema validation + validation report
    pipeline.py       # orchestrates load -> clean -> validate -> output
tests/
  etl/
    test_clean.py
    test_validate.py
```

## Functions: Reused As-Is From Martin

These work correctly and are adopted without changes:

| Function | Source | What it does |
|----|----|----|
| `load_data(data_path)` | `main.ipynb` | Reads CSV, converts pandas NaN to Python `None` |
| `load_json_schema(schema_path)` | `main.ipynb` | Loads a JSON Schema file |
| `clean_data(data, schema)` — column selection | `mainv2.ipynb` | Selects only columns defined in `dataschema.json`, drops the rest |
| Team-member row filtering (`Team Members != "Yes"`) | `mainv2.ipynb` | Removes duplicate per-member rows for team results, keeps the team-level row |
| `clean_dob(value)` | `mainv2.ipynb` | Normalizes `DoB` to string or `None` |
| `clean_olympic(value)` | `mainv2.ipynb` | Normalizes `Is Olympic Discipline` to string or `None` |
| Date parsing to ISO (`pd.to_datetime(...).dt.strftime('%Y-%m-%d')`) | `mainv2.ipynb` | Standardizes the `Date` column |

## Functions: Optimized From Martin's Version

| Issue found | Martin's current behavior | Change | Why (spec/constitution link) |
|----|----|----|----|
| **`DNQ` missing** | `convert_rank()` maps `DNS`→996, `DNF`→997, `DSQ`→998, everything else (incl. missing) →999. `DNQ` is not handled and falls into the generic 999 bucket, indistinguishable from a true missing value. | Add explicit `DNQ` → its own code (e.g. 995). | Constitution Principle 4: DNF/DNQ/DNS/DSQ are meaningful, distinct states — DNQ was silently conflated with "missing." |
| **Original status overwritten** | `convert_rank()` replaces the `Rank` column in place with the numeric surrogate; the original string (`"DNF"`, etc.) is lost. | Keep the original rank value in a new `Rank_Status` column, and store the numeric surrogate separately as `Rank_num`. `Rank_Status` is the authoritative field for DNF/DNQ/DNS/DSQ; `Rank_num` is only for numeric comparisons. | Constitution Principle 4 (never dropped) + Principle 6 (traceability) — a downstream "why is this athlete not qualified" question must be answerable from the data itself. |
| **No numeric field for points/time criteria** | `clean_data()` only produces a clean numeric value for `Rank`. Sports evaluated by points or time (Figure Skating, Freestyle) need `Sec/Mtr/Pts` similarly cleaned. | Add an analogous `clean_result()` step producing a numeric `Result_num` from `Sec/Mtr/Pts`, and a `Result_Status` field for DNF/DNQ/DNS/DSQ (mirroring `Rank_Status`) — non-standard outcomes must not be encoded as fake numeric values in `Result_num`. | ETL spec, "Required Transformations": numeric fields authoritative; YAML Schema spec requires support for performance-value-based criteria, not just rank. |
| **Silent row removal** | Rows with `Team Members == "Yes"` are dropped with no record of how many or which. | Log the count of removed rows per run; include in the validation report (see below). | Constitution Principle 3 (uncertainty/changes must be visible, not silent). |
| **Validation stops at first error** | `validate_data()` calls `jsonschema.validate()`, which raises on the *first* error found, so only one problem is ever visible per run. | Replace with `Draft7Validator(schema).iter_errors(data)` — the same pattern Martin already uses in `validate_rules()` for YAML — to collect *all* errors in one pass. | ETL spec Acceptance Criteria: "validation report containing rejected records and reasons for rejection" — needs all errors, not just the first. |
| **Whole-batch validation** | The full dataset is validated as one array; a single bad record can obscure whether the rest of the batch is valid. | Validate row-by-row (or per-record via the validator), so each invalid record is individually reported with its own reason, while valid records still proceed. | Same acceptance criterion — rejected *records*, not just a pass/fail on the whole file. |
| **Inconsistent date format across files** | `streamlit/utils.py` parses dates as `%d.%m.%Y`; `mainv2.ipynb` uses `%d-%b-%Y`. The real current file (`data/data_2026-01-07.csv`) uses `%d-%b-%Y` (e.g. `23-Feb-2025`). | Standardize on `%d-%b-%Y` for the Podium export path; keep the format configurable per source, since manual CSV imports may differ. | Constitution Principle 5 (numeric/standardized values authoritative) + avoids silent parsing failures. |
| **No idempotency guarantee** | Running the pipeline twice on the same file isn't addressed. | Deduplicate output on a natural key: `source` + `Date` + `Person` + `Nation` + `Competition` + `Comp.SetDetail` + `Discipline`. Pipeline runs overwrite rather than append. | ETL spec Acceptance Criteria: same input twice → same output, no duplicates. |

## New: Not in Martin's Code

Martin's code only handles the Podium/Gracenote CSV path. Two additional
ingestion paths are required by the spec and need new functions with no
direct equivalent to reuse:

- `load_manual_csv(path)` — same target schema as `load_data()`, for
  competitions missing from the Podium export.
- `load_manual_form_entry(entry)` — for single results entered directly,
  not via file.
- A `source` field is added to every record (`"podium_csv"` /
  `"manual_csv"` / `"manual_form"`), so origin stays traceable
  regardless of entry path (constitution Principle 6).

All three paths converge into the same `clean_data()` / `clean_rank()` /
`clean_result()` / `validate_data()` functions — one standardized schema
regardless of source, per the ETL spec's core requirement.

## Pipeline Flow

```         
load (podium_csv | manual_csv | manual_form)
  -> select + tag source
  -> clean_data (column selection via dataschema.json)
  -> clean_rank (Rank_num + Rank_Status, incl. DNQ)
  -> clean_result (Result_num + Result_Status from Sec/Mtr/Pts)
  -> clean_dob, clean_olympic, date normalization
  -> validate (row-level, all errors collected)
  -> output: standardized dataset + validation report
```

The validation report (JSON or DataFrame) contains: total records in,
records passed, records rejected with reasons, rows removed as
team-member duplicates, and rows converted or flagged as DNF/DNQ/DNS/DSQ
per `Rank_Status` and `Result_Status`.

## Testing Approach

- Unit tests for `clean_rank()`/`clean_result()` against a fixed table
  of inputs (`DNS`, `DNF`, `DSQ`, `DNQ`, missing, valid numeric, valid
  string) — this is the highest-risk logic to get subtly wrong.
- Unit tests for `validate_data()` against deliberately broken sample
  records, checking that *all* injected errors are reported.
- Idempotency test: run the pipeline twice on the same file, assert
  identical output.

## Carried-Over Open Items (from spec, unaffected by this plan)

- Data volume sufficiency for validation — assessed once real data
  volume is known.
- `Is Olympic Discipline` sufficiency for Olympic Qualification System
  membership — provisional assumption, may need revisiting.