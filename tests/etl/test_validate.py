import pandas as pd
from src.etl.load import load_json_schema
from src.etl.validate import validate_data


# helper: build one valid row as a small DataFrame
def make_valid_row():
    return pd.DataFrame([{
        "Date": "2025-02-23",
        "Year": 2025,
        "Comp.SetDetail": "IBU World Championships",
        "Sport": "Biathlon",
        "Discipline": "12.5km Mass Start",
        "Gender": "Women",
        "Class": "Seniors",
        "Person/Team": "Aita Gasparin (SUI, 09 Feb 1994)",
        "DoB": "1994-02-09",
        "source": "podium_csv",
        "Rank_num": 11,
        "Rank_Status": None,
        "Result_num": 2501.0,
        "Result_Status": None,
        "Is Olympic Discipline": True,
    }])


# test: a valid dataset passes validation (nothing rejected)
def test_validate_data_valid():
    schema = load_json_schema("schemas/dataschema.json")
    data = make_valid_row()
    report = validate_data(data, schema)
    assert report["rejected"] == 0
    assert report["valid"] == 1


# test: an invalid dataset is detected and rejected
def test_validate_data_invalid():
    schema = load_json_schema("schemas/dataschema.json")
    data = make_valid_row()
    data.loc[0, "Class"] = "SomethingInvalid"   # not an allowed Class value
    report = validate_data(data, schema)
    assert report["rejected"] == 1
    assert report["valid"] == 0