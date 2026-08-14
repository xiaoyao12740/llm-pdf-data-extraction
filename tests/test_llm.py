import pytest

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
