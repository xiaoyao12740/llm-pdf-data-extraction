from abc import ABC, abstractmethod

from pydantic import BaseModel, ConfigDict, Field, StrictFloat, StrictInt, StrictStr


class LLMFieldResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    field: str
    value: StrictStr | StrictInt | StrictFloat | None
    confidence: float = Field(ge=0, le=1)
    page_number: int | None = Field(default=None, ge=1)
    evidence: str = ""
    reason: str = ""


class LLMProvider(ABC):
    @abstractmethod
    def extract_field(self, field: str, pages: list[dict]) -> LLMFieldResult: ...

    @abstractmethod
    def health_check(self) -> bool: ...
