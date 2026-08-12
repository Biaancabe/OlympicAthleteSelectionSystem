---

editor_options: 
  markdown: 
    wrap: 72
---

# Spec: Selection Engine

## What

A rule-based engine that reads YAML-encoded selection criteria and applies them to standardized competition data, producing a transparent, auditable selection list.

## Why

Rule-based logic is chosen over Machine Learning because selection decisions must be transparent, reproducible, and directly defensible against the official criteria — a black-box model cannot provide the traceability that a high-stakes, regulated process like Olympic selection requires (see Vorstudie, 4.3).

## User Stories

- As Swiss Olympic staff, I need to see exactly which athletes qualify, nearly qualify, or don't qualify for a mission, so I can plan budgets and communicate decisions with confidence.
- As Swiss Olympic staff, I need cases with missing or incomplete data flagged for manual review — never silently defaulted to "not qualified" — so athletes aren't unfairly excluded due to data gaps (confirmed by Lionel Castella).
- As a federation or Swiss Olympic representative, I need every result to be traceable to the specific criterion it satisfied or failed, so decisions can be explained and challenged if necessary.
- As a thesis reviewer, I need the engine's output to be validated against historical selection decisions, so its correctness can be demonstrated.

## Output Categories

Every athlete evaluated against a sport's criteria falls into exactly one of four categories:

1.  **Fully qualified** — meets all required conditions.

2.  **Nearly qualified** — close to meeting conditions; strategically significant for budget planning, especially for smaller sports (see constitution).

3.  **Not qualified** — clearly does not meet conditions, based on complete data.

4.  **Manual review required** — data is missing, ambiguous, or insufficient to make an automated determination (confirmed preference by Lionel Castella; see constitution, Principle 3).

## Required Behavior

- Every YAML rule file is loaded and validated against `schemas/ruleschema.json` before being applied (see YAML Schema spec).
- Every selection outcome is linked back to the specific criterion/ condition that produced it (see constitution, Principle 6).
- DNF/DNQ/DNS/DSQ results are evaluated using their explicit codes, not treated as missing/null data (see constitution, Principle 4).
- Numeric time/performance fields are used for all comparisons; string representations are for display only (see constitution, Principle 5).
- The near-qualified threshold is applied as a configurable parameter, not hardcoded (placement to be resolved — see YAML Schema spec open questions).

## Output Format

Per Lionel Castella: the ideal end product is a **dashboard**, to track athletes' qualification status on an ongoing basis as a mission approaches. An export function (CSV/Excel) is desirable but lower priority.

**Decision**: this creates a scope tension with the Vorstudie, which explicitly lists GUI as out of scope. Rather than resolving this upfront, the approach is to start implementation with a lightweight notebook/Streamlit-style output (in the spirit of Martin's prototype `streamlit/utils.py`) and see how far that gets within the thesis scope. Whether it evolves toward something closer to Lionel's dashboard vision, or stays a demonstration layer, will be revisited once there's a working system to evaluate against.

## Validation

The engine's output must be evaluated against historical selection decisions to demonstrate correctness. Historical selection concept documents (PDF) are available from Lionel Castella for Paris 2024 and Milano Cortina 2026; further past/future missions to be confirmed with the Chef de Mission.

## Out of Scope

- Definition of the selection criteria themselves (federations'/Swiss Olympic's responsibility).
- Production-grade deployment or scheduling infrastructure.
- A full-featured GUI/dashboard application (pending clarification — see Output Format above).

## Acceptance Criteria

- Given a valid YAML rule file and standardized competition data, the engine produces exactly one output category per athlete, event/discipline, mission, and criteria version.
- Every "not qualified" or "fully qualified" result is fully explained by complete data — no result in these categories is based on incomplete data.
- Every result missing required data is categorized as "manual review required", never defaulted to "not qualified".
- Engine output for historical missions is compared against actual historical selection decisions, and deviations are categorised as system errors, data gaps, discretionary decisions, exceptional cases, or out-of-scope factors.

## Open Questions

- **Dashboard vs. GUI scope conflict**: not being resolved upfront — see Output Format decision above. Will be revisited once a working implementation exists to evaluate against.
- **Near-qualified threshold placement**: not being resolved for now — carried over as a deferred decision from the YAML Schema spec.
- **Validation tolerance**: not being defined for now — what counts as a "match" against historical decisions will be assessed once real validation runs are possible.

## Resolved (via Lionel Castella)

- Missing/incomplete data must result in "manual review required", not an automatic "not qualified".
- A dashboard-style, continuously updated view of qualification status is the preferred end product; CSV/Excel export is a secondary, lower-priority feature.
