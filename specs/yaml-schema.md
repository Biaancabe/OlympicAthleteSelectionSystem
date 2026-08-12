---
editor_options: 
  markdown: 
    wrap: 72
---

# Spec: Machine-Readable Criteria Schema (YAML)

## What

A YAML-based schema that encodes sports federations' selection criteria — currently published as PDF documents — into a structured, machine-readable, and version-controlled format.

## Why

PDF criteria cannot be processed automatically and create a structural gap between the people who write the rules (federations) and the people who apply them (Swiss Olympic). YAML is chosen over JSON or XML because it is far more human-readable, supports comments, and can still be validated against a strict JSON Schema — so it works for both non-technical staff (readability) and the Selection Engine (structure).

## User Stories

- As a Swiss Olympic staff member without a programming background, I need to read a YAML rule file and understand which conditions an athlete must meet, so I can verify or discuss criteria without needing a developer.
- As the Selection Engine, I need every rule file to follow one strict, validated structure, so criteria evaluation logic doesn't need special cases per sport.
- As a federation/Swiss Olympic representative, I need criteria that change from year to year to be versioned, so past selection decisions remain reproducible under the rules that applied at the time (see constitution, Principle 8).

## Criteria Types to Support

The schema must be expressive enough to cover, at minimum:

- **Rank/placement** (e.g., top-3 at World Championships)
- **Points / performance values** (e.g., World Cup points thresholds)
- **Time** (numeric, not formatted string — see constitution, Principle 5)
- **Age restrictions** (e.g., class: Seniors / Juniors / Under 23)
- **Gender and discipline** scoping per criterion
- **Combined logic**: a criterion may require multiple conditions together, with a minimum count of qualifying results (`count_at_least`)

## Required Structure

### Base (Martin Rumo's prototype)

This is the starting point, taken as-is from `schemas/ruleschema.json`, referenced consistently across `notebooks/main.ipynb`, `notebooks/mainv2.ipynb`, and `streamlit/utils.py`:

- Each rule file has file-level metadata: `Description`, `created at`, `updated at`, `version` (pattern `X.Y`).
- Each rule file contains a `rule_tree` with a `description`, `sport`, optional `class`, and one or more `criteria`.
- Each criterion has a `description`, `priority`, and one or more `conditions` (competition, date range, performance range, `count_at_least`).
- Every rule file must validate against `schemas/ruleschema.json` (JSON Schema, Draft-07) before being usable by the Selection Engine (see constitution, Principle 2).

### Extensions (Bianca's implementation)

Martin's schema is a reference starting point, not a fixed target that requires his sign-off. Bianca owns the implementation and is responsible for making the working system meet this thesis's traceability and precision requirements — Martin's code is something to orient around, not something that gates decisions:

- Each criterion should have a stable `criterion_id`.
- Each condition should have a stable `condition_id`.
  - **Rationale**: these IDs are what allow the Selection Engine to link each output back to the exact rule condition that produced it (see constitution, Principle 6). Without stable IDs, traceability would depend on fragile text matching against `description` fields.
- Each numeric condition must define an explicit comparison operator, such as `less_or_equal`, `greater_or_equal`, `equal`, or `between`.
  - **Rationale**: Martin's current schema encodes ranges implicitly as a `[min, max]` array (e.g. `"performance": {"type": "array", "description": "Performance rank range [min, max]"}`). This works for closed ranges but is ambiguous for open-ended conditions (e.g. "at least rank X" or "under Y seconds"). An explicit operator removes that ambiguity.

These extensions go beyond `schemas/ruleschema.json` as it stands today. That's expected and intentional: Martin explicitly positioned his code as a starting point for Bianca to build on, not a spec to replicate exactly. The priority is a working, traceable system.

Note: an older, structurally different variant (nested `any_of`/`all_of` qualification groups) exists in `archive/Winter_olympic_swiss.ipynb`. This is **not** part of Martin's prototype — it originates from a separate, earlier project (authored by Andrin Kohler, with its own data folder and Streamlit/Cloudflare setup) and is archived accordingly. It is not used as a basis for this schema.

## Near-Qualified Threshold

Per Lionel Castella: the boundary for "near-qualified" is not fixed by the federations and should be configurable rather than hardcoded. This spec treats the threshold as a parameter, not a constant — exact placement (per-criterion in the YAML vs. a separate engine-level config) is an open question below.

## Out of Scope

- Defining what the selection criteria actually are — this remains the responsibility of the federations and Swiss Olympic.
- Automatic PDF-to-YAML conversion — translation from PDF to YAML is manual in this thesis; automation is a possible future extension only.
- A full YAML-generator UI — flagged in the Vorstudie as a risk of scope creep; treated as an optional extension, not a core deliverable.

## Acceptance Criteria

- A rule file for each pilot sport validates against `schemas/ruleschema.json` (extended version) without errors.
- The schema can express all criteria types required by the chosen pilot sports (rank-based, performance-value-based, age-restricted — pending final pilot sport selection, see ETL spec open questions).
- A non-technical reader (e.g., Lionel) can read a sample YAML file and correctly describe, in their own words, which conditions an athlete must meet.
- Each condition in a rule file can be traced 1:1 to a specific outcome in the Selection Engine's output, via `criterion_id`/`condition_id` (see constitution, Principle 6).

## Open Questions

- **Placement of the near-qualified threshold**: not being resolved for now — treated as a deferred decision. Current default assumption is criterion-level configuration in YAML, with optional engine-level defaults, but this is not final.
- **Scope of the YAML-generator tool**: left open for now; not needed to proceed with the core schema work.

## Resolved

- **Schema structure (base)**: `schemas/ruleschema.json` (flat `criteria` → `conditions` structure) is confirmed as the basis, matching Martin's active prototype code. The nested `any_of`/`all_of` variant found in `archive/Winter_olympic_swiss.ipynb` belongs to an unrelated, earlier project and is not used.
- **Schema extensions**: `criterion_id`, `condition_id`, and explicit comparison operators are adopted as Bianca's own extension of Martin's base schema. This does not require Martin's approval — his prototype is a reference to orient around, and Bianca is responsible for the working implementation.
