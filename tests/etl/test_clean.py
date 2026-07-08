# import the function we want to test
from src.etl.clean import clean_rank, clean_result, clean_date, clean_olympic


# test 1: a normal placement (e.g. rank 5)
def test_clean_rank_normal_placement():
    # we expect the number 5 and no special status
    assert clean_rank(5) == (5, None)


# test 2: a rank that comes in as text ("5" instead of 5)
def test_clean_rank_number_as_text():
    # should still become the number 5, no status
    assert clean_rank("5") == (5, None)


# test 3: a DNF (did not finish)
def test_clean_rank_dnf():
    # no number, but the status "DNF" must be preserved
    assert clean_rank("DNF") == (None, "DNF")


# test 4: a lowercase "dnq" -> should be recognised and returned uppercase
def test_clean_rank_lowercase_dnq():
    # no number, status normalised to "DNQ"
    assert clean_rank("dnq") == (None, "DNQ")


# test 5: a missing value (None)
def test_clean_rank_missing():
    # nothing to work with -> both None, don't guess
    assert clean_rank(None) == (None, None)





# test: a points value (e.g. figure skating score)
def test_clean_result_points():
    # 185 becomes the float 185.0, no status
    assert clean_result(185) == (185.0, None)


# test: a time value with decimals, coming in as text
def test_clean_result_time_with_comma():
    # "78.77" becomes the float 78.77, no status
    assert clean_result("78.77") == (78.77, None)


# test: a value with the Swiss thousands separator (apostrophe)
def test_clean_result_swiss_apostrophe():
    # "2'501" -> apostrophe removed -> 2501.0, no status
    assert clean_result("2'501") == (2501.0, None)


# test: a DNF (did not finish)
def test_clean_result_DNF():
    # no number, but the status "DNF" must be preserved
    assert clean_result("DNF") == (None, "DNF")


# test: a missing value (None)
def test_clean_result_None():
    # nothing to work with -> both None, don't guess
    assert clean_result(None) == (None, None)



# test: format "day-Month-year" (e.g. from data_2026-01-07.csv)
def test_clean_date_hyphen():
    # "09-Feb-1994" -> ISO format "1994-02-09"
    assert clean_date("09-Feb-1994") == "1994-02-09"


# test: format "day.month.year" with dots (e.g. from results_22012026.csv)
def test_clean_date_points():
    # "16.05.1998" -> ISO format "1998-05-16"
    assert clean_date("16.05.1998") == "1998-05-16"


# test: already in ISO format -> stays the same
def test_clean_date_hyphen_year_first():
    # "2001-07-24" is already ISO, so it stays unchanged
    assert clean_date("2001-07-24") == "2001-07-24"


# test: a missing value (None)
def test_clean_date_None():
    # nothing to parse -> None
    assert clean_date(None) is None




# test: "Yes" -> True
def test_clean_olympic_Yes():
    assert clean_olympic("Yes") is True


# test: "No" -> False
def test_clean_olympic_No():
    assert clean_olympic("No") is False


# test: empty string -> None (unknown, don't guess "not olympic")
def test_clean_olympic_missing():
    assert clean_olympic("") is None


# test: a missing value (None) -> None
def test_clean_olympic_none():
    assert clean_olympic(None) is None