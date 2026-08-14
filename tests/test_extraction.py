from src.extraction.field_mapper import canonical_field
from src.extraction.rule_extractor import extract_fields


def test_alias_mapping():
    assert canonical_field("Total Tests") == "sample_count"


def test_standard_fields():
    fields = extract_fields(
        [
            {
                "page_number": 1,
                "text": "Report Date: 2026-01-08\nPeriod Start: 2026-01-01\nPeriod End: 2026-01-07\nRegion: North\nSamples Tested: 1,200\nPositive Cases: 83\nPositive Rate: 6.92%",
                "tables": [],
            }
        ]
    )
    result = {x["field_name"]: x["normalized_candidate"] for x in fields}
    assert result["sample_count"] == 1200 and result["positive_rate"] == 0.0692
    assert all(x["page_number"] == 1 and x["extraction_method"] == "rule" for x in fields)


def test_table_fields_have_table_provenance():
    pages = [{"page_number": 2, "text": "", "tables": [[["Tests", "Positive", "Rate"], ["100", "5", "5.00%"]]]}]
    fields = extract_fields(pages)
    assert fields and all(item["extraction_method"] == "table" and item["page_number"] == 2 for item in fields)
