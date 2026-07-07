import json
from jsonschema import Draft7Validator
import pandas as pd

# validate a cleaned DataFrame row by row against the item schema
def validate_data(data, schema):
    # if the schema is an array schema, take the item schema out of it
    item_schema = schema.get("items", schema)
    validator = Draft7Validator(item_schema)

    report = {
        "total": len(data),
        "valid": 0,
        "rejected": 0,
        "errors": [],
    }

    # go through each row individually
    for index, row in data.iterrows():
        # convert the row to a dict, turning pandas NaN into real None
        record = row.where(pd.notnull(row), None).to_dict()              # turn the row into a plain dict
        row_errors = sorted(validator.iter_errors(record), key=lambda e: e.path)

        if not row_errors:
            report["valid"] += 1
        else:
            report["rejected"] += 1
            for err in row_errors:
                field = ".".join([str(p) for p in err.path]) or "root"
                report["errors"].append({
                    "row": index,
                    "field": field,
                    "message": err.message,
                })

    return report