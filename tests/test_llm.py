import pytest

from src.llm.evidence import value_is_bound_to_evidence
from src.llm.ollama_client import LLMResponseError, OllamaClient
from src.llm.prompts import field_prompt

PAGES = [{"page_number": 1, "text": "Laboratories processed 1,200 specimens.", "tables": []}]


class FakeOllama(OllamaClient):
    response = '{"field":"sample_count","value":1200,"confidence":0.91,"page_number":1,"evidence":"processed 1,200 specimens","reason":"explicit total"}'

    def _request(self, endpoint, payload=None):
        return {"models": []} if endpoint == "/api/tags" else {"response": self.response}


def test_prompt_forbids_guessing():
    prompt = field_prompt("sample_count", "text")
    assert "return null" in prompt and "Do not invent" in prompt and "untrusted data" in prompt


def test_strict_page_evidence_contract():
    result = FakeOllama().extract_field("sample_count", PAGES)
    assert result.value == 1200 and result.page_number == 1


@pytest.mark.parametrize("response", ["[]", '"text"', "42", "{bad json"])
def test_non_object_or_invalid_json_is_rejected(response):
    client = FakeOllama()
    client.response = response
    with pytest.raises(LLMResponseError):
        client.extract_field("sample_count", PAGES)


def test_program_marker_is_not_valid_pdf_evidence():
    client = FakeOllama()
    client.response = '{"field":"sample_count","value":1,"confidence":1,"page_number":1,"evidence":"<page number=\\"1\\">","reason":"marker"}'
    with pytest.raises(LLMResponseError):
        client.extract_field("sample_count", PAGES)


def test_wrong_page_is_rejected():
    client = FakeOllama()
    client.response = client.response.replace('"page_number":1', '"page_number":2')
    with pytest.raises(LLMResponseError):
        client.extract_field("sample_count", PAGES)


def test_real_quote_with_wrong_value_is_rejected():
    client = FakeOllama()
    client.response = client.response.replace('"value":1200', '"value":999')
    with pytest.raises(LLMResponseError, match="not deterministically supported"):
        client.extract_field("sample_count", PAGES)


def test_correct_value_bound_to_wrong_field_evidence_is_rejected():
    pages = [{"page_number": 1, "text": "Positive cases: 1,200.", "tables": []}]
    client = FakeOllama()
    client.response = client.response.replace(
        '"evidence":"processed 1,200 specimens"', '"evidence":"Positive cases: 1,200"'
    )
    with pytest.raises(LLMResponseError, match="not deterministically supported"):
        client.extract_field("sample_count", pages)


def test_structured_value_is_rejected_by_schema():
    client = FakeOllama()
    client.response = client.response.replace('"value":1200', '"value":{"amount":1200}')
    with pytest.raises(LLMResponseError):
        client.extract_field("sample_count", PAGES)


@pytest.mark.parametrize(
    ("field", "value", "evidence"),
    [
        ("positive_count", 17, "Laboratory confirmation identified 17 positive specimens"),
        ("positive_rate", 0.125, "The corresponding positivity was 12.5%"),
        ("report_date", "2026-01-08", "Report Date: 2026-01-08"),
        ("period_start", "2026-01-01", "Period Start: 2026-01-01"),
        ("period_end", "2026-01-07", "Period End: 2026-01-07"),
        ("region", "North", "Region: North"),
    ],
)
def test_field_specific_value_evidence_binding(field, value, evidence):
    assert value_is_bound_to_evidence(field, value, evidence)
