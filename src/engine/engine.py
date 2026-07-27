import json
import pandas as pd
from jsonschema import Draft7Validator

from src.etl.load import load_yaml_rules, load_json_schema
from src.engine.evaluate import evaluate_athlete

import re


# an individual entry carries a "(NOC, date of birth)" suffix in the name,
# e.g. "Marco Odermatt (SUI, 08 Oct 1997)". A team, relay or pair entry does
# not, e.g. "Switzerland", "Sieber / Zehnder" or "Switzerland 1".
def is_individual_entry(name):
    return bool(re.search(r"\([A-Z]{3},", str(name)))


# select the units to evaluate for a sport, based on how the sport treats teams.
# "individual" (default): evaluate individual athletes, exclude team entries.
# "team": evaluate the team entries themselves (genuine team sports). Team mode
# reuses the same evaluation logic; only the set of evaluated units differs.
def select_units(sport_data, team_handling):
    names = sport_data["Person/Team"].dropna().unique()
    if team_handling == "team":
        kept = [n for n in names if not is_individual_entry(n)]
    else:
        kept = [n for n in names if is_individual_entry(n)]
    excluded = [n for n in names if n not in kept]
    return kept, excluded

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
def run_engine(data, rules_path, schema_path):
    # 1) load + validate the rules (fails loudly if invalid)
    rules = load_and_validate_rules(rules_path, schema_path)

    sport = rules["rule_tree"]["sport"]
    criteria = rules["rule_tree"]["criteria"]
    # how this sport treats team/relay entries; default is individual, which
    # is correct for all winter sports in the pilot (L. Castella, personal
    # communication, July 2026).
    team_handling = rules["rule_tree"].get("team_handling", "individual")

    # 2) filter the data to this sport
    # compare the sport name case-insensitively, same reasoning as for
    # competition and discipline names
    sport_data = data[data["Sport"].str.lower() == sport.lower()]

    # 3) select the units to evaluate (individual athletes or team entries)
    units, excluded = select_units(sport_data, team_handling)

    # 4) evaluate each selected unit
    results = []
    for name in units:
        athlete_results = sport_data[sport_data["Person/Team"] == name]
        evaluation = evaluate_athlete(athlete_results, criteria)
        results.append({
            "athlete": name,
            "category": evaluation["category"],
            "criteria": evaluation["criteria"],
        })

    return {
        "sport": sport,
        "team_handling": team_handling,
        "n_athletes": len(results),
        "n_excluded": len(excluded),
        "excluded_entries": list(excluded),
        "results": results,
    }