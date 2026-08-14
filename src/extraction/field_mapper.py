"""Canonical field aliases used by the deterministic extractor."""

FIELD_ALIASES = {
    "report_date": ("Report Date", "Generated On"),
    "period_start": ("Period Start", "From"),
    "period_end": ("Period End", "To"),
    "region": ("Region", "Area", "Zone"),
    "sample_count": ("Samples Tested", "Total Tests", "Tests", "Number Tested"),
    "positive_count": ("Positive Cases", "Detected Positive", "Positives", "Positive"),
    "positive_rate": ("Positive Rate", "Detection Rate", "Rate"),
}


def canonical_field(label: str) -> str | None:
    normalized = " ".join(label.casefold().split())
    for field, aliases in FIELD_ALIASES.items():
        if normalized in {alias.casefold() for alias in aliases}:
            return field
    return None
