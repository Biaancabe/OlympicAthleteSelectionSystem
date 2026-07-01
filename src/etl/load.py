# imports
import pandas as pd
import json
import yaml

# load data (Podium / Gracenote-CSV or manually created data )
def load_data(data_path, sep=None, source='podium_csv'):
    data = pd.read_csv(data_path, sep=sep, engine='python')
    data = data.where(pd.notnull(data), None)
    data['source'] = source
    return data

# loading the JSON schema files
def load_json_schema(schema_path):
    with open(schema_path, 'r') as f:                       # open the file at schema_path (read mode)
        return json.load(f)                                 # parse the content using json.load() AND return the result

# loading the YAML rules file
def load_yaml_rules(rules_path):
    with open(rules_path, 'r') as f:
        return yaml.safe_load(f)

# manual single-result entry (e.g. via input form)
# Deferred: depends on the input interface, which is tied to the still-open dashboard/GUI scope decision.
# See specs/selection-engine.md.
def load_manual_form_entry(entry):
    raise NotImplementedError("Manual form entry not yet implemented.")