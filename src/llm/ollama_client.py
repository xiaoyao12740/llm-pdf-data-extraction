import json
from urllib.error import URLError
from urllib.request import Request, urlopen
from .base import LLMFieldResult, LLMProvider
from .prompts import field_prompt


class OllamaClient(LLMProvider):
    def __init__(self, model="qwen2.5:7b", base_url="http://localhost:11434", timeout=120):
        self.model=model; self.base_url=base_url.rstrip("/"); self.timeout=timeout

    def _request(self, endpoint, payload=None):
        body=None if payload is None else json.dumps(payload).encode()
        request=Request(self.base_url+endpoint,data=body,headers={"Content-Type":"application/json"})
        with urlopen(request,timeout=self.timeout) as response: return json.loads(response.read())

    def health_check(self):
        try: return isinstance(self._request("/api/tags").get("models"),list)
        except (OSError,URLError,ValueError): return False

    def extract_field(self, field, context):
        response=self._request("/api/generate",{"model":self.model,"prompt":field_prompt(field,context),"stream":False,"format":"json","options":{"temperature":0}})
        data=json.loads(response["response"]); result=LLMFieldResult(field,data.get("value"),float(data.get("confidence",0)),str(data.get("evidence","")).strip(),str(data.get("reason","")).strip())
        if result.value is not None and (not result.evidence or result.evidence not in context): raise ValueError("LLM evidence is not present in supplied context")
        return result
