from datetime import datetime

# check whether a single value satisfies a comparison
def satisfies(value, operator, comp_value=None, comp_min=None, comp_max=None):
    # if there is no value to compare (missing data), it cannot satisfy anything
    if value is None:
        return False

    if operator == "less_or_equal":
        return value <= comp_value
    elif operator == "greater_or_equal":
        return value >= comp_value
    elif operator == "equal":
        return value == comp_value
    elif operator == "between":
        return comp_min <= value <= comp_max
    else:
        # unknown operator -> should never happen if the rule passed schema validation
        raise ValueError(f"Unknown operator: {operator}")


# helper: parse a cleaned ISO date string (YYYY-MM-DD); None if absent/unparseable
def _parse_iso(value):
    if value is None:
        return None
    try:
        return datetime.strptime(str(value), "%Y-%m-%d")
    except (ValueError, TypeError):
        return None


# check whether a birth date satisfies a date-based cutoff (age criterion).
# Returns True or False, or None when the birth date is unknown -> the caller
# decides what "unknown" means (here: manual review). A date cutoff is a hard
# eligibility bound, so there is deliberately no tolerance zone.
def satisfies_date(value_date, operator, comp_date):
    dob = _parse_iso(value_date)
    cutoff = _parse_iso(comp_date)
    if dob is None:
        return None                      # unknown birth date -> not decidable here
    if cutoff is None:
        # a malformed cutoff should already have failed schema validation
        raise ValueError(f"Invalid cutoff date: {comp_date!r}")
    if operator == "on_or_after":
        return dob >= cutoff
    elif operator == "on_or_before":
        return dob <= cutoff
    else:
        raise ValueError(f"Unknown date operator: {operator}")