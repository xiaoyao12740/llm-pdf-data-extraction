import re

from src.normalization.normalizer import normalize_value

COUNT_VALUE = r"(?P<value>\d[\d,]*)"
RATE_VALUE = r"(?P<value>\d[\d,]*(?:\.\d+)?\s*%)"
DATE_VALUE = r"(?P<value>\d{4}[-/]\d{1,2}[-/]\d{1,2})"
DATE_TOKEN = r"\d{4}[-/]\d{1,2}[-/]\d{1,2}"
LABEL_SEPARATOR = r"\s*(?::|=|\|)?\s*"


def _patterns(*patterns):
    return tuple(re.compile(pattern, re.I | re.M) for pattern in patterns)


FIELD_VALUE_PATTERNS = {
    "sample_count": _patterns(
        rf"\b(?:samples?\s+tested|total\s+tests?|tests?|sample\s+count)\b{LABEL_SEPARATOR}{COUNT_VALUE}",
        rf"\b(?:reporting\s+)?cohort\s+comprised\s+{COUNT_VALUE}\s+(?:samples?|specimens?|tests?)\b",
        rf"\b(?:laborator(?:y|ies)\s+)?processed\s+{COUNT_VALUE}\s+(?:samples?|specimens?|tests?)\b",
    ),
    "positive_count": _patterns(
        rf"\b(?:positive\s+cases?|detected\s+positive|positives?|positive\s+count)\b{LABEL_SEPARATOR}{COUNT_VALUE}",
        rf"\b(?:laboratory\s+)?(?:confirmation\s+)?(?:identified|confirmed|detected)\s+{COUNT_VALUE}\s+positive(?:\s+(?:samples?|specimens?|tests?))?\b",
        rf"\b{COUNT_VALUE}\s+(?:samples?|specimens?|tests?)?\s*(?:were\s+)?positive\b",
    ),
    "positive_rate": _patterns(
        rf"\b(?:positive\s+rate|detection\s+rate|positivity|rate)\b{LABEL_SEPARATOR}{RATE_VALUE}",
        rf"\b(?:positive\s+rate|positivity)\s+(?:was|is|of)\s+{RATE_VALUE}",
    ),
    "report_date": _patterns(
        rf"\b(?:report\s+date|generated\s+on|issued(?:\s+on)?)\b{LABEL_SEPARATOR}{DATE_VALUE}",
    ),
    "period_start": _patterns(
        rf"\b(?:period\s+start|from)\b{LABEL_SEPARATOR}{DATE_VALUE}",
        rf"\b(?:during|between)\s+{DATE_VALUE}\s+(?:through|to|and)\s+{DATE_TOKEN}\b",
    ),
    "period_end": _patterns(
        rf"\b(?:period\s+end|to)\b{LABEL_SEPARATOR}{DATE_VALUE}",
        rf"\b(?:during|between)\s+{DATE_TOKEN}\s+(?:through|to|and)\s+{DATE_VALUE}\b",
    ),
    "region": _patterns(
        r"(?:^|\n)[ \t]*(?:region|area|zone)\b[ \t]*(?::|=|\|)?[ \t]*"
        r"(?P<value>[^\r\n,;|.]+?)[ \t]*(?=$|[\r\n,;|.])",
    ),
}


def _normalized_words(value) -> str:
    return " ".join(re.findall(r"[a-z0-9]+", str(value).casefold()))


def _bound_values(field: str, evidence: str):
    for pattern in FIELD_VALUE_PATTERNS.get(field, ()):
        yield from (match.group("value").strip() for match in pattern.finditer(evidence))


def value_is_bound_to_evidence(field: str, value, evidence: str, tolerance: float = 0.0001) -> bool:
    """Return whether a field-specific relation in the quote captures the exact value."""
    try:
        expected = normalize_value(field, value)
    except (TypeError, ValueError):
        return False

    for bound_value in _bound_values(field, evidence):
        try:
            candidate = normalize_value(field, bound_value)
        except (TypeError, ValueError):
            continue
        if field == "positive_rate":
            if abs(float(candidate) - float(expected)) <= tolerance:
                return True
        elif field == "region":
            if _normalized_words(candidate) == _normalized_words(expected):
                return True
        elif candidate == expected:
            return True
    return False
