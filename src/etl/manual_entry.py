from pathlib import Path
import pandas as pd

from src.etl.load import load_yaml_rules

# the raw Podium column layout that clean_data expects. A manual entry is
# written in exactly this shape and then flows through the same pipeline as a
# Podium export, so cleaning and validation are identical for every source.
RAW_COLUMNS = [
    "Date", "Year", "Comp.SetDetail", "Sport", "Discipline", "Gender", "Class",
    "Rank", "Sec/Mtr/Pts", "Team Members", "Person/Team", "Nationality", "DoB",
    "Is Olympic Discipline",
]

# the four non-standard result codes the cleaning step recognises.
RESULT_STATUS_CODES = ["DNF", "DNQ", "DNS", "DSQ"]


# map a readable sport name to its rule file.
def sport_rule_paths(rules_dir):
    paths = {}
    for path in sorted(Path(rules_dir).glob("*_v2.yaml")):
        rules = load_yaml_rules(str(path))
        paths[rules["rule_tree"]["sport"]] = str(path)
    return paths


# collect the option vocabulary for a sport straight from its rule file, so the
# form offers values the engine can actually match. Competitions especially are
# taken from the rules, not from the data, so a manual entry cannot introduce a
# competition-name mismatch.
def sport_rule_options(rules_path):
    rule_tree = load_yaml_rules(rules_path)["rule_tree"]
    competitions, disciplines, genders, metrics = set(), set(), set(), set()
    has_age_criterion = False
    for criterion in rule_tree["criteria"]:
        disciplines.update(criterion.get("discipline") or [])
        genders.update(criterion.get("gender") or [])
        for condition in criterion["conditions"]:
            competitions.update(condition.get("competition") or [])
            performance = condition.get("performance")
            if performance:
                metrics.add(performance["metric"])
            if condition.get("age"):
                has_age_criterion = True
    return {
        "competitions": sorted(competitions),
        "disciplines": sorted(disciplines),
        "genders": sorted(genders),
        "metrics": sorted(metrics),
        "has_age_criterion": has_age_criterion,
    }


# build one raw-layout row from the form inputs. Rank carries either a
# placement number or a status code (DNF/DNQ/DNS/DSQ); the cleaning step turns
# it into Rank_num/Rank_Status. is_olympic is "Yes"/"No"/"" so that clean_olympic
# maps an unknown value to None rather than guessing.
def build_manual_row(athlete, sport, discipline, gender, klass, competition,
                     date, dob=None, nationality="SUI",
                     rank=None, rank_status=None, result=None, is_olympic=""):
    dob_display = ""
    if dob:
        dob_display = pd.to_datetime(dob).strftime("%d %b %Y")

    # the parenthesised "(NOC, DoB)" suffix is what marks this as an individual
    # entry for the engine (see engine.is_individual_entry). The comma is required.
    person_team = f"{athlete} ({nationality}, {dob_display})"

    if rank_status:
        rank_cell = rank_status
    elif rank not in (None, ""):
        rank_cell = int(rank)
    else:
        rank_cell = None

    row = {
        "Date": date,
        "Year": pd.to_datetime(date).year if date else None,
        "Comp.SetDetail": competition,
        "Sport": sport,
        "Discipline": discipline,
        "Gender": gender,
        "Class": klass,
        "Rank": rank_cell,
        "Sec/Mtr/Pts": result if result not in (None, "") else None,
        "Team Members": "No",
        "Person/Team": person_team,
        "Nationality": nationality,
        "DoB": dob if dob else None,
        "Is Olympic Discipline": is_olympic,
    }
    return pd.DataFrame([row], columns=RAW_COLUMNS)


# append a raw manual row to the persistent manual-entries file, writing the
# header only when the file is first created. Semicolon-separated so that the
# commas inside athlete names do not need sniffing on read.
def append_manual_entry(row_df, manual_path):
    manual_path = Path(manual_path)
    manual_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = not manual_path.exists()
    row_df.to_csv(manual_path, sep=";", index=False, mode="a", header=write_header)
    return str(manual_path)