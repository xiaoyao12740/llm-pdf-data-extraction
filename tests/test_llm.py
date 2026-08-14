import pytest
from src.llm.ollama_client import OllamaClient
from src.llm.prompts import field_prompt


class FakeOllama(OllamaClient):
    def _request(self,endpoint,payload=None):
        if endpoint=="/api/tags": return {"models":[]}
        return {"response":'{"field":"sample_count","value":1200,"confidence":0.91,"evidence":"processed 1,200 specimens","reason":"explicit total"}'}


def test_prompt_forbids_guessing(): assert "return null" in field_prompt("sample_count","text") and "Do not invent" in field_prompt("sample_count","text")
def test_strict_evidence_contract():
    client=FakeOllama(); result=client.extract_field("sample_count","processed 1,200 specimens")
    assert result.value==1200 and result.evidence=="processed 1,200 specimens"
    with pytest.raises(ValueError): client.extract_field("sample_count","unrelated text")
