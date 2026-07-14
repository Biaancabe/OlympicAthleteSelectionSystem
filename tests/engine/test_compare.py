from src.engine.compare import satisfies, is_near


# --- satisfies ---
def test_satisfies_less_or_equal_true():
    assert satisfies(5, "less_or_equal", comp_value=8) is True

def test_satisfies_less_or_equal_false():
    assert satisfies(9, "less_or_equal", comp_value=8) is False

def test_satisfies_between_true():
    assert satisfies(5, "between", comp_min=1, comp_max=8) is True

def test_satisfies_missing_value():
    assert satisfies(None, "less_or_equal", comp_value=8) is False

# --- is_near ---
def test_is_near_rank_just_above():
    # rank 9 for Top-8 -> near (just missed)
    assert is_near(9, "less_or_equal", comp_value=8) is True

def test_is_near_rank_too_far():
    # rank 11 for Top-8 -> not near (too far)
    assert is_near(11, "less_or_equal", comp_value=8) is False

def test_is_near_rank_full_hit_not_near():
    # rank 5 for Top-8 -> full hit, so NOT near
    assert is_near(5, "less_or_equal", comp_value=8) is False

def test_is_near_between_just_above():
    # rank 9 for between 1-8 -> near
    assert is_near(9, "between", comp_min=1, comp_max=8) is True

def test_is_near_points_just_below():
    # 180 points for min 185 -> near (just below)
    assert is_near(180, "greater_or_equal", comp_value=185) is True

def test_is_near_points_too_far():
    # 140 points for min 185 -> not near
    assert is_near(140, "greater_or_equal", comp_value=185) is False

def test_is_near_missing_value():
    # no value -> not near
    assert is_near(None, "less_or_equal", comp_value=8) is False