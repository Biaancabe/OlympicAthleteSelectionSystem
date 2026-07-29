import pandas as pd
from src.engine.compare import satisfies, satisfies_date


# map a metric name to the cleaned data column it refers to
def metric_column(metric):
    if metric == "rank":
        return "Rank_num"
    elif metric in ("points", "time"):
        return "Result_num"
    else:
        raise ValueError(f"Unknown metric: {metric}")


# evaluate a single condition for one athlete's results
def evaluate_condition(athlete_results, condition, dob=None, aliases=None):
    # 0) age gate (athlete-level eligibility, checked before looking at results).
    #    A birth-date cutoff is a hard eligibility bound, not a performance
    #    threshold -> no tolerance. Checked once; a failed gate makes the whole
    #    condition unsatisfiable regardless of results.
    age = condition.get("age")
    if age is not None:
        age_ok = satisfies_date(dob, age["operator"], age["value"])
        if age_ok is None:
            return {
                "condition_id": condition["condition_id"],
                "status": "manual_review",
                "full_hits": [],
                "review_flags": [{"reason": "missing date of birth for age criterion"}],
            }
        if not age_ok:
            return {
                "condition_id": condition["condition_id"],
                "status": "not_met",
                "full_hits": [],
                "review_flags": [],
            }

    # 1) filter to the condition's competitions and date range
    comps = condition["competition"]
    start, end = condition["date"]
    comps_lower = [c.lower() for c in comps]
    # extend the accepted names with any data-side aliases for these rule
    # names, so a differently spelled name for the SAME competition still
    # matches. The comparison itself stays exact (see competition_aliases.yaml).
    accepted = set(comps_lower)
    if aliases:
        for name in comps_lower:
            accepted.update(aliases.get(name, []))
    mask = (
            athlete_results["Comp.SetDetail"].str.lower().isin(accepted)
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
    review_flags = []

    for _, row in relevant.iterrows():
        value = row[column]
        status = row[status_column]

        # a status code (DNF/DNQ/DNS/DSQ) is a KNOWN non-result: the athlete
        # did not achieve a placement here -> simply not a hit, no manual review.
        if status is not None and pd.notna(status):
            continue

        # no value AND no status code -> genuinely unknown -> manual review
        if value is None or pd.isna(value):
            review_flags.append({"date": row["Date"], "reason": "missing value"})
            continue

        if satisfies(value, operator, perf.get("value"), perf.get("min"), perf.get("max")):
            full_hits.append({"date": row["Date"], "value": value})

    # 4) condition has three states only: met / not_met / manual_review.
    #    nearly_met is decided at criterion level (see evaluate_criterion).
    needed = condition["count_at_least"]
    status = decide_condition_status(len(full_hits), len(review_flags), needed)

    return {
        "condition_id": condition["condition_id"],
        "status": status,
        "full_hits": full_hits,
        "review_flags": review_flags,
    }


# decide the status of a single condition from the counts.
# A condition has only three states: met, not_met, or manual_review.
# nearly_met is decided at criterion level (see evaluate_criterion).
def decide_condition_status(n_full, n_review, needed):
    if n_full >= needed:
        return "met"
    if n_full + n_review >= needed:
        return "manual_review"
    return "not_met"


# evaluate one criterion (a route) for an athlete.
# A criterion has several conditions joined by AND (all must hold).
def evaluate_criterion(athlete_results, criterion, dob=None, aliases=None):
    # a criterion may be restricted to certain disciplines -> filter first
    disciplines = criterion.get("discipline")
    if disciplines:
        disciplines_lower = [d.lower() for d in disciplines]
        relevant_results = athlete_results[
            athlete_results["Discipline"].str.lower().isin(disciplines_lower)
        ]
    else:
        relevant_results = athlete_results

    condition_results = [
        evaluate_condition(relevant_results, cond, dob, aliases)
        for cond in criterion["conditions"]
    ]

    # Decide the criterion status (L. Castella, personal communication, July 2026):
    # - age conditions are mandatory: not_met age -> criterion not_met.
    # - nearly_met: all age conditions met, exactly one performance condition
    #   not_met, all others met. Only possible with 2+ performance conditions.
    # - a criterion with a single performance condition is met or not_met only.
    def _is_pure_age_cond(cond_result):
        cdef = next((c for c in criterion["conditions"]
                     if c["condition_id"] == cond_result["condition_id"]), {})
        return bool(cdef.get("age")) and not bool(cdef.get("performance"))

    age_statuses = [c["status"] for c in condition_results if _is_pure_age_cond(c)]
    perf_statuses = [c["status"] for c in condition_results if not _is_pure_age_cond(c)]

    if "not_met" in age_statuses:
        status = "not_met"
    elif "manual_review" in age_statuses or "manual_review" in perf_statuses:
        status = "manual_review"
    elif all(s == "met" for s in perf_statuses):
        status = "met"
    elif (len(perf_statuses) > 1
          and perf_statuses.count("not_met") == 1
          and all(s == "met" for s in perf_statuses if s != "not_met")):
        status = "nearly_met"
    else:
        status = "not_met"

    return {
        "criterion_id": criterion["criterion_id"],
        "description": criterion["description"],
        "priority": criterion["priority"],
        "status": status,
        "conditions": condition_results,
    }


# evaluate an athlete against all criteria (routes) of a sport.
# Routes are joined by OR (any one route qualifies). The best status wins.
def evaluate_athlete(athlete_results, criteria, aliases=None):
    athlete_gender = None
    if "Gender" in athlete_results.columns and len(athlete_results) > 0:
        athlete_gender = athlete_results["Gender"].iloc[0]

    # the birth date is athlete-level (consistent across rows) -> read once
    dob = None
    if "DoB" in athlete_results.columns and len(athlete_results) > 0:
        dob = athlete_results["DoB"].iloc[0]

    applicable = [c for c in criteria if criterion_applies(c, athlete_gender)]

    criterion_results = [
        evaluate_criterion(athlete_results, crit, dob, aliases)
        for crit in applicable
    ]

    statuses = [c["status"] for c in criterion_results]

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
def criterion_applies(criterion, athlete_gender):
    genders = criterion.get("gender")
    if not genders:
        return True
    return athlete_gender in genders