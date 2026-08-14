import re
from dataclasses import asdict, dataclass
from datetime import datetime
from .field_mapper import FIELD_ALIASES, canonical_field


@dataclass
class ExtractedField:
    field_name: str
    raw_value: str
    normalized_candidate: object
    page_number: int
    source_text: str
    extraction_method: str = "rule"
    confidence: float = 0.95

    def to_dict(self) -> dict:
        return asdict(self)


def _normalize(field: str, raw: str):
    value = raw.strip().rstrip(".")
    if field in {"sample_count", "positive_count"}:
        return int(value.replace(",", ""))
    if field == "positive_rate":
        return float(value.rstrip("%")) / 100
    if field in {"report_date", "period_start", "period_end"}:
        return datetime.strptime(value.replace("/", "-"), "%Y-%m-%d").date().isoformat()
    return value


def extract_fields(pages: list[dict]) -> list[dict]:
    found: dict[str, ExtractedField] = {}
    value_patterns = {
        "report_date": r"\d{4}[-/]\d{2}[-/]\d{2}", "period_start": r"\d{4}[-/]\d{2}[-/]\d{2}",
        "period_end": r"\d{4}[-/]\d{2}[-/]\d{2}", "region": r"[A-Za-z]+(?:\s+Region)?",
        "sample_count": r"\d[\d,]*", "positive_count": r"\d[\d,]*", "positive_rate": r"\d+(?:\.\d+)?%",
    }
    for page in pages:
        lines = [line.strip() for line in page["text"].splitlines() if line.strip()]
        joined = "\n".join(lines)
        for table in page.get("tables", []):
            if len(table) < 2:
                continue
            headers, values = table[0], table[1]
            for label, raw in zip(headers, values):
                field = canonical_field(label or "")
                if field and raw and field not in found:
                    try:
                        found[field] = ExtractedField(field, raw, _normalize(field, raw), page["page_number"], f"{label}: {raw}", confidence=.96)
                    except (TypeError, ValueError):
                        pass
        for field, aliases in FIELD_ALIASES.items():
            if field in found:
                continue
            alias_pattern = "|".join(re.escape(a) for a in sorted(aliases, key=len, reverse=True))
            match = re.search(rf"(?im)^\s*(?:{alias_pattern})\s*(?::|=)?\s*(?:\n\s*)?({value_patterns[field]})\s*$", joined)
            if match:
                raw = match.group(1)
                found[field] = ExtractedField(field, raw, _normalize(field, raw), page["page_number"], match.group(0), confidence=.98)
        # Natural-language fallback deliberately has lower confidence.
        if "sample_count" not in found:
            match = re.search(r"(?i)(?:total of|processed)\s+([\d,]+)\s+(?:samples|specimens)", joined)
            if match:
                found["sample_count"] = ExtractedField("sample_count", match.group(1), _normalize("sample_count", match.group(1)), page["page_number"], match.group(0), confidence=.65)
        if "positive_count" not in found:
            match = re.search(r"(?i)(?:of which\s+)?([\d,]+)\s+were positive", joined)
            if match:
                found["positive_count"] = ExtractedField("positive_count", match.group(1), _normalize("positive_count", match.group(1)), page["page_number"], match.group(0), confidence=.65)
    return [item.to_dict() for item in found.values()]
