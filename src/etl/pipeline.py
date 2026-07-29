import pandas as pd
from src.etl.load import load_data, load_json_schema
from src.etl.clean import clean_data, exclude_non_sui
from src.etl.validate import validate_data
import os


# process an already-loaded raw DataFrame: clean, exclude non-SUI, dedup,
# validate and save. This is the shared core; both the file-based entry point
# and the dashboard (which concatenates the export with manual entries before
# cleaning) go through here, so cleaning and validation stay identical for
# every source.
def run_pipeline_on_frame(data, schema_path, output_dir="output"):
    schema = load_json_schema(schema_path)
    item_schema = schema.get("items", schema)

    # 1) clean
    cleaned, clean_log = clean_data(data, item_schema)

    # 2) exclude athletes not eligible to start for Switzerland (known non-SUI).
    cleaned, excluded = exclude_non_sui(cleaned)
    print(f"run_pipeline: excluded {len(excluded)} non-SUI rows "
          f"({excluded['Person/Team'].nunique()} athletes)")
    clean_log["non_sui_rows_excluded"] = len(excluded)
    clean_log["non_sui_excluded"] = (
        excluded[["Person/Team", "Nationality"]]
        .drop_duplicates()
        .to_dict("records")
    )

    # 3) remove exact duplicate results. source is part of the key, so a manual
    #    entry and a Podium row are kept as distinct records on purpose.
    key_cols = ['source', 'Date', 'Person/Team', 'Comp.SetDetail',
                'Discipline', 'Class', 'Gender']
    rows_before_dedup = len(cleaned)
    cleaned = cleaned.drop_duplicates(subset=key_cols, keep='first')
    duplicates_removed = rows_before_dedup - len(cleaned)
    print(f"run_pipeline: removed {duplicates_removed} duplicate rows "
          f"({rows_before_dedup} -> {len(cleaned)})")
    clean_log["duplicates_removed"] = duplicates_removed

    # 4) validate the cleaned data
    report = validate_data(cleaned, schema)
    report["cleaning"] = clean_log

    # 5) save the cleaned data to disk (semicolon-separated for robustness)
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "cleaned_data.csv")
    cleaned.to_csv(output_path, sep=";", index=False)
    report["output_path"] = output_path
    print(f"run_pipeline: saved cleaned data to {output_path}")

    return cleaned, report


# file-based entry point: load one raw CSV, then run the shared core.
# Behaviour is unchanged from before the split.
def run_pipeline(data_path, schema_path, source="podium_csv", sep=None, output_dir="output"):
    data = load_data(data_path, sep=sep, source=source)
    return run_pipeline_on_frame(data, schema_path, output_dir=output_dir)