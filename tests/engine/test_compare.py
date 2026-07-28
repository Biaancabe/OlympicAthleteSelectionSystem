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