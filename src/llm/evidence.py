import re

from src.normalization.normalizer import normalize_value

FIELD_CONTEXT = {
    "sample_count": re.compile(r"\b(total|tests?|tested|processed|sample\s*count|cohort(?:\s+comprised)?)\b", re.I),
    "positive_count": re.compile(r"\b(positive|positives|detected|confirmation\s+identified)\b", re.I),
    "positive_rate": re.compile(r"(%|\b(rate|positivity|percent(?:age)?)\b)", re.I),
    "report_date": re.compile(r"\b(report\s+date|generated\s+on)\b", re.I),
    "period_start": re.compile(r"\b(period\s+start|from|start(?:ed|ing)?)\b", re.I),
    "period_end": re.compile(r"\b(period\s+end|to|end(?:ed|ing)?)\b", re.I),
    "region": re.compile(r"\b(region|area|zone)\b", re.I),
}

NUMBER_PATTERN = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?\s*%?")
DATE_PATTERN = re.compile(r"\b\d{4}[-/]\d{1,2}[-/]\d{1,2}\b")


def _normalized_words(value) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value).casefold()))


def value_is_bound_to_evidence(field: str, value, evidence: str, tolerance: float = 0.0001) -> bool:
    """Return whether a field value is deterministically supported by its quote."""
    context = FIELD_CONTEXT.get(field)
    if context is None or not context.search(evidence):
        return False
    try:
        expected = normalize_value(field, value)
    except (TypeError, ValueError):
        return False
    if field in {"sample_count", "positive_count"}:
        for token in NUMBER_PATTERN.findall(evidence):
            candidate = token.strip().rstrip("%")
            if "." not in candidate and int(candidate.replace(",", "")) == expected:
                return True
        return False
    if field == "positive_rate":
        for token in NUMBER_PATTERN.findall(evidence):
            try:
                candidate = normalize_value(field, token.strip())
            except ValueError:
                continue
            if abs(float(candidate) - float(expected)) <= tolerance:
                return True
        return False
    if field in {"report_date", "period_start", "period_end"}:
        return any(normalize_value(field, token) == expected for token in DATE_PATTERN.findall(evidence))
    if field == "region":
        return _normalized_words(expected) in _normalized_words(evidence)
    return False
