---
editor_options: 
  markdown: 
    wrap: 72
---

# Spec: ETL Pipeline (Data Integration Layer)

## What

A pipeline that ingests competition data from Swiss Olympic's available
sources and transforms it into a standardized, validated format that the
Selection Engine can consume.

## Why

Selection criteria can only be applied automatically if competition data
is available in one consistent, reliable structure. Today, Swiss Olympic
has no automatic connection between raw competition results and the
criteria that decide qualification — this pipeline is the bridge.

## Inputs

- **Primary source**: a daily CSV export from Swiss Olympic's Podium
  platform (Gracenote-sourced competition data), semicolon-separated
  (e.g. `results_DDMMYYYY.csv` / `data_YYYY-MM-DD.csv`). This is a
  daily batch export — no real-time or API access, and none is
  required.
- **Observed fields** (from `data/data_2026-01-07.csv`): `Date`, `Year`,
  `Competition`, `CompetitionSet`, `Comp.SetDetail`, `Sport`,
  `Discipline`, `Gender`, `Class`, `Phase`, `Rank`, `Medal`,
  `Team Members`, `Person/Team`, `Person`, `Person First Name`,
  `Person Last Name`, `PersonGender`, `Team`, `Nationality`, `DoB`,
  `YoB`, `Age (days)`, `Age`, `Country`, `Country Code`, `Continent`,
  `Result`, `Sec/Mtr/Pts`, `Host City`, `Host Country`, `Host
  Continent`, `# Participants`, `# Countries`, `# Continents`,
  `World Ranking`, `Rank Within Country`, `Is Olympic Discipline`.
- **Time representation**: `Result` (formatted string, e.g. `1:26.13`)
  and `Sec/Mtr/Pts` (numeric) both exist — the numeric field is
  authoritative for computation (see constitution, Principle 5).
- **Fallback sources**: manual CSV import and a manual entry form, for
  competitions or results not covered by the Podium/Gracenote export
  (relevant especially for smaller sports).
- **Historical data**: historical selection concepts exist as PDF
  documents; Lionel Castella can provide these for Paris 2024 and
  Milano Cortina 2026, with further past/future missions to be
  confirmed with the Chef de Mission. Relevant primarily for validating
  the Selection Engine, but the ETL pipeline must be able to ingest
  competition data far enough back to support that validation.

## Data Privacy

Confirmed by Lionel Castella: no anonymization or pseudonymization is
required. Competition results are official, public-domain data.

## User Stories

- As the Selection Engine, I need competition data in one consistent
  schema, regardless of which source it came from, so that rule
  evaluation doesn't need source-specific logic.
- As a Swiss Olympic staff member, I need results from competitions
  missing in the Podium export to still be usable, so smaller sports
  aren't systematically disadvantaged.
- As a thesis reviewer, I need every transformation step to be
  traceable, so the pipeline's output can be audited against the raw
  input.

## Required Transformations

- Unify field names across sources (Podium export vs. manual CSV vs.
  manual form must map to the same standardized schema).
- Normalize data types (numbers, dates) consistently.
- Standardize date formats.
- Preserve the numeric representation of time/performance values
  (`Sec/Mtr/Pts`) as the authoritative value for computation; the
  formatted `Result` string is for display only (see constitution,
  Principle 5).
- Map non-standard result codes (DNF, DNQ, DNS, DSQ) explicitly — these
  are meaningful states, never dropped or treated as null (see
  constitution, Principle 4).
- Exclude/flag records that are structurally invalid or incomplete
  rather than silently passing them through (see constitution, Principle
  3: visible uncertainty).

## Acceptance Criteria

- Given a daily Podium/Gracenote CSV export, the pipeline produces a
  dataset that validates against `schemas/dataschema.json`.
- Given a manual CSV import with the same expected structure, the
  pipeline produces output equivalent to the Podium/Gracenote path.
- DNF/DNQ/DNS/DSQ results are present in the output as explicit,
  distinguishable values — not missing rows, not null.
- Any record that fails schema validation is reported, not silently
  discarded.
- Given invalid or incomplete records, the pipeline produces a
  validation report containing rejected records and reasons for
  rejection.
- Given the same raw input twice, the pipeline produces the same
  standardized output without creating duplicates.
- Every transformed field can be traced back to its original source
  field in the Podium export or manual input.

## Out of Scope

- The Gracenote/Podium infrastructure itself (only the daily CSV export
  is used as given).
- Real-time or API-based data access.
- Definition of the selection criteria (handled in the YAML Schema
  spec).
- Production-grade deployment or scheduling infrastructure.

## Open Questions

- **Data volume** available may be insufficient for full quantitative
  validation of the pipeline — deferred, to be assessed once working
  with the real data.
- **Pilot sports**: Martin's prototype already contains rule files for
  10 sports (see `rules/rules.json`), covering ranking-based,
  performance-value-based, and age-restricted criteria types. Final
  confirmation of which sports are prioritized may still come from
  Lionel Castella, but the ETL pipeline is not blocked by this — data
  for all 10 sports can be ingested from the start.

## Risks

- **`Is Olympic Discipline` may not be precise enough**: it flags
  discipline-level Olympic status, not competition-level Olympic
  Qualification System membership. For now, it is used as-is; if this
  turns out to be insufficient once applied to real criteria, a
  derived field or manual mapping table can be added later.

## Resolved (via Lionel Castella)

- The daily Podium/Gracenote CSV export is the working data source for
  the thesis; no separate database access is required.
- No anonymization/pseudonymization of athlete data required.
- Historical selection documents for Paris 2024 and Milano Cortina 2026
  are available on request.

## Resolved (provisional, Bianca's decision)

- **Olympic Qualification System membership**: for now, the existing
  `Is Olympic Discipline` field is assumed sufficient to determine
  competition relevance. This is a working assumption, not a final
  answer — may be revisited if it proves insufficient once applied to
  real criteria.
