import re
import pandas as pd


# the five categories a deviation can be assigned to. The assignment itself is
# an analytical judgement and is not done automatically: the framework only
# identifies that a deviation exists and in which direction, and leaves the
# reason to be filled in during the analysis.
DEVIATION_REASONS = [
    "system_error",
    "data_gap",
    "discretionary_decision",
    "exceptional_case",
    "out_of_scope",
]

# the selection outcome the engine's category implies. fully qualified is
# expected to be selected, not qualified and nearly qualified are expected not
# to be selected by the automatic criteria, and manual review carries no
# automatic expectation because the engine deliberately did not decide.
# This mapping is an explicit modelling choice and can be adjusted here.
_EXPECTED_SELECTION = {
    "fully_qualified": True,
    "nearly_qualified": False,
    "not_qualified": False,
    "manual_review_required": None,
}


# reduce an athlete label to a comparable key. The engine list carries names in
# the form "Marco Odermatt (SUI, 08 Oct 1997)", whereas a selection decision
# may list only "Marco Odermatt". The suffix in parentheses is therefore
# removed, and the remainder is lower-cased and stripped of surrounding and
# repeated whitespace.
def normalize_name(name):
    base = re.sub(r"\(.*?\)", "", str(name))
    return re.sub(r"\s+", " ", base).strip().lower()


# classify one athlete by comparing the engine's expectation with the actual
# selection decision.
def _classify(athlete, category, expected, selected, in_engine):
    if not in_engine:
        # the athlete was selected but never evaluated by the engine, e.g.
        # because no result for them was present in the data
        return {
            "athlete": athlete, "category": None,
            "expected_selected": None, "actually_selected": selected,
            "outcome": "deviation", "direction": "not_evaluated",
            "deviation_reason": None,
        }
    if expected is None:
        # manual review: the engine deferred the decision to a human, so the
        # outcome is neither an agreement nor a deviation
        outcome, direction = "deferred", None
    elif expected == selected:
        outcome, direction = "agreement", None
    else:
        outcome = "deviation"
        # expected selection but not selected, or vice versa
        direction = "engine_over" if expected else "engine_under"
    return {
        "athlete": athlete, "category": category,
        "expected_selected": expected, "actually_selected": selected,
        "outcome": outcome, "direction": direction,
        "deviation_reason": None,
    }


# compare the engine's selection list against the athletes actually selected.
# Returns one row per athlete, from either list, with the comparison outcome
# and an empty reason column to be filled during the analysis.
def reconcile(selection_list, selected_names, normalize=normalize_name):
    selected_keys = {normalize(n) for n in selected_names}

    rows = []
    seen = set()
    for _, r in selection_list.iterrows():
        key = normalize(r["athlete"])
        seen.add(key)
        expected = _EXPECTED_SELECTION.get(r["category"])
        rows.append(_classify(r["athlete"], r["category"], expected,
                              key in selected_keys, in_engine=True))

    # selected athletes that the engine never evaluated
    for name in selected_names:
        if normalize(name) not in seen:
            rows.append(_classify(name, None, None, True, in_engine=False))

    columns = ["athlete", "category", "expected_selected", "actually_selected",
               "outcome", "direction", "deviation_reason"]
    return pd.DataFrame(rows, columns=columns)


# summarise a reconciliation: counts by outcome, by deviation direction, and,
# once reasons have been assigned, by reason.
def summarize(reconciliation):
    summary = {
        "total": len(reconciliation),
        "by_outcome": reconciliation["outcome"].value_counts().to_dict(),
    }
    deviations = reconciliation[reconciliation["outcome"] == "deviation"]
    summary["by_direction"] = deviations["direction"].value_counts().to_dict()
    summary["by_reason"] = (
        deviations["deviation_reason"].dropna().value_counts().to_dict()
    )
    return summary