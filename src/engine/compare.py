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


# check whether a value is a "near hit": not a full hit, but within the
# percentage tolerance of the threshold. Direction depends on the operator.
def is_near(value, operator, comp_value=None, comp_min=None, comp_max=None, tolerance=0.2):
    # no value -> cannot be near
    if value is None:
        return False

    # a full hit is not a "near" hit (near means: just missed)
    if satisfies(value, operator, comp_value, comp_min, comp_max):
        return False

    # rank-style: smaller is better -> near zone is just ABOVE the threshold
    if operator in ("less_or_equal", "between"):
        threshold = comp_value if operator == "less_or_equal" else comp_max
        upper_bound = threshold * (1 + tolerance)
        return threshold < value <= upper_bound

    # value-style: larger is better -> near zone is just BELOW the threshold
    elif operator == "greater_or_equal":
        lower_bound = comp_value * (1 - tolerance)
        return lower_bound <= value < comp_value

    # "equal" has no meaningful tolerance zone
    else:
        return False