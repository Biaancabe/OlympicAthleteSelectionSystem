import pandas as pd
from src.engine.report import build_selection_list, export_selection_list


# helper: build a minimal engine output with one athlete of a given category.
# The decisive route must carry the status that drives that category.
def _engine_output(category, driver_status):
    return {
        "sport": "Skeleton",
        "n_athletes": 1,
        "results": [{
            "athlete": "Test Athlete",
            "category": category,
            "criteria": [
                {"criterion_id": "r1", "description": "a route",
                 "priority": 1, "status": driver_status, "conditions": []},
            ],
        }],
    }


# test: a fully qualified athlete is linked to the met route
def test_fully_qualified_points_to_met_route():
    df = build_selection_list(_engine_output("fully_qualified", "met"))
    assert len(df) == 1
    assert df.loc[0, "category"] == "fully_qualified"
    assert df.loc[0, "decisive_route"] == "r1"


# test: a nearly qualified athlete is linked to the nearly-met route
def test_nearly_qualified_points_to_nearly_met_route():
    df = build_selection_list(_engine_output("nearly_qualified", "nearly_met"))
    assert df.loc[0, "decisive_route"] == "r1"


# test: a manual-review athlete is linked to the route that needs review
def test_manual_review_points_to_review_route():
    df = build_selection_list(_engine_output("manual_review_required", "manual_review"))
    assert df.loc[0, "decisive_route"] == "r1"


# test: a not-qualified athlete has no decisive route
def test_not_qualified_has_no_route():
    df = build_selection_list(_engine_output("not_qualified", "not_met"))
    assert pd.isna(df.loc[0, "decisive_route"])


# test: the list is ordered qualified -> nearly -> review -> not
def test_selection_list_is_ordered_by_category():
    output = {
        "sport": "Skeleton", "n_athletes": 4,
        "results": [
            {"athlete": "D", "category": "not_qualified", "criteria": []},
            {"athlete": "A", "category": "fully_qualified",
             "criteria": [{"criterion_id": "r1", "description": "x",
                           "priority": 1, "status": "met", "conditions": []}]},
            {"athlete": "C", "category": "manual_review_required",
             "criteria": [{"criterion_id": "r2", "description": "y",
                           "priority": 1, "status": "manual_review", "conditions": []}]},
            {"athlete": "B", "category": "nearly_qualified",
             "criteria": [{"criterion_id": "r3", "description": "z",
                           "priority": 1, "status": "nearly_met", "conditions": []}]},
        ],
    }
    df = build_selection_list(output)
    assert df["category"].tolist() == [
        "fully_qualified", "nearly_qualified",
        "manual_review_required", "not_qualified",
    ]


# test: export writes a semicolon-separated CSV that reads back identically
def test_export_round_trip(tmp_path):
    df = build_selection_list(_engine_output("fully_qualified", "met"))
    path = tmp_path / "selection.csv"
    export_selection_list(df, str(path))
    reloaded = pd.read_csv(path, sep=";")
    assert reloaded.loc[0, "athlete"] == "Test Athlete"
    assert reloaded.loc[0, "decisive_route"] == "r1"