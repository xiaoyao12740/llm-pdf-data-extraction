from dataclasses import asdict, dataclass


@dataclass
class ValidationIssue:
    field_name: str
    issue_type: str
    severity: str
    message: str


def validate_record(record: dict, tolerance: float = 0.005) -> list[dict]:
    issues = []

    def add(field, kind, message):
        issues.append(asdict(ValidationIssue(field, kind, "error", message)))

    samples = record.get("sample_count")
    positives = record.get("positive_count")
    rate = record.get("positive_rate")
    for field in (
        "report_date",
        "period_start",
        "period_end",
        "region",
        "sample_count",
        "positive_count",
        "positive_rate",
    ):
        if record.get(field) is None:
            add(field, "missing", f"{field} is missing")
    if samples is not None and samples < 0:
        add("sample_count", "range", "sample_count must be non-negative")
    if positives is not None and positives < 0:
        add("positive_count", "range", "positive_count must be non-negative")
    if samples is not None and positives is not None and positives > samples:
        add("positive_count", "cross_field", "positive_count exceeds sample_count")
    if rate is not None and not 0 <= rate <= 1:
        add("positive_rate", "range", "positive_rate must be between 0 and 1")
    if samples and positives is not None and rate is not None and abs(rate - positives / samples) > tolerance:
        add("positive_rate", "rate_mismatch", "positive_rate is inconsistent with counts")
    if record.get("period_start") and record.get("period_end") and record["period_start"] > record["period_end"]:
        add("period_start", "date_range", "period_start is after period_end")
    return issues
