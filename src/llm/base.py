from abc import ABC, abstractmethod
from dataclasses import dataclass, asdict


@dataclass
class LLMFieldResult:
    field: str
    value: object | None
    confidence: float
    evidence: str
    reason: str

    def to_dict(self): return asdict(self)


class LLMProvider(ABC):
    @abstractmethod
    def extract_field(self, field: str, context: str) -> LLMFieldResult: ...

    @abstractmethod
    def health_check(self) -> bool: ...
