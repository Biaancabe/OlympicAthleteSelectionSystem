import pandas as pd
from src.etl.load import load_data
from src.etl.pipeline import run_pipeline_on_frame
from src.engine.engine import run_engine
from src.engine.report import build_selection_list

DATA_SCHEMA = "schemas/dataschema.json"
RULE_SCHEMA = "schemas/ruleschema.json"

# 1) load the real export as raw, tagged podium_csv
export = load_data("data/data_2026-01-07.csv", source="podium_csv")

# 2) a synthetic MANUAL raw row, same raw layout, tagged manual_form
manual = pd.DataFrame([{
    "Date": "2026-01-10", "Year": 2026, "Comp.SetDetail": "Audi FIS Ski World Cup",
    "Sport": "Alpine Skiing", "Discipline": "Downhill", "Gender": "Male", "Class": "Seniors",
    "Rank": 3, "Sec/Mtr/Pts": None, "Team Members": "No",
    "Person/Team": "Testesserin Manual (SUI, 01 Jan 2000)", "Nationality": "SUI",
    "DoB": "2000-01-01", "Is Olympic Discipline": "Yes",
}])
manual["source"] = "manual_form"

# 3) additive union, then ONE cleaning/validation pass over both
raw_all = pd.concat([export, manual], ignore_index=True)
cleaned, report = run_pipeline_on_frame(raw_all, DATA_SCHEMA)
print("--- validation:", report["valid"], "valid /", report["rejected"], "rejected ---")

# 4) engine for Alpine, then look for the manual athlete
out = run_engine(cleaned, "rules/Alpine_Skiing_qualification_rules_v2.yaml", RULE_SCHEMA)
sel = build_selection_list(out)
row = sel[sel["athlete"].str.contains("Testesserin Manual")]
print("--- manual athlete present:", not row.empty, "---")
print(row.to_string(index=False))