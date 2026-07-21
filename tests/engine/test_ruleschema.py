import pytest
from src.engine.engine import load_and_validate_rules

SCHEMA_PATH = "schemas/ruleschema.json"

# a minimal but complete, valid rule file. {date} is filled in per test.
VALID_RULE_TEMPLATE = """\
Description: "test rule file"
created at: "2026-01-01"
updated at: "2026-01-01"
version: "1.0"
rule_tree:
  description: "test sport rules"
  sport: "Bobsleigh"
  criteria:
    - criterion_id: "r1"
      description: "a route"
      priority: 1
      conditions:
        - condition_id: "r1_c1"
          description: "a condition"
          competition: ["IBSF World Cup"]
          date: {date}
          performance:
            metric: rank
            operator: less_or_equal
            value: 10
          count_at_least: 1
"""


# helper: write a rule file into a temp dir and return its path
def _write_rule(tmp_path, date_literal):
    content = VALID_RULE_TEMPLATE.format(date=date_literal)
    path = tmp_path / "rule.yaml"
    path.write_text(content, encoding="utf-8")
    return str(path)


# test: a well-formed ISO date window passes validation and returns the rules
def test_valid_iso_date_passes(tmp_path):
    path = _write_rule(tmp_path, '["2025-11-01", "2026-01-18"]')
    rules = load_and_validate_rules(path, SCHEMA_PATH)
    assert rules["rule_tree"]["sport"] == "Bobsleigh"


# test: a Swiss-style dotted date is rejected loudly (pattern enforced)
def test_dotted_date_rejected(tmp_path):
    path = _write_rule(tmp_path, '["01.01.2025", "31.12.2025"]')
    with pytest.raises(ValueError) as excinfo:
        load_and_validate_rules(path, SCHEMA_PATH)
    # the error should point at the date field
    assert "date" in str(excinfo.value)


# test: a bare year (not YYYY-MM-DD) is rejected loudly
def test_year_only_date_rejected(tmp_path):
    path = _write_rule(tmp_path, '["2025", "2026"]')
    with pytest.raises(ValueError):
        load_and_validate_rules(path, SCHEMA_PATH)


# test: a single-element date window is rejected (needs exactly start + end)
def test_single_element_date_rejected(tmp_path):
    path = _write_rule(tmp_path, '["2025-11-01"]')
    with pytest.raises(ValueError):
        load_and_validate_rules(path, SCHEMA_PATH)