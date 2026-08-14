import json

FIELD_TYPES={"report_date":"ISO date string YYYY-MM-DD","period_start":"ISO date string YYYY-MM-DD","period_end":"ISO date string YYYY-MM-DD","region":"string","sample_count":"integer","positive_count":"integer","positive_rate":"decimal fraction between 0 and 1"}


def field_prompt(field: str, context: str) -> str:
    schema={"field":field,"value":None,"confidence":0.0,"evidence":"","reason":""}
    return f"""Extract only the field {field!r} ({FIELD_TYPES[field]}) from the supplied text.
Return exactly one JSON object matching this shape: {json.dumps(schema)}
The evidence must be a verbatim substring of the supplied text.
If the value is not explicitly supported by the supplied text, return null.
Do not invent missing information or use outside knowledge. Do not add Markdown.

SUPPLIED TEXT:
{context[:4000]}"""
