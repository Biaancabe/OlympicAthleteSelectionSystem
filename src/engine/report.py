import pandas as pd


# map an athlete's overall category to the criterion status that produces it,
# so the decisive route can be identified for traceability.
_CATEGORY_DRIVER = {
    "fully_qualified": "met",
    "nearly_qualified": "nearly_met",
    "manual_review_required": "manual_review",
}

# a stable, meaningful order for the output: qualified first, then nearly
# qualified, then the cases needing a human, then not qualified.
_CATEGORY_ORDER = {
    "fully_qualified": 0,
    "nearly_qualified": 1,
    "manual_review_required": 2,
    "not_qualified": 3,
}


# find the criterion (route) that produced the athlete's category, so the
# output can point back to it. For "not_qualified" there is no single decisive
# route, so None is returned.
def _decisive_criterion(athlete_result):
    driver = _CATEGORY_DRIVER.get(athlete_result["category"])
    if driver is None:
        return None
    for crit in athlete_result["criteria"]:
        if crit["status"] == driver:
            return crit
    return None


# turn the engine's nested result into a flat selection list: one row per
# athlete, with the category and a link back to the decisive route.
def build_selection_list(engine_output):
    sport = engine_output["sport"]
    rows = []
    for athlete_result in engine_output["results"]:
        crit = _decisive_criterion(athlete_result)
        rows.append({
            "sport": sport,
            "athlete": athlete_result["athlete"],
            "category": athlete_result["category"],
            "decisive_route": crit["criterion_id"] if crit else None,
            "route_description": crit["description"] if crit else None,
        })

    columns = ["sport", "athlete", "category", "decisive_route", "route_description"]
    df = pd.DataFrame(rows, columns=columns)

    df["_order"] = df["category"].map(_CATEGORY_ORDER).fillna(99)
    df = df.sort_values(["_order", "athlete"]).drop(columns="_order").reset_index(drop=True)
    return df


# write the selection list to a semicolon-separated CSV, consistent with the
# pipeline output.
def export_selection_list(df, path):
    df.to_csv(path, sep=";", index=False)
    return path