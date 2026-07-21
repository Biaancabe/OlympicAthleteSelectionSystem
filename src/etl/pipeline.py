import pandas as pd
from src.etl.load import load_data, load_json_schema
from src.etl.clean import clean_data, exclude_non_sui
from src.etl.validate import validate_data
import os


def run_pipeline(data_path, schema_path, source="podium_csv", sep=None, output_dir="output"):
    # 1) load raw data + schema
    data = load_data(data_path, sep=sep, source=source)
    schema = load_json_schema(schema_path)
    item_schema = schema.get("items", schema)

    # 2) clean
    cleaned, clean_log = clean_data(data, item_schema)

    # 2a) exclude athletes not eligible to start for Switzerland.
    #     Only rows with a KNOWN non-SUI nationality are dropped. Rows with an
    #     empty Nationality (team/relay entries, or the occasional individual
    #     with a missing value) are left in place -> no silent, data-driven
    #     exclusion (constitution Principle 3); team handling is a separate,
    #     still-open question.
    cleaned, excluded = exclude_non_sui(cleaned)
    print(f"run_pipeline: excluded {len(excluded)} non-SUI rows "
          f"({excluded['Person/Team'].nunique()} athletes)")
    clean_log["non_sui_rows_excluded"] = len(excluded)
    clean_log["non_sui_excluded"] = (
        excluded[["Person/Team", "Nationality"]]
        .drop_duplicates()
        .to_dict("records")
    )

    # 2b) remove exact duplicate results (idempotency)
    key_cols = ['source', 'Date', 'Person/Team', 'Comp.SetDetail',
                'Discipline', 'Class', 'Gender']
    rows_before_dedup = len(cleaned)
    cleaned = cleaned.drop_duplicates(subset=key_cols, keep='first')
    duplicates_removed = rows_before_dedup - len(cleaned)
    print(f"run_pipeline: removed {duplicates_removed} duplicate rows "
          f"({rows_before_dedup} -> {len(cleaned)})")
    clean_log["duplicates_removed"] = duplicates_removed

    # 3) validate the cleaned data
    report = validate_data(cleaned, schema)

    # 4) merge the cleaning info into the report
    report["cleaning"] = clean_log

    # 5) save the cleaned data to disk (semicolon-separated for robustness)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "cleaned_data.csv")
    cleaned.to_csv(output_path, sep=";", index=False)
    report["output_path"] = output_path
    print(f"run_pipeline: saved cleaned data to {output_path}")

    # 6) return both the cleaned data and the combined report
    return cleaned, report