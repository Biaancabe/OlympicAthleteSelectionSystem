import pandas as pd
from src.validation.reconcile import (
    reconcile, summarize, normalize_name, DEVIATION_REASONS,
)


# helper: build an engine selection list from (athlete, category) pairs
def _selection(pairs):
    return pd.DataFrame(
        [{"sport": "Skeleton", "athlete": a, "category": c,
          "decisive_route": None, "route_description": None} for a, c in pairs],
        columns=["sport", "athlete", "category", "decisive_route", "route_description"],
    )


# test: names are reduced to a comparable key regardless of the trailing suffix
def test_normalize_name_strips_suffix():
    assert normalize_name("Marco Odermatt (SUI, 08 Oct 1997)") == "marco odermatt"
    assert normalize_name("Marco Odermatt") == "marco odermatt"


# test: fully qualified and selected is an agreement
def test_qualified_and_selected_is_agreement():
    rec = reconcile(_selection([("Anna (SUI, 01 Jan 2000)", "fully_qualified")]),
                    ["Anna"])
    assert rec.loc[0, "outcome"] == "agreement"


# test: not qualified and not selected is an agreement
def test_not_qualified_and_not_selected_is_agreement():
    rec = reconcile(_selection([("Ben (SUI, 01 Jan 2000)", "not_qualified")]), [])
    assert rec.loc[0, "outcome"] == "agreement"


# test: fully qualified but not selected is a deviation (engine over-selects)
def test_qualified_but_not_selected_is_deviation():
    rec = reconcile(_selection([("Cara (SUI, 01 Jan 2000)", "fully_qualified")]), [])
    assert rec.loc[0, "outcome"] == "deviation"
    assert rec.loc[0, "direction"] == "engine_over"


# test: not qualified but selected is a deviation (engine under-selects)
def test_not_qualified_but_selected_is_deviation():
    rec = reconcile(_selection([("Dana (SUI, 01 Jan 2000)", "not_qualified")]),
                    ["Dana"])
    assert rec.loc[0, "outcome"] == "deviation"
    assert rec.loc[0, "direction"] == "engine_under"


# test: manual review is deferred, never counted as agreement or deviation
def test_manual_review_is_deferred():
    rec = reconcile(_selection([("Eli (SUI, 01 Jan 2000)", "manual_review_required")]),
                    ["Eli"])
    assert rec.loc[0, "outcome"] == "deferred"


# test: an athlete selected but never evaluated by the engine is flagged
def test_selected_but_not_evaluated():
    rec = reconcile(_selection([("Anna (SUI, 01 Jan 2000)", "fully_qualified")]),
                    ["Anna", "Unknown Athlete"])
    row = rec[rec["athlete"] == "Unknown Athlete"].iloc[0]
    assert row["outcome"] == "deviation"
    assert row["direction"] == "not_evaluated"


# test: the summary counts outcomes and, once assigned, reasons
def test_summarize_counts_outcomes_and_reasons():
    rec = reconcile(
        _selection([
            ("Anna (SUI, 01 Jan 2000)", "fully_qualified"),   # agreement
            ("Cara (SUI, 01 Jan 2000)", "fully_qualified"),   # deviation
            ("Dana (SUI, 01 Jan 2000)", "not_qualified"),     # deviation
        ]),
        ["Anna", "Dana"],
    )
    # assign a reason to one deviation, as an analyst would
    rec.loc[rec["athlete"].str.startswith("Cara"), "deviation_reason"] = \
        "discretionary_decision"
    s = summarize(rec)
    assert s["total"] == 3
    assert s["by_outcome"]["agreement"] == 1
    assert s["by_outcome"]["deviation"] == 2
    assert s["by_reason"]["discretionary_decision"] == 1


# test: the five reason labels are available as a defined set
def test_reason_set_is_defined():
    assert "system_error" in DEVIATION_REASONS
    assert len(DEVIATION_REASONS) == 5