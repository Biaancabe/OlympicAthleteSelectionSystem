from src.engine.compare import satisfies


# --- satisfies ---
def test_satisfies_less_or_equal_true():
    assert satisfies(5, "less_or_equal", comp_value=8) is True

def test_satisfies_less_or_equal_false():
    assert satisfies(9, "less_or_equal", comp_value=8) is False

def test_satisfies_between_true():
    assert satisfies(5, "between", comp_min=1, comp_max=8) is True

def test_satisfies_missing_value():
    assert satisfies(None, "less_or_equal", comp_value=8) is False

def test_satisfies_greater_or_equal_true():
    assert satisfies(185, "greater_or_equal", comp_value=185) is True

def test_satisfies_greater_or_equal_false():
    assert satisfies(184, "greater_or_equal", comp_value=185) is False

def test_satisfies_equal_true():
    assert satisfies(1, "equal", comp_value=1) is True

def test_satisfies_equal_false():
    assert satisfies(2, "equal", comp_value=1) is False

def test_satisfies_unknown_operator_raises():
    import pytest
    with pytest.raises(ValueError):
        satisfies(1, "not_an_operator", comp_value=1)