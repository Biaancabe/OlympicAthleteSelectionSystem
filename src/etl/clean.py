import math
from datetime import datetime
import pandas as pd

# clean a single rank value into (rank_num, rank_status)
def clean_rank(value):
    # the four non-standard result codes we want to preserve as status
    status_codes = ['DNS', 'DNF', 'DNQ', 'DSQ']

    # 1) real missing value (None or NaN) -> both None
    if value is None:
        return None, None
    if isinstance(value, float) and math.isnan(value):
        return None, None

    # 2) non-standard result code (case-insensitive) -> status kept, num is None
    if str(value).strip().upper() in status_codes:
        return None, str(value).strip().upper()

    # 3) a real placement -> numeric rank, no special status
    try:
        return int(value), None
    except (ValueError, TypeError):
        # anything we can't interpret -> treat as missing, don't guess
        return None, None


# clean a single result value into (result_num, result_status)
def clean_result(value):
    status_codes = ['DNS', 'DNF', 'DNQ', 'DSQ']

    # 1) real missing value -> both None
    if value is None:
        return None, None
    if isinstance(value, float) and math.isnan(value):
        return None, None

    # 2) non-standard result code -> status kept, num is None
    if str(value).strip().upper() in status_codes:
        return None, str(value).strip().upper()

    # 3) a real performance value -> numeric result, no special status
    try:
        cleaned = str(value).replace("'", "")   # remove Swiss thousands separator
        return float(cleaned), None
    except (ValueError, TypeError):
        return None, None


# clean a single date value (competition date or DoB) into ISO format (YYYY-MM-DD)
def clean_date(value):
    # missing values -> None
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None

    text = str(value).strip()

    # try the known input formats one after another
    for fmt in ("%d-%b-%Y", "%d.%m.%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(text, fmt).strftime("%Y-%m-%d")
        except ValueError:
            continue

    # no known format matched -> keep original value visible (don't hide it)
    return text


# clean the 'Is Olympic Discipline' value into True / False / None
def clean_olympic(value):
    # missing values -> None (unknown, not automatically "not olympic")
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None

    text = str(value).strip().lower()

    if text == "yes":
        return True
    if text == "no":
        return False

    # anything unexpected -> None, don't guess
    return None


def clean_data(data, schema):
    # 1) keep only columns defined in the schema
    valid_columns = [prop for prop in schema['properties'].keys() if prop in data.columns]
    cleaned = data[valid_columns].copy()

    # 2) remove per-member team rows, keep the team-level row
    rows_before = len(cleaned)
    cleaned = cleaned[cleaned["Team Members"] != "Yes"]
    rows_after = len(cleaned)
    removed = rows_before - rows_after
    print(f"clean_data: removed {removed} team-member rows "
          f"({rows_before} -> {rows_after})")
    cleaned = cleaned.drop(columns=["Team Members"])

    # 3) rank -> Rank_num + Rank_Status
    cleaned[["Rank_num", "Rank_Status"]] = cleaned["Rank"].apply(clean_rank).apply(pd.Series)

    # 4) result -> Result_num + Result_Status
    cleaned[["Result_num", "Result_Status"]] = cleaned["Sec/Mtr/Pts"].apply(clean_result).apply(pd.Series)

    # 5) DoB -> ISO date
    cleaned["DoB"] = cleaned["DoB"].apply(clean_date)

    # 6) competition date -> ISO date
    cleaned["Date"] = cleaned["Date"].apply(clean_date)

    # 7) Is Olympic Discipline -> True / False / None
    cleaned["Is Olympic Discipline"] = cleaned["Is Olympic Discipline"].apply(clean_olympic)

    return cleaned