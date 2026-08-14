from collections import Counter

import pytest

import src.pipeline as pipeline
from src.llm.base import LLMFieldResult, LLMProvider
from src.pipeline import _llm_candidates, _llm_telemetry, run


class FakeProvider(LLMProvider):
    def health_check(self):
        return True

    def extract_field(self, field, pages):
        return LLMFieldResult(field=field, value=999, confidence=1, page_number=1, evidence="Tests: 100", reason="fake")


def test_llm_confidence_cannot_override_deterministic_candidate(monkeypatch):
    monkeypatch.setattr(pipeline, "TARGET_FIELDS", ("sample_count",))
    stats = Counter()
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
        [{"page_number": 1, "text": "Tests: 100", "tables": []}],
        [rule],
        FakeProvider(),
        threshold=0.6,
        stats=stats,
    )
    sample = next(item for item in fields if item["field_name"] == "sample_count")
    assert sample["normalized_candidate"] == 100 and sample["extraction_method"] == "rule"
    assert _llm_telemetry(stats) == {
        "calls": 1,
        "accepted": 0,
        "abstained": 0,
        "rejected": 0,
        "ignored": 1,
    }


def test_pipeline_does_not_require_ground_truth(tmp_path):
    results = run(raw_dir=tmp_path / "raw", processed_dir=tmp_path / "out", evaluate_results=False)
    assert results == [] and (tmp_path / "out" / "structured_records.json").exists()


def test_unknown_files_are_not_evaluated_unless_requested(tmp_path):
    results = run(raw_dir=tmp_path / "unknown", processed_dir=tmp_path / "out", ground_truth=tmp_path / "missing.json")
    assert results == []


class UnavailableProvider(FakeProvider):
    def health_check(self):
        return False


class FailingProvider(FakeProvider):
    error = TimeoutError("runtime timeout")

    def extract_field(self, field, pages):
        raise self.error


def test_startup_unavailable_obeys_fail_fast(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "OllamaClient", lambda **kwargs: UnavailableProvider())
    with pytest.raises(RuntimeError, match="unavailable"):
        run(
            raw_dir=tmp_path / "raw",
            processed_dir=tmp_path / "out",
            llm="ollama",
            llm_failure_policy="fail_fast",
        )


@pytest.mark.parametrize("error", [TimeoutError("timeout"), ValueError("invalid JSON or schema")])
def test_runtime_llm_failure_obeys_fail_fast(error):
    provider = FailingProvider()
    provider.error = error
    with pytest.raises(RuntimeError, match="LLM extraction failed"):
        _llm_candidates(
            [{"page_number": 1, "text": "Report Date: 2026-01-01", "tables": []}],
            [],
            provider,
            failure_policy="fail_fast",
        )


def test_runtime_llm_failure_falls_back_with_fixed_telemetry():
    stats = Counter()
    fields, issues = _llm_candidates(
        [{"page_number": 1, "text": "Report Date: 2026-01-01", "tables": []}],
        [],
        FailingProvider(),
        stats=stats,
        failure_policy="fallback_rules",
    )
    assert fields == []
    assert len(issues) == len(pipeline.TARGET_FIELDS)
    assert _llm_telemetry(stats) == {
        "calls": 7,
        "accepted": 0,
        "abstained": 0,
        "rejected": 7,
        "ignored": 0,
    }


def test_llm_telemetry_rejects_unaccounted_calls():
    with pytest.raises(ValueError, match="1 calls but 0 outcomes"):
        _llm_telemetry(Counter(calls=1))
