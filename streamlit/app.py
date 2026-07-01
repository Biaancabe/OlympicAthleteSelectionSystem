import streamlit as st
import pandas as pd
from typing import List, Dict, Any
from utils import (
    load_data,
    get_sports,
    get_disciplines,
    get_genders,
    normalize_rules,
    filter_rules,
    count_criteria,
    get_athlete_record_counts,
    clean_data,
    load_json_schema,
    validate_data,
    load_sport_rule_map,
    load_yaml_rules,
    validate_rules,
    evaluate_athletes,
    DATA_SCHEMA_PATH,
    RULE_SCHEMA_PATH,
    RULE_FOLDER_NAME,
    DATA_PATH
)

# Simple password
PASSWORD = "NOC-Swiss"

# Ask for password
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    password_input = st.text_input("Enter password", type="password")
    if st.button("Login"):
        if password_input == PASSWORD:
            st.session_state.authenticated = True
            st.success("Authenticated!")
            st.rerun() 
        else:
            st.error("Wrong password")
else:
    # Load all data and schemas
    data_schema = load_json_schema(DATA_SCHEMA_PATH)
    print('Data schema loaded')
    rule_schema = load_json_schema(RULE_SCHEMA_PATH)
    print('Rule schema loaded')
    fulldata = load_data(DATA_PATH)
    print('Data loaded')
    # Extract the item schema since data_schema is for an array
    item_schema = data_schema.get('items', data_schema)
    fulldata = clean_data(fulldata, item_schema)
    print('Data cleaned')
    vality = validate_data(fulldata, data_schema)
    print('Data validated')

    st.title("Swiss Olympic Athlete Selection Tool")
    #st.write(f"Data loaded and validated: {vality}")

    SPORT = st.selectbox("Select a sport:", get_sports(fulldata))
    print(f"Selected sport: {SPORT}")
    RULE_FILE = load_sport_rule_map().get(SPORT, None)
    if RULE_FILE:
        RULE_PATH = f'{RULE_FOLDER_NAME}/{RULE_FILE}'
        rules = load_yaml_rules(RULE_PATH)
        Nrules = count_criteria(rules)
        print(f"Loaded {Nrules} selection criteria for {SPORT}")
        rules = normalize_rules(rules)
        print(f"Rules normalized")
        is_valid = validate_rules(rules, rule_schema)
        print(f"Rules validated: {is_valid}")
    else:
        st.write(f"No rules found for {SPORT}") 

    data = fulldata[fulldata['Sport'] == SPORT]
    print(f"Filtered data for sport: {SPORT}, records: {len(data)}")

    disciplines = get_disciplines(data)
    DISCIPLINE = st.multiselect("Select disciplines:", disciplines, default=disciplines)
    print(f"Selected disciplines: {DISCIPLINE}")

    data = data[data['Discipline'].isin(DISCIPLINE)]
    print(f"Filtered data for disciplines: {DISCIPLINE}, records: {len(data)}")

    genders = get_genders(data)
    GENDER = st.multiselect("Select genders:", genders, default=genders)
    data = data[data['Gender'].isin(GENDER)]

    print(f"Filtered data for genders: {GENDER}, records: {len(data)}")

    #st.write("Athlete Record Counts:")
    athletes = get_athlete_record_counts(data)['Athlete'].tolist()
    ATHLETES = st.multiselect("Select athletes to evaluate:", athletes, default=athletes)

    st.header("Evaluating Athletes")

    rules = filter_rules(rules, GENDER, DISCIPLINE)
    Nrules = count_criteria(rules)
    print(f"Number of selection criteria after filtering for genders: {GENDER} and disciplines: {DISCIPLINE}: {Nrules}")
    results = evaluate_athletes(ATHLETES, data, rules, False)
    st.write("Evaluation Results:")

    # Display
    for athlete in results:
        # Show the summary
        if athlete['N_criteria_passed'] > 0:
            emoji = "🟢"
        elif athlete['N_evidences_found'] > 0:
            emoji = "🟡"
        else:
            emoji = "🔴"
        
        st.write(f"**{athlete['athlete']}** - Criteria passed: {athlete['N_criteria_passed']}, Evidences found: {athlete['N_evidences_found']} {emoji}")

        # Expander for detailed evaluation
        with st.expander("Show detailed evaluation"):
            for eval_item in athlete['evaluation']:
                # Display criteria with colored indicator
                result = eval_item.get('result', 0)
                if result == 0:
                    st.write(f"**Criteria: (prio: {eval_item['priority']})** {eval_item['criteria']} 🟢")
                elif result == -1:
                    st.write(f"**Criteria: (prio: {eval_item['priority']})** {eval_item['criteria']} 🟡")
                else:  # result < -1
                    st.write(f"**Criteria: (prio: {eval_item['priority']})** {eval_item['criteria']} 🔴")
                for cond in eval_item['conditions']:
                    if cond['result'] == 0:
                        st.write(f"Condition: {cond['condition']} 🟢")
                    elif cond['result'] == -1:
                        st.write(f"Condition: {cond['condition']} 🟡")
                    else:  # result < -1
                        st.write(f"Condition: {cond['condition']} 🔴")
                    st.write("Evidence:")
                    for ev in cond['evidence']:
                        st.write(f"- {ev['competition']} on {ev['date']}: Result {ev['result']}")
                st.markdown("---")  # Separator between criteria













