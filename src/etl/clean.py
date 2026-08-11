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

    # 3) normalize separators (thousands, comma decimal)
    cleaned = str(value).strip()
    cleaned = cleaned.replace(" ", "").replace("'", "")  # drop thousands separators (space, apostrophe)
    cleaned = cleaned.replace(",", ".")  # comma decimal -> dot

    # 3a) clock-style times "m:ss.x" or "h:mm:ss.x" -> total seconds.
    #     e.g. "6:50.3" -> 410.3, "2:08:10" -> 7690.0. A time is only a valid
    #     result here if every part parses and the seconds/minutes parts are
    #     within 0-59; otherwise fall through to the plain-number path.
    if ":" in cleaned:
        parts = cleaned.split(":")
        try:
            nums = [float(p) for p in parts]
        except (ValueError, TypeError):
            return None, None
        # all parts except the last (seconds) must be whole and < 60;
        # minutes/hours are integers, only the last part carries decimals
        if len(parts) in (2, 3) and all(n >= 0 for n in nums):
            total = 0.0
            for n in nums:
                total = total * 60 + n
            return total, None
        return None, None

    # 3b) a plain numeric performance value
    try:
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
    # 1) work on a copy; keep all raw columns for now (needed during cleaning)
    cleaned = data.copy()

    # 2) remove per-member team rows, keep the team-level row
    rows_before = len(cleaned)
    cleaned = cleaned[cleaned["Team Members"] != "Yes"]
    rows_after = len(cleaned)
    removed = rows_before - rows_after
    print(f"clean_data: removed {removed} team-member rows "
          f"({rows_before} -> {rows_after})")
    cleaned = cleaned.drop(columns=["Team Members"])
    # collect cleaning info to pass back to the pipeline / report
    clean_log = {
        "rows_before": rows_before,
        "rows_after": rows_after,
        "team_member_rows_removed": removed,
    }

    # 3) rank -> Rank_num + Rank_Status
    cleaned[["Rank_num", "Rank_Status"]] = cleaned["Rank"].apply(clean_rank).apply(pd.Series)

    # 4) result -> Result_num + Result_Status
    cleaned[["Result_num", "Result_Status"]] = cleaned["Result"].apply(clean_result).apply(pd.Series)

    # 5) DoB -> ISO date
    cleaned["DoB"] = cleaned["DoB"].apply(clean_date)

    # 6) competition date -> ISO date
    cleaned["Date"] = cleaned["Date"].apply(clean_date)

    # 7) Is Olympic Discipline -> True / False / None
    cleaned["Is Olympic Discipline"] = cleaned["Is Olympic Discipline"].apply(clean_olympic)

    # keep only columns defined in the schema (drops raw Rank, Sec/Mtr/Pts, etc.)
    valid_columns = [prop for prop in schema['properties'].keys() if prop in cleaned.columns]
    cleaned = cleaned[valid_columns].copy()

    return cleaned, clean_log

# split a cleaned dataset into eligible rows and excluded (known non-SUI) rows.
# Only a KNOWN nationality other than the home NOC is a reason to exclude. A
# missing nationality (team/relay entries, or an individual whose value happens
# to be empty in the source) is NOT positive evidence of ineligibility, so those
# rows are kept (constitution Principle 3: no silent, data-driven exclusion).
def exclude_non_sui(data, home="SUI"):
    non_home_mask = data["Nationality"].notna() & (data["Nationality"] != home)
    kept = data[~non_home_mask].copy()
    excluded = data[non_home_mask].copy()
    return kept, excluded