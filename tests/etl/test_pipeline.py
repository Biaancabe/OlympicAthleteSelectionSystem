from io import StringIO
import pandas as pd

from src.etl.pipeline import run_pipeline_on_frame

SCHEMA_PATH = "schemas/dataschema.json"


def _template_row():
    # one realistic raw Podium row (individual athlete, clock-time result)
    return {
        'Date': '23-Feb-2025', 'Year': 2025,
        'Competition': 'IBU World Championships',
        'CompetitionSet': 'World Championships',
        'Comp.SetDetail': 'IBU World Championships',
        'Sport': 'Biathlon', 'Discipline': '12.5km Mass Start',
        'Gender': 'Women', 'Class': 'Seniors', 'Phase': None,
        'Rank': '11', 'Medal': None, 'Team Members': 'No',
        'Person/Team': 'Aita Gasparin (SUI, 09 Feb 1994)',
        'Person': 'Aita Gasparin', 'Person First Name': 'Aita',
        'Person Last Name': 'Gasparin', 'PersonGender': 'Women',
        'Team': 'Switzerland', 'Nationality': 'SUI',
        'DoB': '09-Feb-1994', 'YoB': None, 'Age (days)': '31-014',
        'Age': 31.0, 'Country': 'Switzerland', 'Country Code': 'SUI',
        'Continent': 'Europe', 'Result': '41:40.7', 'Sec/Mtr/Pts': "2'501",
        'Host City': 'Lenzerheide', 'Host Country': 'Switzerland',
        'Host Continent': 'Europe', '# Participants': 30.0,
        '# Countries': 14.0, '# Continents': 1.0, 'World Ranking': None,
        'Rank Within Country': 1.0, 'Is Olympic Discipline': 'Yes',
        'source': 'podium_csv',
    }


def _make_raw_frame():
    # r1 and r2 are an exact duplicate (same natural key) -> dedup must drop one.
    # r3 differs in competition and date -> must be kept.
    r1 = _template_row()
    r2 = _template_row()
    r3 = _template_row()
    r3['Comp.SetDetail'] = 'IBU World Cup Oberhof'
    r3['Date'] = '12-Jan-2025'
    r3['Result'] = '40:12.0'
    r3['Rank'] = '7'
    return pd.DataFrame([r1, r2, r3])


def test_pipeline_idempotent(tmp_path):
    # processing the same input twice must produce the same standardised data
    cleaned1, _ = run_pipeline_on_frame(_make_raw_frame(), SCHEMA_PATH,
                                        output_dir=str(tmp_path))
    cleaned2, _ = run_pipeline_on_frame(_make_raw_frame(), SCHEMA_PATH,
                                        output_dir=str(tmp_path))

    pd.testing.assert_frame_equal(
        cleaned1.reset_index(drop=True),
        cleaned2.reset_index(drop=True),
    )

    # the deliberate duplicate was removed, so deduplication actually acted
    assert len(cleaned1) == 2


def test_pipeline_output_roundtrip(tmp_path):
    # writing the standardised data and reading it back must preserve the
    # fields (names and order) and the record values
    cleaned, report = run_pipeline_on_frame(_make_raw_frame(), SCHEMA_PATH,
                                            output_dir=str(tmp_path))
    reloaded = pd.read_csv(report["output_path"], sep=";")

    # same fields in the same order, same number of records
    assert list(reloaded.columns) == list(cleaned.columns)
    assert len(reloaded) == len(cleaned)

    # CSV stores everything as text, so compare the reloaded frame against the
    # in-memory frame passed through the same read path (both via read_csv).
    cleaned_roundtripped = pd.read_csv(
        StringIO(cleaned.to_csv(sep=";", index=False)), sep=";"
    )
    pd.testing.assert_frame_equal(
        reloaded.reset_index(drop=True),
        cleaned_roundtripped.reset_index(drop=True),
    )