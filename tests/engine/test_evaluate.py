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


def test_condition_nearly_met_one_full_one_near():
    # one full hit (rank 5) + one near hit (rank 9, within 20% of 8) -> nearly met
    results = make_results([
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-01",
         "Rank_num": 5, "Rank_Status": None, "Result_num": None, "Result_Status": None},
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-15",
         "Rank_num": 9, "Rank_Status": None, "Result_num": None, "Result_Status": None},
    ])
    res = evaluate_condition(results, TOP8_WC)
    assert res["status"] == "nearly_met"


def test_condition_manual_review_status_code():
    # one full hit + one DNS: could tip over the threshold if she had finished -> manual review
    results = make_results([
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-01",
         "Rank_num": 5, "Rank_Status": None, "Result_num": None, "Result_Status": None},
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-15",
         "Rank_num": None, "Rank_Status": "DNS", "Result_num": None, "Result_Status": None},
    ])
    res = evaluate_condition(results, TOP8_WC)
    assert res["status"] == "manual_review"


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


def test_criterion_not_met_overrides_manual_review():
    # WM condition clearly not met (rank 20), WC condition manual_review (DNS)
    # -> not_met wins over manual_review (your own rule)
    results = make_results([
        {"Comp.SetDetail": "Test WM", "Date": "2025-02-15",
         "Rank_num": 20, "Rank_Status": None, "Result_num": None, "Result_Status": None},
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-01",
         "Rank_num": None, "Rank_Status": "DNS", "Result_num": None, "Result_Status": None},
    ])
    res = evaluate_criterion(results, TWO_COND_CRITERION)
    assert res["status"] == "not_met"


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
    # route 1 not met (rank 20), route 2 manual_review (DNS at WC)
    # -> no met route, but a data gap could still qualify -> manual review
    results = make_results([
        {"Comp.SetDetail": "Test WM", "Date": "2025-02-15",
         "Rank_num": 20, "Rank_Status": None, "Result_num": None, "Result_Status": None},
        {"Comp.SetDetail": "Test World Cup", "Date": "2025-12-01",
         "Rank_num": None, "Rank_Status": "DNS", "Result_num": None, "Result_Status": None},
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