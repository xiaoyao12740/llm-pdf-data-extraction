from src.llm.base import LLMFieldResult, LLMProvider
from src.pipeline import _llm_candidates, run


class FakeProvider(LLMProvider):
    def health_check(self):
        return True

    def extract_field(self, field, pages):
        return LLMFieldResult(field=field, value=999, confidence=1, page_number=1, evidence="Tests: 100", reason="fake")


def test_llm_confidence_cannot_override_deterministic_candidate():
    rule = {
        "field_name": "sample_count",
        "raw_value": "100",
        "normalized_candidate": 100,
        "page_number": 1,
        "source_text": "Tests: 100",
        "extraction_method": "rule",
        "confidence": 0.2,
    }
    fields, issues = _llm_candidates(
        [{"page_number": 1, "text": "Tests: 100", "tables": []}], [rule], FakeProvider(), threshold=0.6
    )
    sample = next(item for item in fields if item["field_name"] == "sample_count")
    assert sample["normalized_candidate"] == 100 and sample["extraction_method"] == "rule"


def test_pipeline_does_not_require_ground_truth(tmp_path):
    results = run(raw_dir=tmp_path / "raw", processed_dir=tmp_path / "out", evaluate_results=False)
    assert results == [] and (tmp_path / "out" / "structured_records.json").exists()


def test_unknown_files_are_not_evaluated_unless_requested(tmp_path):
    results = run(raw_dir=tmp_path / "unknown", processed_dir=tmp_path / "out", ground_truth=tmp_path / "missing.json")
    assert results == []
