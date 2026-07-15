import json
import pandas as pd
from jsonschema import Draft7Validator

from src.etl.load import load_yaml_rules, load_json_schema
from src.engine.evaluate import evaluate_athlete

# load a rule file and validate it against the rule schema.
# Fails loudly if the rules are invalid (constitution, Principle 2).
def load_and_validate_rules(rules_path, schema_path):
    rules = load_yaml_rules(rules_path)
    schema = load_json_schema(schema_path)

    # convert date objects to strings for validation (YAML parses dates as date objects)
    rules_for_validation = json.loads(json.dumps(rules, default=str))

    validator = Draft7Validator(schema)
    errors = sorted(validator.iter_errors(rules_for_validation), key=lambda e: str(e.path))

    if errors:
        messages = []
        for err in errors:
            path = ".".join(str(p) for p in err.path) or "root"
            messages.append(f"  - {path}: {err.message}")
        raise ValueError(
            f"Rule file '{rules_path}' failed schema validation:\n"
            + "\n".join(messages)
        )

    return rules


# run the selection engine for one sport's rule file against the data.
def run_engine(data, rules_path, schema_path, tolerance=0.2):
    # 1) load + validate the rules (fails loudly if invalid)
    rules = load_and_validate_rules(rules_path, schema_path)

    sport = rules["rule_tree"]["sport"]
    criteria = rules["rule_tree"]["criteria"]

    # 2) filter the data to this sport
    # compare the sport name case-insensitively, same reasoning as for
    # competition and discipline names
    sport_data = data[data["Sport"].str.lower() == sport.lower()]

    # 3) evaluate each athlete
    results = []
    for name in sport_data["Person/Team"].unique():
        athlete_results = sport_data[sport_data["Person/Team"] == name]
        evaluation = evaluate_athlete(athlete_results, criteria, tolerance)
        results.append({
            "athlete": name,
            "category": evaluation["category"],
            "criteria": evaluation["criteria"],
        })

    return {
        "sport": sport,
        "n_athletes": len(results),
        "results": results,
    }