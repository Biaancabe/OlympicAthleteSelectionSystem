import pandas as pd
from src.engine.evaluate import evaluate_condition, evaluate_criterion, evaluate_athlete


# helper: build a small results DataFrame for one athlete
def make_results(rows):
    return pd.DataFrame(rows)


# a simple reusable condition: Top-8 at World Cup, needs 2 results
TOP8_WC = {
    "condition_id": "test_c1",
    "description": "Top-8 WC",
    "competition": ["Test World Cup"],
    "date": ["2025-11-01", "2026-01-18"],
    "performance": {"metric": "rank", "operator": "between", "min": 1, "max": 8},
    "count_at_least": 2,
}

def test_condition_met_two_full_hits():
    # athlete has two Top-8 results at the World Cup -> condition met
    results = make_results([
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-01",
         "Rank_num": 3, "Rank_Status": None, "Result_num": None, "Result_Status": None},
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-15",
         "Rank_num": 6, "Rank_Status": None, "Result_num": None, "Result_Status": None},
    ])
    res = evaluate_condition(results, TOP8_WC)
    assert res["status"] == "met"


def test_condition_not_met_only_one_hit():
    # only one Top-8 result, but 2 are needed -> not met (no near, no status codes)
    results = make_results([
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-01",
         "Rank_num": 3, "Rank_Status": None, "Result_num": None, "Result_Status": None},
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-15",
         "Rank_num": 25, "Rank_Status": None, "Result_num": None, "Result_Status": None},
    ])
    res = evaluate_condition(results, TOP8_WC)
    assert res["status"] == "not_met"


def test_condition_one_full_one_miss_is_not_met():
    # one full hit (rank 5), one miss (rank 9): at condition level this is
    # not_met. nearly_met is decided at criterion level, not here.
    results = make_results([
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-01",
         "Rank_num": 5, "Rank_Status": None, "Result_num": None, "Result_Status": None},
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-15",
         "Rank_num": 9, "Rank_Status": None, "Result_num": None, "Result_Status": None},
    ])
    res = evaluate_condition(results, TOP8_WC)
    assert res["status"] == "not_met"


def test_condition_manual_review_missing_value():
    # one full hit + one result with NO rank and NO status code:
    # genuinely unknown -> could tip over the threshold -> manual review
    results = make_results([
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-01",
         "Rank_num": 5, "Rank_Status": None, "Result_num": None, "Result_Status": None},
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-15",
         "Rank_num": None, "Rank_Status": None, "Result_num": None, "Result_Status": None},
    ])
    res = evaluate_condition(results, TOP8_WC)
    assert res["status"] == "manual_review"


def test_condition_status_code_is_not_a_hit():
    # a DNS is a KNOWN non-result, not missing data:
    # one full hit + one DNS, 2 needed -> not met (no manual review)
    results = make_results([
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-01",
         "Rank_num": 5, "Rank_Status": None, "Result_num": None, "Result_Status": None},
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-15",
         "Rank_num": None, "Rank_Status": "DNS", "Result_num": None, "Result_Status": None},
    ])
    res = evaluate_condition(results, TOP8_WC)
    assert res["status"] == "not_met"


# a criterion with two conditions (AND): both must hold
TWO_COND_CRITERION = {
    "criterion_id": "test_r1",
    "description": "Two conditions",
    "priority": 1,
    "conditions": [
        {
            "condition_id": "test_r1_c1",
            "description": "Top-3 WM",
            "competition": ["Test WM"],
            "date": ["2025-01-01", "2025-12-31"],
            "performance": {"metric": "rank", "operator": "between", "min": 1, "max": 3},
            "count_at_least": 1,
        },
        {
            "condition_id": "test_r1_c2",
            "description": "Top-8 WC",
            "competition": ["Test World Cup"],
            "date": ["2025-11-01", "2026-01-18"],
            "performance": {"metric": "rank", "operator": "between", "min": 1, "max": 8},
            "count_at_least": 1,
        },
    ],
}


def test_criterion_met_both_conditions():
    # one Top-3 WM result AND one Top-8 WC result -> criterion met
    results = make_results([
        {"Comp.SetDetail": "Test WM", "Date": "2025-02-15",
         "Rank_num": 2, "Rank_Status": None, "Result_num": None, "Result_Status": None},
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-01",
         "Rank_num": 5, "Rank_Status": None, "Result_num": None, "Result_Status": None},
    ])
    res = evaluate_criterion(results, TWO_COND_CRITERION)
    assert res["status"] == "met"


def test_criterion_manual_review_when_one_not_met_one_unknown():
    # WM condition not met (rank 20), WC condition manual_review
    # (result with no rank and no status -> genuinely unknown).
    # manual_review propagates: the unknown result could affect the outcome.
    results = make_results([
        {"Comp.SetDetail": "Test WM", "Date": "2025-02-15",
         "Rank_num": 20, "Rank_Status": None, "Result_num": None, "Result_Status": None},
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-01",
         "Rank_num": None, "Rank_Status": None, "Result_num": None, "Result_Status": None},
    ])
    res = evaluate_criterion(results, TWO_COND_CRITERION)
    assert res["status"] == "manual_review"


# two criteria (routes) joined by OR: any one qualifies
TWO_CRITERIA = [
    {
        "criterion_id": "route_1",
        "description": "Top-3 WM",
        "priority": 1,
        "conditions": [{
            "condition_id": "route_1_c1",
            "description": "Top-3 WM",
            "competition": ["Test WM"],
            "date": ["2025-01-01", "2025-12-31"],
            "performance": {"metric": "rank", "operator": "between", "min": 1, "max": 3},
            "count_at_least": 1,
        }],
    },
    {
        "criterion_id": "route_2",
        "description": "Top-8 WC",
        "priority": 2,
        "conditions": [{
            "condition_id": "route_2_c1",
            "description": "Top-8 WC",
            "competition": ["Test World Cup"],
            "date": ["2025-11-01", "2026-01-18"],
            "performance": {"metric": "rank", "operator": "between", "min": 1, "max": 8},
            "count_at_least": 1,
        }],
    },
]


def test_athlete_fully_qualified_one_route_met():
    # fails route 1 (rank 20 at WM) but meets route 2 (rank 5 at WC)
    # -> one met route is enough -> fully qualified
    results = make_results([
        {"Comp.SetDetail": "Test WM", "Date": "2025-02-15",
         "Rank_num": 20, "Rank_Status": None, "Result_num": None, "Result_Status": None},
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-01",
         "Rank_num": 5, "Rank_Status": None, "Result_num": None, "Result_Status": None},
    ])
    res = evaluate_athlete(results, TWO_CRITERIA)
    assert res["category"] == "fully_qualified"


def test_athlete_manual_review_beats_not_qualified():
    # route 1 not met (rank 20), route 2 has a result with no rank and no status
    # -> no met route, but genuinely missing data could still qualify -> manual review
    results = make_results([
        {"Comp.SetDetail": "Test WM", "Date": "2025-02-15",
         "Rank_num": 20, "Rank_Status": None, "Result_num": None, "Result_Status": None},
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-01",
         "Rank_num": None, "Rank_Status": None, "Result_num": None, "Result_Status": None},
    ])
    res = evaluate_athlete(results, TWO_CRITERIA)
    assert res["category"] == "manual_review_required"


# a criterion restricted to one discipline
HALFPIPE_CRITERION = {
    "criterion_id": "test_hp",
    "description": "Top-8 WC Halfpipe",
    "priority": 1,
    "discipline": ["Halfpipe"],
    "conditions": [{
        "condition_id": "test_hp_c1",
        "description": "Top-8 WC",
        "competition": ["Test World Cup"],
        "date": ["2025-11-01", "2026-01-18"],
        "performance": {"metric": "rank", "operator": "between", "min": 1, "max": 8},
        "count_at_least": 1,
    }],
}


def test_criterion_ignores_other_disciplines():
    # a Top-8 result in Big Air must NOT count for a Halfpipe criterion
    results = make_results([
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-01", "Discipline": "Big Air",
         "Rank_num": 5, "Rank_Status": None, "Result_num": None, "Result_Status": None},
    ])
    res = evaluate_criterion(results, HALFPIPE_CRITERION)
    assert res["status"] == "not_met"


def test_criterion_counts_matching_discipline():
    # the same result, but in Halfpipe -> counts
    results = make_results([
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-01", "Discipline": "Halfpipe",
         "Rank_num": 5, "Rank_Status": None, "Result_num": None, "Result_Status": None},
    ])
    res = evaluate_criterion(results, HALFPIPE_CRITERION)
    assert res["status"] == "met"


# --- age gate (birth-date cutoff) ---------------------------------------

import pytest
from src.engine.compare import satisfies_date

# a condition that requires Top-8 at the WC AND a birth date on/after a cutoff
AGE_GATED = {
    "condition_id": "age_c1",
    "description": "Top-8 WC & born on/after 2001-02-07",
    "competition": ["Test World Cup"],
    "date": ["2025-11-01", "2026-01-18"],
    "performance": {"metric": "rank", "operator": "between", "min": 1, "max": 8},
    "age": {"metric": "birth_date", "operator": "on_or_after", "value": "2001-02-07"},
    "count_at_least": 1,
}


def _one_top8():
    # one qualifying Top-8 WC result (performance side is always satisfied)
    return make_results([
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-01",
         "Rank_num": 5, "Rank_Status": None, "Result_num": None, "Result_Status": None},
    ])


# satisfies_date: the pure comparison, incl. the boundary day and unknown case
def test_satisfies_date_on_cutoff_counts():
    # born exactly on the cutoff -> on_or_after is inclusive -> True
    assert satisfies_date("2001-02-07", "on_or_after", "2001-02-07") is True

def test_satisfies_date_day_after_counts():
    assert satisfies_date("2001-02-08", "on_or_after", "2001-02-07") is True

def test_satisfies_date_day_before_fails():
    assert satisfies_date("2001-02-06", "on_or_after", "2001-02-07") is False

def test_satisfies_date_missing_dob_is_unknown():
    # unknown birth date -> None (undecidable), NOT False
    assert satisfies_date(None, "on_or_after", "2001-02-07") is None


# age gate inside evaluate_condition
def test_condition_age_ok_falls_through_to_performance():
    # young enough (born on cutoff) + a Top-8 result -> met
    res = evaluate_condition(_one_top8(), AGE_GATED, dob="2001-02-07")
    assert res["status"] == "met"

def test_condition_age_too_old_is_not_met():
    # born before the cutoff -> ineligible -> not_met, even with a Top-8 result
    res = evaluate_condition(_one_top8(), AGE_GATED, dob="2000-12-31")
    assert res["status"] == "not_met"

def test_condition_age_unknown_is_manual_review():
    # no birth date -> eligibility undecidable -> manual_review, not a silent pass
    res = evaluate_condition(_one_top8(), AGE_GATED, dob=None)
    assert res["status"] == "manual_review"

# --- nearly_met at criterion level -----------------------------------------

# a two-condition criterion: WM + WC both needed
TWO_PERF_CRITERION = {
    "criterion_id": "test_2perf",
    "description": "WM + WC route",
    "priority": 1,
    "conditions": [
        {
            "condition_id": "c_wm",
            "description": "Top-5 WM",
            "competition": ["Test WM"],
            "date": ["2025-01-01", "2026-01-18"],
            "performance": {"metric": "rank", "operator": "between", "min": 1, "max": 5},
            "count_at_least": 1,
        },
        {
            "condition_id": "c_wc",
            "description": "Top-8 WC",
            "competition": ["Test World Cup"],
            "date": ["2025-11-01", "2026-01-18"],
            "performance": {"metric": "rank", "operator": "between", "min": 1, "max": 8},
            "count_at_least": 1,
        },
    ],
}


def test_criterion_nearly_met_one_perf_met_one_not_met():
    # WM met (rank 3), WC not met (rank 12) -> criterion is nearly_met
    results = make_results([
        {"Comp.SetDetail": "Test WM", "Date": "2025-02-15",
         "Rank_num": 3, "Rank_Status": None, "Result_num": None, "Result_Status": None},
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-01",
         "Rank_num": 12, "Rank_Status": None, "Result_num": None, "Result_Status": None},
    ])
    res = evaluate_criterion(results, TWO_PERF_CRITERION)
    assert res["status"] == "nearly_met"


def test_criterion_not_met_both_perf_not_met():
    # both conditions not met -> not nearly_met, simply not_met
    results = make_results([
        {"Comp.SetDetail": "Test WM", "Date": "2025-02-15",
         "Rank_num": 10, "Rank_Status": None, "Result_num": None, "Result_Status": None},
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-01",
         "Rank_num": 12, "Rank_Status": None, "Result_num": None, "Result_Status": None},
    ])
    res = evaluate_criterion(results, TWO_PERF_CRITERION)
    assert res["status"] == "not_met"


def test_criterion_single_perf_cond_has_no_nearly_met():
    # a criterion with only one performance condition cannot be nearly_met
    single_cond_crit = {
        "criterion_id": "test_single",
        "description": "single cond",
        "priority": 1,
        "conditions": [
            {
                "condition_id": "c1",
                "description": "Top-8 WC",
                "competition": ["Test World Cup"],
                "date": ["2025-11-01", "2026-01-18"],
                "performance": {"metric": "rank", "operator": "between", "min": 1, "max": 8},
                "count_at_least": 2,
            }
        ],
    }
    results = make_results([
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-01",
         "Rank_num": 5, "Rank_Status": None, "Result_num": None, "Result_Status": None},
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-15",
         "Rank_num": 12, "Rank_Status": None, "Result_num": None, "Result_Status": None},
    ])
    res = evaluate_criterion(results, single_cond_crit)
    assert res["status"] == "not_met"


# --- empty competition list = no competition filter -------------------------

# same rank condition, once with an empty competition list ("any competition"),
# once with a named list. Date window is identical.
ANY_COMP = {
    "condition_id": "any_c1",
    "description": "Top-3 at any competition",
    "competition": [],
    "date": ["2024-01-01", "2024-12-31"],
    "performance": {"metric": "rank", "operator": "less_or_equal", "value": 3},
    "count_at_least": 1,
}

NAMED_COMP = {
    "condition_id": "named_c1",
    "description": "Top-3 at Worlds only",
    "competition": ["Test Worlds"],
    "date": ["2024-01-01", "2024-12-31"],
    "performance": {"metric": "rank", "operator": "less_or_equal", "value": 3},
    "count_at_least": 1,
}


def _two_comps_top3():
    # two Top-3 results at different competitions, both inside the date window
    return make_results([
        {"Comp.SetDetail": "Test Worlds", "Date": "2024-05-01",
         "Rank_num": 3, "Rank_Status": None, "Result_num": None, "Result_Status": None},
        {"Comp.SetDetail": "Some Small Meeting", "Date": "2024-05-02",
         "Rank_num": 2, "Rank_Status": None, "Result_num": None, "Result_Status": None},
    ])


def test_empty_competition_matches_any():
    # empty competition list -> no name filter, date window alone decides ->
    # both Top-3 results count
    res = evaluate_condition(_two_comps_top3(), ANY_COMP)
    assert res["status"] == "met"
    assert len(res["full_hits"]) == 2


def test_named_competition_still_excludes_others():
    # non-empty list -> only the named competition counts; the small meeting
    # is filtered out even though it is a Top-3 in-window result
    res = evaluate_condition(_two_comps_top3(), NAMED_COMP)
    assert res["status"] == "met"
    assert len(res["full_hits"]) == 1
    assert res["full_hits"][0]["value"] == 3

# --- class filter (age category: Elite vs U23) ------------------------------

# a criterion restricted to one age category (Class)
U23_CRITERION = {
    "criterion_id": "test_u23",
    "description": "Top-3 U23",
    "priority": 1,
    "class": ["Under 23"],
    "conditions": [{
        "condition_id": "test_u23_c1",
        "description": "Top-3 at any competition",
        "competition": [],
        "date": ["2024-01-01", "2024-12-31"],
        "performance": {"metric": "rank", "operator": "less_or_equal", "value": 3},
        "count_at_least": 1,
    }],
}


def test_criterion_ignores_other_class():
    # a Top-3 result in the Seniors (Elite) category must NOT count for a
    # U23-restricted criterion
    results = make_results([
        {"Comp.SetDetail": "Test Cup", "Date": "2024-05-01", "Class": "Seniors",
         "Rank_num": 2, "Rank_Status": None, "Result_num": None, "Result_Status": None},
    ])
    res = evaluate_criterion(results, U23_CRITERION)
    assert res["status"] == "not_met"


def test_criterion_counts_matching_class():
    # the same Top-3 result, but in the Under 23 category -> counts
    results = make_results([
        {"Comp.SetDetail": "Test Cup", "Date": "2024-05-01", "Class": "Under 23",
         "Rank_num": 2, "Rank_Status": None, "Result_num": None, "Result_Status": None},
    ])
    res = evaluate_criterion(results, U23_CRITERION)
    assert res["status"] == "met"