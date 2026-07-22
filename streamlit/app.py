import sys
from pathlib import Path

# make the project root importable when Streamlit runs from the streamlit/ folder
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import streamlit as st

from src.etl.pipeline import run_pipeline
from src.etl.load import load_yaml_rules
from src.engine.engine import run_engine
from src.engine.report import build_selection_list

DATA_SCHEMA = str(ROOT / "schemas" / "dataschema.json")
RULE_SCHEMA = str(ROOT / "schemas" / "ruleschema.json")
RULES_DIR = ROOT / "rules"
DATA_DIR = ROOT / "data"

st.set_page_config(page_title="Swiss Olympic Selection", layout="wide")


# run the ETL pipeline once per file and cache the standardised data
@st.cache_data(show_spinner=False)
def clean_export(data_path):
    cleaned, report = run_pipeline(data_path, DATA_SCHEMA, output_dir=str(ROOT / "output"))
    return cleaned, report


# map a readable sport name to its rule file, read from the rule files
@st.cache_data(show_spinner=False)
def available_sports():
    sports = {}
    for path in sorted(RULES_DIR.glob("*_v2.yaml")):
        rules = load_yaml_rules(str(path))
        sports[rules["rule_tree"]["sport"]] = str(path)
    return sports


st.title("Swiss Olympic Athlete Selection")
st.caption("Applies the machine-readable selection criteria to the standardised "
           "competition data.")

data_files = sorted(DATA_DIR.glob("*.csv"))
if not data_files:
    st.error("No competition data export found in the data folder.")
    st.stop()

with st.sidebar:
    st.header("Input")
    data_choice = st.selectbox("Competition data export", data_files,
                               format_func=lambda p: p.name)
    sports = available_sports()
    sport_choice = st.selectbox("Sport", sorted(sports.keys()))

# run the pipeline and the engine for the chosen data and sport
cleaned, _ = clean_export(str(data_choice))
engine_output = run_engine(cleaned, sports[sport_choice], RULE_SCHEMA)
selection = build_selection_list(engine_output)

st.subheader(f"{sport_choice}: {len(selection)} athletes evaluated")

counts = selection["category"].value_counts()
c1, c2, c3, c4 = st.columns(4)
c1.metric("Fully qualified", int(counts.get("fully_qualified", 0)))
c2.metric("Nearly qualified", int(counts.get("nearly_qualified", 0)))
c3.metric("Manual review", int(counts.get("manual_review_required", 0)))
c4.metric("Not qualified", int(counts.get("not_qualified", 0)))

categories = ["fully_qualified", "nearly_qualified",
              "manual_review_required", "not_qualified"]
chosen = st.multiselect("Show categories", categories, default=categories)
shown = selection[selection["category"].isin(chosen)]

st.dataframe(shown, use_container_width=True, hide_index=True)

csv = shown.to_csv(sep=";", index=False).encode("utf-8")
st.download_button("Download selection list (CSV)", data=csv,
                   file_name=f"selection_{sport_choice.replace(' ', '_')}.csv",
                   mime="text/csv")