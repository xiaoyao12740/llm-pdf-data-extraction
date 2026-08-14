import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from pydantic import ValidationError

from .base import LLMFieldResult, LLMProvider
from .context import select_context
from .prompts import field_prompt


class LLMResponseError(ValueError):
    pass


class OllamaClient(LLMProvider):
    def __init__(self, model="qwen2.5:7b", base_url="http://localhost:11434", timeout=120):
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _request(self, endpoint, payload=None):
        body = None if payload is None else json.dumps(payload).encode()
        request = Request(self.base_url + endpoint, data=body, headers={"Content-Type": "application/json"})
        with urlopen(request, timeout=self.timeout) as response:
            return json.loads(response.read())

    def health_check(self):
        try:
            return isinstance(self._request("/api/tags").get("models"), list)
        except (OSError, URLError, ValueError, AttributeError):
            return False

    def extract_field(self, field, pages):
        context = select_context(field, pages)
        response = self._request(
            "/api/generate",
            {
                "model": self.model,
                "prompt": field_prompt(field, context),
                "stream": False,
                "format": "json",
                "options": {"temperature": 0},
            },
        )
        try:
            data = json.loads(response["response"])
            if not isinstance(data, dict):
                raise LLMResponseError("LLM JSON response must be an object")
            result = LLMFieldResult.model_validate(data)
        except (KeyError, TypeError, json.JSONDecodeError, ValidationError) as error:
            raise LLMResponseError(f"Invalid LLM field response: {error}") from error
        if result.field != field:
            raise LLMResponseError("LLM returned a different field name")
        if result.value is None:
            return result
        page = next((page for page in pages if page["page_number"] == result.page_number), None)
        if page is None or not result.evidence or result.evidence not in page["text"]:
            raise LLMResponseError("LLM evidence is not present on the claimed PDF page")
        return result
