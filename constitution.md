---

editor_options: 
  markdown: 
    wrap: 72
---

# Project Constitution — Swiss Olympic Athlete Selection Engine

## Purpose

Automate the selection of athletes for Olympic missions by making selection criteria machine-readable and applying them transparently to competition data.

## Core Principles

1.  **Config-driven Development (CDD)** — selection logic lives in YAML configuration files, not hardcoded in application code. Non-technical staff must be able to read and eventually edit criteria.

2.  **Schema-governed data contracts** — every YAML rule file and every ingested dataset must validate against a JSON Schema (Draft-07) before being used (`schemas/ruleschema.json`, `schemas/dataschema.json`). Invalid data/rules fail loudly, never silently.

3.  **Visible uncertainty over silent resolution** — when data is missing or ambiguous, the engine must output "manual review required", never guess, default to null, or assume worst-case.

4.  **Explicit handling of non-standard results** — DNF, DNQ, DNS, DSQ are distinct, meaningful states, not null values. They must be mapped explicitly, never dropped or coerced silently.

5.  **Numeric values as source of truth** — for all computation (ranking, time comparisons), numeric fields are authoritative. Formatted string representations are for display only.

6.  **Traceability** — every selection outcome (qualified / nearly qualified / not qualified / manual review) must be traceable back to the specific criterion/condition that produced it.

7.  **Backend flexibility** — code must not hardcode assumptions that only work with one database backend; switching between SQLite and PostgreSQL should require config changes only, not logic rewrites.

8.  **Explicit versioning of criteria** — selection criteria change annually. Every rule file must carry a `version` field (already present in Martin's schema) and changes must be traceable across Olympic cycles. Old versions are archived, never overwritten, so past selection decisions remain reproducible.

## Project Structure

(aligned with M. Rumo's prototype; subject to refinement after discussion with Martin/Lionel on the exact src/ layout)

```         
data/       raw + processed competition data
rules/      YAML selection criteria, one file per sport
schemas/    JSON Schema definitions for rules and data
src/        ETL, engine, and validation code
tests/      unit + validation tests
```

## Technology Stack

- Python (Pandas or Polars for transformation)
- PyYAML for reading criteria files
- `jsonschema` (Draft7Validator) for validating rules and data
- SQLite / PostgreSQL, interchangeable via config
- Git for version control of code and YAML files

## Non-negotiables

- No rule file is applied by the engine unless it passes schema validation.
- No silent data coercion — every transformation must be explicit and logged.
- Every engine run must produce an auditable output linking result → criterion.
- No rule version is overwritten — changes are versioned and archived.
