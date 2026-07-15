import pandas as pd
from src.engine.compare import satisfies, is_near


# map a metric name to the cleaned data column it refers to
def metric_column(metric):
    if metric == "rank":
        return "Rank_num"
    elif metric in ("points", "time"):
        return "Result_num"
    else:
        raise ValueError(f"Unknown metric: {metric}")

# evaluate a single condition for one athlete's results
def evaluate_condition(athlete_results, condition, tolerance=0.2):
    # 1) filter to the condition's competitions and date range
    comps = condition["competition"]
    start, end = condition["date"]
    mask = (
        athlete_results["Comp.SetDetail"].isin(comps)
        & (athlete_results["Date"] >= start)
        & (athlete_results["Date"] <= end)
    )
    relevant = athlete_results[mask]

    # 2) figure out which column and comparison to use
    perf = condition["performance"]
    metric = perf["metric"]
    operator = perf["operator"]
    column = metric_column(metric)
    status_column = "Rank_Status" if metric == "rank" else "Result_Status"

    # 3) classify each relevant result
    full_hits = []
    near_hits = []
    review_flags = []

    for _, row in relevant.iterrows():
        value = row[column]
        status = row[status_column]

        # a status code (DNF/DNQ/DNS/DSQ) means no usable number here
        if status is not None and pd.notna(status):
            review_flags.append({"date": row["Date"], "status": status})
            continue

        if satisfies(value, operator, perf.get("value"), perf.get("min"), perf.get("max")):
            full_hits.append({"date": row["Date"], "value": value})
        elif is_near(value, operator, perf.get("value"), perf.get("min"), perf.get("max"), tolerance):
            near_hits.append({"date": row["Date"], "value": value})

    # 4) decide the status against count_at_least
    needed = condition["count_at_least"]
    status = decide_condition_status(len(full_hits), len(near_hits), len(review_flags), needed)

    return {
        "condition_id": condition["condition_id"],
        "status": status,
        "full_hits": full_hits,
        "near_hits": near_hits,
        "review_flags": review_flags,
    }

# decide the status of a single condition from the counts.
# This is the isolated place to refine later (e.g. after Lionel's age answer).
def decide_condition_status(n_full, n_near, n_review, needed):
    # 1) enough full hits -> met
    if n_full >= needed:
        return "met"

    # 2) missing/ambiguous data (DNF/DNQ/DNS/DSQ) could change the outcome
    #    -> only if the flagged results could tip it over the threshold
    if n_full + n_review >= needed:
        return "manual_review"

    # 3) enough when counting near hits -> nearly met
    if n_near > 0 and n_full + n_near >= needed:
        return "nearly_met"

    # 4) otherwise clearly not met
    return "not_met"

# evaluate one criterion (a route) for an athlete.
# A criterion has several conditions joined by AND (all must hold).
def evaluate_criterion(athlete_results, criterion, tolerance=0.2):
    # a criterion may be restricted to certain disciplines -> filter the data first
    disciplines = criterion.get("discipline")
    if disciplines:
        relevant_results = athlete_results[athlete_results["Discipline"].isin(disciplines)]
    else:
        relevant_results = athlete_results

    # evaluate each condition on the (possibly discipline-filtered) results
    condition_results = [
        evaluate_condition(relevant_results, cond, tolerance)
        for cond in criterion["conditions"]
    ]

    statuses = [c["status"] for c in condition_results]

    # decide the criterion status (AND-logic: the weakest condition drives it)
    if "not_met" in statuses:
        status = "not_met"
    elif "manual_review" in statuses:
        status = "manual_review"
    elif all(s == "met" for s in statuses):
        status = "met"
    else:
        status = "nearly_met"

    return {
        "criterion_id": criterion["criterion_id"],
        "description": criterion["description"],
        "priority": criterion["priority"],
        "status": status,
        "conditions": condition_results,
    }


# evaluate an athlete against all criteria (routes) of a sport.
# Routes are joined by OR (any one route qualifies). The best status wins.
def evaluate_athlete(athlete_results, criteria, tolerance=0.2):
    # determine the athlete's gender from their data (consistent across rows)
    athlete_gender = None
    if "Gender" in athlete_results.columns and len(athlete_results) > 0:
        athlete_gender = athlete_results["Gender"].iloc[0]

    # only evaluate criteria that apply to this athlete
    applicable = [c for c in criteria if criterion_applies(c, athlete_gender)]

    criterion_results = [
        evaluate_criterion(athlete_results, crit, tolerance)
        for crit in applicable
    ]

    statuses = [c["status"] for c in criterion_results]

    # decide the final category (OR-logic: the best route drives it)
    if "met" in statuses:
        category = "fully_qualified"
    elif "nearly_met" in statuses:
        category = "nearly_qualified"
    elif "manual_review" in statuses:
        category = "manual_review_required"
    else:
        category = "not_qualified"

    return {
        "category": category,
        "criteria": criterion_results,
    }


# check whether a criterion applies to an athlete, based on gender.
# A criterion without a "gender" field applies to everyone.
def criterion_applies(criterion, athlete_gender):
    genders = criterion.get("gender")
    if not genders:
        # no gender restriction -> applies to everyone
        return True
    return athlete_gender in genders