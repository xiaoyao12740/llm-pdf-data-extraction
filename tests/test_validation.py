from src.validation.validators import validate_record


def kinds(record): return {x["issue_type"] for x in validate_record(record)}
def test_count_error(): assert "cross_field" in kinds({"sample_count":10,"positive_count":11})
def test_rate_error(): assert "rate_mismatch" in kinds({"sample_count":100,"positive_count":10,"positive_rate":.3})
def test_date_error(): assert "date_range" in kinds({"period_start":"2026-02-01","period_end":"2026-01-01"})
