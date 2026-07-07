import pandas as pd
from src.etl.load import load_data, load_json_schema
from src.etl.clean import clean_data
from src.etl.validate import validate_data


def run_pipeline(data_path, schema_path, source="podium_csv", sep=None):
    # 1) load raw data + schema
    data = load_data(data_path, sep=sep, source=source)
    schema = load_json_schema(schema_path)
    item_schema = schema.get("items", schema)

    # 2) clean
    cleaned, clean_log = clean_data(data, item_schema)

    # 3) validate the cleaned data
    report = validate_data(cleaned, schema)

    # 4) merge the cleaning info into the report
    report["cleaning"] = clean_log

    # 5) return both the cleaned data and the combined report
    return cleaned, report