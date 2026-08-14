FIELD_TERMS = {
    "report_date": ("report date", "generated on", "issued"),
    "period_start": ("period", "from", "during"),
    "period_end": ("period", "to", "during"),
    "region": ("region", "area", "zone"),
    "sample_count": ("sample", "specimen", "test", "processed"),
    "positive_count": ("positive", "detected", "confirmation"),
    "positive_rate": ("rate", "percent", "positivity", "%"),
}


def select_context(field: str, pages: list[dict], max_chars: int = 4000) -> str:
    terms = FIELD_TERMS[field]
    chunks = []
    for page in pages:
        lines = [line.strip() for line in page["text"].splitlines() if line.strip()]
        selected = [line for line in lines if any(term in line.casefold() for term in terms)]
        if selected:
            chunks.append(f'<page number="{page["page_number"]}">\n' + "\n".join(selected) + "\n</page>")
    return "\n".join(chunks)[:max_chars]
