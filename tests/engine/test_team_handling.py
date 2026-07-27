import pandas as pd
from src.engine.engine import is_individual_entry, select_units


# test: an individual entry is recognised by its "(NOC, date)" suffix
def test_is_individual_entry_true_for_athlete():
    assert is_individual_entry("Marco Odermatt (SUI, 08 Oct 1997)") is True

# test: team, relay and pair entries are not individual
def test_is_individual_entry_false_for_teams():
    assert is_individual_entry("Switzerland") is False
    assert is_individual_entry("Switzerland 1") is False
    assert is_individual_entry("Sieber / Zehnder") is False


def _data(names):
    return pd.DataFrame({"Person/Team": names})


# test: individual mode keeps athletes and excludes team entries
def test_select_units_individual_mode():
    df = _data(["Marco Odermatt (SUI, 08 Oct 1997)", "Switzerland", "Sieber / Zehnder"])
    kept, excluded = select_units(df, "individual")
    assert kept == ["Marco Odermatt (SUI, 08 Oct 1997)"]
    assert set(excluded) == {"Switzerland", "Sieber / Zehnder"}


# test: team mode keeps team entries and excludes individual athletes
def test_select_units_team_mode():
    df = _data(["Marco Odermatt (SUI, 08 Oct 1997)", "Switzerland", "Sieber / Zehnder"])
    kept, excluded = select_units(df, "team")
    assert set(kept) == {"Switzerland", "Sieber / Zehnder"}
    assert excluded == ["Marco Odermatt (SUI, 08 Oct 1997)"]


# test: default behaves like individual
def test_select_units_default_is_individual():
    df = _data(["Marco Odermatt (SUI, 08 Oct 1997)", "Switzerland"])
    kept, _ = select_units(df, "individual")
    assert kept == ["Marco Odermatt (SUI, 08 Oct 1997)"]