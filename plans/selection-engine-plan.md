---
editor_options: 
  markdown: 
    wrap: 72
---

# Plan: Selection Engine (Technical Implementation)

This plan describes *how* the Selection Engine spec
(`specs/selection-engine.md`) is implemented. It builds on the concepts
in Martin Rumo's prototype (`streamlit/app.py`, `streamlit/utils.py`,
and the `eval_all_of` / `eval_any_of` / `eligibility_checker` functions
in `archive/SO_Selectiontool_functions.ipynb`), but adapts the logic to
Bianca's extended YAML structure (explicit `criterion_id`,
`condition_id`, and `metric` / `operator` / `value` / `min` / `max`
comparison objects, plus the optional `age` field).

## Core idea

The engine evaluates, for each athlete in a sport, whether they meet the
selection criteria, and assigns exactly one of four categories. Every
outcome is traceable back to the specific criterion / condition that
produced it (constitution, Principle 6).

Because Bianca's YAML makes the comparison explicit (`operator`,
`metric`), the engine reads the intent directly instead of inferring it
from an ambiguous `[min, max]` array. This makes the evaluation logic
clearer than in Martin's prototype, not more complex.

## Evaluation hierarchy

Evaluation happens on three nested levels: Condition -> Criterion ->
Athlete.

### Level 1 - Condition

A single condition (e.g. "2x Top-8 World Cup 2025/26") is evaluated for
one athlete like this:

1. Filter the athlete's results to the condition's `competition`
   (match on `Comp.SetDetail`; a list means OR - any listed competition
   counts).
2. Filter to the condition's `date` range (inclusive start and end).
3. Classify each remaining result against the `performance` comparison
   (and `age`, if present) into one of three groups:
   - **full hit**: satisfies the comparison exactly
     (e.g. rank <= 8, or points >= 185).
   - **near hit**: misses the comparison but falls within the
     configurable percentage tolerance (see "Near-qualified tolerance").
   - **no hit**: clearly misses.
4. Compare the counts against `count_at_least`:
   - enough **full hits** -> condition **met**.
   - full + near hits together reach `count_at_least`, but full hits
     alone do not -> condition **nearly met**.
   - not enough even with near hits -> condition **not met**.
   - a relevant result exists but required data is missing or
     ambiguous (empty `Rank_num` / `Result_num`, or a status code like
     DNF/DNQ/DNS/DSQ where a placement would be needed) -> condition
     **manual review**.

### Level 2 - Criterion (a route)

A criterion may contain several conditions, joined by AND (all must
hold). Its status is derived from its conditions:

- all conditions **met** -> criterion **met**.
- every condition is **met** or **nearly met** (at least one nearly)
  -> criterion **nearly met**.
- at least one condition is clearly **not met** (with complete data)
  -> criterion **not met**.
- otherwise, if missing data blocks a decision -> criterion
  **manual review**.

### Level 3 - Athlete

An athlete is evaluated against all criteria (routes) of the sport,
joined by OR (any one route qualifies). The final category is decided in
this strict priority order:

1. at least one criterion **met** -> **fully qualified**.
2. else, at least one criterion **nearly met** -> **nearly qualified**.
3. else, missing data could still change the outcome of some route
   -> **manual review required**.
4. else (all routes clearly not met, data complete) -> **not
   qualified**.

The order matters: fully > nearly > manual review > not qualified.
A route that is cleanly and fully met makes the athlete fully qualified
even if *other* (unneeded) routes have data gaps - a data gap only
triggers manual review when it actually blocks an otherwise-possible
qualification.

## Comparison operators

The engine implements the four operators from the rule schema. For a
value `x` from the data:

- `less_or_equal`: x <= value
- `greater_or_equal`: x >= value
- `equal`: x == value
- `between`: min <= x <= max

`metric` tells the engine which cleaned column to read:
- `rank` -> `Rank_num`
- `points` / `time` -> `Result_num`
- `age` -> derived from `DoB` (see "Age handling")

## Near-qualified tolerance

"Nearly qualified" uses a **configurable percentage tolerance** applied
to the threshold, and the direction depends on the operator:

- rank-style (`less_or_equal`, `between` on rank; smaller is better):
  a result just *above* the threshold is a near hit.
  E.g. Top-8 with 20% tolerance -> ranks 9-10 (8 * 1.2 = 9.6) are near.
- value-style (`greater_or_equal` on points; larger is better):
  a result just *below* the threshold is a near hit.
  E.g. 185 points with 20% tolerance -> 148-184 (185 * 0.8) are near.

The tolerance is a single configurable parameter (not hardcoded), in
line with the spec. Its exact placement (per-criterion in YAML vs. a
global engine setting) is still an open question; for the first
implementation it is an engine-level parameter with a sensible default.

Scope note: for the first version, "nearly qualified" is defined by
this tolerance combined with `count_at_least` (Weg A - a clear,
explainable threshold). A finer graded "closeness score" (Weg B) is
noted as a possible later refinement in the thesis discussion, not built
now.

## Age handling

Age criteria (`age` field, e.g. Skeleton Route 5, Bobsleigh Route 5) are
structurally modelled like performance (`metric: age`, an operator, and
a value). The reference date for the age calculation, whether age must
hold at each qualifying result or at a fixed cutoff, and whether it is
evaluated automatically or flagged for manual review, are an **open
question sent to Lionel Castella**. Until confirmed, the engine computes
age from `DoB` and applies the operator; borderline cases can be routed
to manual review once the rule is clarified.

## Traceability output

For each athlete, the engine returns not just the final category but the
full evaluation trail: for every criterion (by `criterion_id`) and every
condition (by `condition_id`), its status and the specific results
(evidence) that were counted. This satisfies Principle 6 and mirrors the
evidence-based display in Martin's `app.py` (green / yellow / red per
criterion and condition).

## DNF / DNQ / DNS / DSQ handling

These are read from `Rank_Status` / `Result_Status`, not treated as
missing values (constitution, Principle 4). A status code where a
placement would be required means the result cannot count as a hit; if
it is decisive for whether a route could be met, it routes to manual
review rather than being silently treated as "not met".

## Module layout (proposed)

```
src/
  engine/
    __init__.py
    compare.py        # the four operators + tolerance logic
    evaluate.py       # condition -> criterion -> athlete evaluation
    engine.py         # orchestration: load rules + data, run, return results
tests/
  engine/
    test_compare.py
    test_evaluate.py
```

## Inputs and preconditions

- Cleaned competition data from the ETL pipeline
  (`output/cleaned_data.csv`, validated against `dataschema.json`).
- A rule file validated against `schemas/ruleschema.json` before use
  (constitution, Principle 2; no rule file is applied unless it passes
  validation).
- Rules are filtered to the relevant `gender` / `discipline` before
  evaluation (as Martin does with `filter_rules`).

## Open questions carried into implementation

- Near-qualified tolerance: exact value and placement (per-criterion vs.
  global) - default global parameter for now.
- Age criterion evaluation details - pending Lionel's answer.
- Validation tolerance against historical decisions - assessed later
  when real validation runs are possible.