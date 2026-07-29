import sys
import json
from pathlib import Path

# make the project root importable when Streamlit runs from the streamlit/ folder
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import pandas as pd
import streamlit as st

from src.etl.load import load_data
from src.etl.pipeline import run_pipeline_on_frame
from src.engine.engine import run_engine
from src.engine.report import build_selection_list
from src.etl.manual_entry import (
    sport_rule_paths, sport_rule_options,
    build_manual_row, append_manual_entry, RESULT_STATUS_CODES,
)

DATA_SCHEMA = str(ROOT / "schemas" / "dataschema.json")
RULE_SCHEMA = str(ROOT / "schemas" / "ruleschema.json")
RULES_DIR = ROOT / "rules"
DATA_DIR = ROOT / "data"
MANUAL_PATH = DATA_DIR / "manual_entries.csv"

st.set_page_config(page_title="Swiss Olympic Selection", layout="wide")


# the Class values allowed by the data schema, so the form offers exactly those.
@st.cache_data(show_spinner=False)
def class_options():
    schema = json.loads(Path(DATA_SCHEMA).read_text())
    return schema["items"]["properties"]["Class"]["enum"]


# map a readable sport name to its rule file.
@st.cache_data(show_spinner=False)
def available_sports():
    return sport_rule_paths(str(RULES_DIR))


# load the chosen export together with the persistent manual entries, then run
# one cleaning/validation pass over the union. manual_mtime is part of the key
# so the cache refreshes as soon as a new manual entry is written.
@st.cache_data(show_spinner=False)
def load_cleaned(export_path, manual_mtime):
    frames = [load_data(export_path, source="podium_csv")]
    if manual_mtime is not None:
        frames.append(load_data(str(MANUAL_PATH), sep=";", source="manual_form"))
    raw_all = pd.concat(frames, ignore_index=True)
    return run_pipeline_on_frame(raw_all, DATA_SCHEMA)


st.title("Swiss Olympic Athlete Selection")
st.caption("Applies the machine-readable selection criteria to the standardised "
           "competition data, including results added by hand.")

data_files = sorted(p for p in DATA_DIR.glob("*.csv") if p != MANUAL_PATH)
if not data_files:
    st.error("No competition data export found in the data folder.")
    st.stop()

with st.sidebar:
    st.header("Input")
    data_choice = st.selectbox("Competition data export", data_files,
                               format_func=lambda p: p.name)
    sports = available_sports()
    sport_choice = st.selectbox("Sport", sorted(sports.keys()))

manual_mtime = MANUAL_PATH.stat().st_mtime if MANUAL_PATH.exists() else None
cleaned, report = load_cleaned(str(data_choice), manual_mtime)
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

# surface rejected rows loudly instead of dropping them silently
# (constitution, Principle 2).
if report["rejected"] > 0:
    with st.expander(f"{report['rejected']} rows rejected during validation"):
        st.dataframe(pd.DataFrame(report["errors"]), hide_index=True)


# ---------------------------------------------------------------------------
# Add a result by hand. Extends the data basis for the smaller sports, where
# Gracenote is incomplete and results have to be added manually
# (L. Castella, personal communication, April 2026).
# ---------------------------------------------------------------------------
st.divider()
st.subheader("Add a result manually")
st.caption(f"The entry is stored persistently and is applied to {sport_choice} "
           "on the next run. Competition names come from the rule file, so a "
           "manual entry cannot introduce a name mismatch.")

# messages from the previous save survive the rerun via session state
if "manual_save_msg" in st.session_state:
    st.success(st.session_state.pop("manual_save_msg"))
if "manual_save_warn" in st.session_state:
    st.warning(st.session_state.pop("manual_save_warn"))

rule_opts = sport_rule_options(sports[sport_choice])
sport_slice = cleaned[cleaned["Sport"].str.lower() == sport_choice.lower()]
data_genders = [str(x) for x in sport_slice["Gender"].dropna().unique()]
data_disciplines = [str(x) for x in sport_slice["Discipline"].dropna().unique()]

gender_options = sorted(set(rule_opts["genders"]) | set(data_genders)) or \
    ["Men", "Women", "Mixed", "Open"]
discipline_options = sorted(set(rule_opts["disciplines"]) | set(data_disciplines))
metric_hint = " / ".join(rule_opts["metrics"]) or "rank"

with st.form("manual_entry", clear_on_submit=True):
    col_a, col_b = st.columns(2)
    with col_a:
        athlete = st.text_input("Athlete name")
        nationality = st.text_input("Nationality (NOC)", value="SUI")
        if discipline_options:
            discipline = st.selectbox("Discipline", discipline_options)
        else:
            discipline = st.text_input("Discipline")
        gender = st.selectbox("Gender", gender_options)
        klass = st.selectbox("Class", class_options())
    with col_b:
        competition = st.selectbox("Competition (from rules)",
                                   rule_opts["competitions"] or ["(no competition in rules)"])
        competition_free = st.text_input("or other competition (free text)")
        event_date = st.date_input("Competition date")
        dob_unknown = st.checkbox("Date of birth unknown")
        dob = st.date_input("Date of birth", value=None) if not dob_unknown else None

    st.markdown(f"**Result** (this sport is scored by: {metric_hint})")
    col_c, col_d, col_e = st.columns(3)
    with col_c:
        rank_type = st.selectbox("Rank", ["Placement", "no rank"] + RESULT_STATUS_CODES)
    with col_d:
        placement = st.number_input("Placement", min_value=1, step=1, value=1)
    with col_e:
        result_value = st.text_input("Performance value (time / points)")
    is_olympic = st.selectbox("Is Olympic discipline", ["Yes", "No", "Unknown"])

    submitted = st.form_submit_button("Save result")

if submitted:
    chosen_competition = competition_free.strip() or competition
    missing = []
    if not athlete.strip():
        missing.append("athlete name")
    if not chosen_competition or chosen_competition == "(no competition in rules)":
        missing.append("competition")

    if missing:
        st.error("Please fill in: " + ", ".join(missing))
    else:
        rank = placement if rank_type == "Placement" else None
        rank_status = rank_type if rank_type in RESULT_STATUS_CODES else None
        row = build_manual_row(
            athlete=athlete.strip(),
            sport=sport_choice,
            discipline=discipline.strip() if isinstance(discipline, str) else discipline,
            gender=gender,
            klass=klass,
            competition=chosen_competition,
            date=event_date.isoformat() if event_date else None,
            dob=dob.isoformat() if dob else None,
            nationality=nationality.strip() or "SUI",
            rank=rank,
            rank_status=rank_status,
            result=result_value.strip() or None,
            is_olympic="" if is_olympic == "Unknown" else is_olympic,
        )
        append_manual_entry(row, MANUAL_PATH)
        st.session_state["manual_save_msg"] = f"Saved {athlete.strip()} for {sport_choice}."
        # a missing birth date is a valid, honest state; it is only worth flagging
        # when this sport actually has an age criterion, since those routes will
        # then fall to manual review for this athlete.
        if rule_opts["has_age_criterion"] and not dob:
            st.session_state["manual_save_warn"] = (
                f"{sport_choice} has an age criterion and no date of birth was "
                "entered. Age-based routes will fall to manual review for this athlete."
            )
        st.rerun()