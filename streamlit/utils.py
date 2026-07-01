
import math
import streamlit as st
import pandas as pd
import json
import yaml
import jsonschema
from jsonschema import validate
from jsonschema import Draft7Validator, ValidationError
from datetime import date, datetime
from typing import Dict, List, Union, Any, Tuple

# Folders
DATA_FOLDER_NAME = 'data'
RULE_FOLDER_NAME = 'rules'
SCHEMA_FOLDER_NAME = 'schemas'
# Files
DATA_FILE_NAME = 'results_22012026.csv'
DATA_SCHEMA_FILE_NAME = 'dataschema.json'
RULE_SCHEMA_FILE_NAME = 'ruleschema.json'
RULE_MAP_FILE_NAME = 'rules.json'
# Paths
DATA_PATH = f'{DATA_FOLDER_NAME}/{DATA_FILE_NAME}'
DATA_SCHEMA_PATH = f'{SCHEMA_FOLDER_NAME}/{DATA_SCHEMA_FILE_NAME}'
RULE_SCHEMA_PATH = f'{SCHEMA_FOLDER_NAME}/{RULE_SCHEMA_FILE_NAME}'
RULE_MAP_PATH = f'{RULE_FOLDER_NAME}/{RULE_MAP_FILE_NAME}'

# Utility functions

# read full data and cache it
@st.cache_data
def load_data(DATA_PATH=DATA_PATH):
    return pd.read_csv(DATA_PATH, sep=';')

# Function to read JSON schema
def load_json_schema(schema_path):
    with open(schema_path, 'r') as f:
        return json.load(f)

# Function to read YAML rules
def load_yaml_rules(rules_path):
    with open(rules_path, 'r') as f:
        return yaml.safe_load(f)

# get unique sports from data
def get_sports(data: pd.DataFrame = None):
    return sorted(data["Sport"].dropna().unique())

# get disciplines for a sport
def get_disciplines(data: pd.DataFrame = None):
    return sorted(data["Discipline"].dropna().unique()) 

# get genders for a discipline
def get_genders(data: pd.DataFrame = None):
    return sorted(data["Gender"].dropna().unique()) 

# show me the number of records for each athlete
def get_athlete_record_counts(data: pd.DataFrame):
    record_counts = data['Person/Team'].value_counts().reset_index()
    record_counts.columns = ['Athlete', 'Record Count']
    #st.dataframe(record_counts)
    return record_counts

# A function that takes data and the schema and removes all invalid columns in the data frame based on the schema
def clean_data(data, schema):
    valid_columns = [prop for prop in schema['properties'].keys() if prop in data.columns]
    # remove all rows with Team Members == Yes
    cleaned_data = data[valid_columns].copy()
    cleaned_data = cleaned_data[cleaned_data["Team Members"] != "Yes"]
    # remove column "Team Members"
    cleaned_data = cleaned_data.drop(columns=["Team Members"])
    # in rank column, convert all values to integers, DNS, DNF, DSQ to be converted to 997, 998, 999 respectively
    def convert_rank(value):
        if value in ['DNS', 'dns']:
            return 996
        elif value in ['DNF', 'dnf']:
            return 997
        elif value in ['DSQ', 'dsq']:
            return 998
        elif value is None:
            return 999
        # Handle actual NaN from pandas
        if isinstance(value, float) and math.isnan(value):
            return 999
        try:
            return int(value)
        except:
            return 999

    cleaned_data['Rank'] = cleaned_data['Rank'].apply(convert_rank)

    def clean_dob(value):
    # Handle NaN
        if isinstance(value, float) and math.isnan(value):
            return None
        # Keep None as None
        if value is None:
            return None
        # Convert any valid string date to string
        return str(value)
    
    cleaned_data["DoB"] = cleaned_data["DoB"].apply(clean_dob)

    def clean_olympic(value):
    # If pandas NaN, convert to None
        if isinstance(value, float) and math.isnan(value):
            return None
        # Keep None as None
        if value is None:
            return None
        # Convert valid string to string
        return str(value)
    
    cleaned_data["Is Olympic Discipline"] = cleaned_data["Is Olympic Discipline"].apply(clean_olympic)

    # Convert Date column to ISO format
    cleaned_data['Date'] = pd.to_datetime(cleaned_data['Date'], format='%d.%m.%Y').dt.strftime('%Y-%m-%d')
    
    return cleaned_data


# normalize rules dict
def normalize_rules(obj):
    """
    Recursively normalize a dict representing rules:
    1. Convert empty strings or None-like values to Python None.
    2. Convert 'created at' and 'updated at' dates to ISO strings.
    3. Convert 'version' to string.
    """
    if isinstance(obj, dict):
        new_obj = {}
        for k, v in obj.items():
            # Step 1: Normalize recursively
            v = normalize_rules(v)

            # Step 2: Handle dates
            if k in ("created at", "updated at") and isinstance(v, (date, datetime)):
                new_obj[k] = v.isoformat()
            # Step 3: Handle version field
            elif k == "version" and isinstance(v, (float, int)):
                new_obj[k] = str(v)
            # Step 4: Convert empty string or None to Python None
            elif v == "" or v is None:
                new_obj[k] = None
            else:
                new_obj[k] = v
        return new_obj
    elif isinstance(obj, list):
        return [normalize_rules(v) for v in obj]
    elif obj == "" or obj is None:
        return None
    else:
        return obj

def filter_rules(rules: dict, genders: List[str], disciplines: List[str]) -> dict:
    """
    Filters criteria in the rules dictionary based on genders and disciplines.
    
    Keeps a criterion if:
    - It has no 'gender' field OR any of its genders overlap with selected genders
    - It has no 'discipline' field OR any of its disciplines overlap with selected disciplines
    - Both conditions must be true to keep the criterion
    
    Args:
        rules: The full rules dictionary loaded from YAML
        genders: List of selected genders (e.g., ["Men", "Women"])
        disciplines: List of selected disciplines (e.g., ["Big Air", "Halfpipe"])
    
    Returns:
        A new rules dictionary with filtered criteria
    """
    
    if "rule_tree" not in rules or "criteria" not in rules["rule_tree"]:
        return rules
    
    filtered_criteria = []
    
    for criterion in rules["rule_tree"]["criteria"]:
        criterion_genders = criterion.get("gender", None)
        criterion_disciplines = criterion.get("discipline", None)
        
        # Check gender match: None means applies to all, or check for overlap
        if criterion_genders is None:
            gender_match = True
        else:
            gender_match = any(g in criterion_genders for g in genders)
        
        # Check discipline match: None means applies to all, or check for overlap
        if criterion_disciplines is None:
            discipline_match = True
        else:
            discipline_match = any(d in criterion_disciplines for d in disciplines)
        
        # Keep if both conditions are met
        if gender_match and discipline_match:
            filtered_criteria.append(criterion)
    
    # Create a new rules dictionary with filtered criteria
    filtered_rules = rules.copy()
    filtered_rules["rule_tree"] = rules["rule_tree"].copy()
    filtered_rules["rule_tree"]["criteria"] = filtered_criteria
    
    return filtered_rules

def count_criteria(rules: dict) -> int:
    """
    Counts the number of criteria in a rules dictionary.
    
    Args:
        rules: The rules dictionary loaded from YAML
    
    Returns:
        The number of criteria in the rule_tree
    """
    if "rule_tree" not in rules or "criteria" not in rules["rule_tree"]:
        return 0
    
    return len(rules["rule_tree"]["criteria"])

# validate data against schema    
def validate_rules(data: dict, schema: dict) -> bool:
    """
    Validate a Python dict against a JSON Schema.
    Prints all validation errors if they exist.
    Returns True if validation passed, False otherwise.
    """
    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(data), key=lambda e: e.path)

    if not errors:
        print("✅ Validation passed!")
        return True

    print("❌ Validation failed with the following errors:\n")
    for err in errors:
        path = ".".join([str(p) for p in err.path])
        print(f"- Path: {path or 'root'}")
        print(f"  Message: {err.message}\n")
    return False

# A function that validates data against a schema
def validate_data(data, schema):
    data = data.to_dict(orient='records')
    try:
        validate(instance=data, schema=schema)
        print("Data is valid.")
        return True
    except jsonschema.exceptions.ValidationError as err:
        print("Data is invalid:", err)
        return False

@st.cache_data
def load_sport_rule_map():
    with open(RULE_MAP_PATH, "r") as f:
        return json.load(f)

def parse_date(d: str) -> date:
    return date.fromisoformat(d)

def filter_by_date(
    df: pd.DataFrame,
    date_rule: Union[int, List[str]]
) -> pd.DataFrame:
    """
    Filters dataframe by either a single year or a date range.
    """
    if isinstance(date_rule, int):
        return df[df["Year"] == date_rule]

    start_date, end_date = pd.to_datetime(date_rule)
    dates = pd.to_datetime(df["Date"])
    return df[(dates >= start_date) & (dates <= end_date)]

def condition_is_met(
    condition: Dict[str, Any],
    results: List[Dict[str, Any]],
) -> Tuple[int, List[Dict[str, Any]]]:
    """
    Evaluate a single condition against competition results.

    Returns:
        score (int): 0 or negative
        evidence (list): matching competition entries
    """

    start_date, end_date = map(parse_date, condition["date"])
    competitions = set(condition["competition"])
    performance_range = condition["performance"]
    min_rank = min(performance_range)
    max_rank = max(performance_range) if len(performance_range) > 1 else min_rank
    required_count = condition["count_at_least"]

    evidence = []

    for r in results:
        if r["Rank"] is None:
            continue
        
        if r["Date"] is None:
            continue
        
        r_date = parse_date(r["Date"])

        if not (start_date <= r_date <= end_date):
            continue

        if r["Comp.SetDetail"] not in competitions:
            continue

        rank = int(r["Rank"])
        if not (min_rank <= rank <= max_rank):
            continue

        evidence.append(
            {
                "competition": r["Comp.SetDetail"],
                "date": r["Date"],
                "result": rank,
            }
        )

    count = len(evidence)

    # ---- scoring logic ----
    if count >= required_count:
        score = 0
    elif count > 0:
        score = -1
    else:
        score = -required_count

    return score, evidence




def criteria_is_met(
    criteria: Dict[str, Any],
    results: List[Dict[str, Any]],
) -> Dict[str, Any]:
    """
    Evaluate a criteria by summing its condition scores.
    """

    condition_evaluations = []
    total_score = 0

    for condition in criteria["conditions"]:
        score, evidence = condition_is_met(condition, results)
        total_score += score

        condition_evaluations.append(
            {
                "condition": condition["description"],
                "result": score,
                "evidence": evidence,
            }
        )

    return {
        "criteria": criteria["description"],
        "priority": criteria["priority"],
        "result": total_score,
        "conditions": condition_evaluations,
    }


def evaluate_athlete(
    athlete: str,
    results: List[Dict[str, Any]],
    rule_set: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Evaluate all criteria for a single athlete.
    """

    criteria_results = []
    passed_count = 0
    total_evidences = 0

    criterias = rule_set["rule_tree"]["criteria"]

    for criteria in sorted(criterias, key=lambda c: c["priority"]):
        evaluation = criteria_is_met(criteria, results)
        criteria_results.append(evaluation)

        if evaluation["result"] == 0:
            passed_count += 1
        
        # Count evidences across all conditions in this criteria
        for condition in evaluation["conditions"]:
            total_evidences += len(condition["evidence"])

    valid_dates = [r["Date"] for r in results if r["Date"] is not None]
    latest_date = max(valid_dates) if valid_dates else None

    return {
        "athlete": athlete,
        "date": latest_date,
        "version_criteria_set": rule_set["version"],
        "N_criteria_passed": passed_count,
        "N_evidences_found": total_evidences,
        "evaluation": criteria_results,
    }

def evaluate_athletes(
    athletes: List[str],
    df: pd.DataFrame,
    rule_set: Dict[str, Any],
    verbose: bool = False
) -> List[Dict[str, Any]]:
    """
    Evaluate each athlete and return a list of qualification matrices.
    Filters results to the athlete's rows before evaluation.
    """
    all_results = df.to_dict(orient='records')
    matrices: List[Dict[str, Any]] = []

    for athlete in athletes:
        if verbose:
            print(f"Evaluating: {athlete}")
        athlete_results = [r for r in all_results if r.get("Person/Team") == athlete]
        qm = evaluate_athlete(athlete=athlete, results=athlete_results, rule_set=rule_set)
        matrices.append(qm)

    matrices.sort(key=lambda x: x["N_criteria_passed"], reverse=True)
    return matrices