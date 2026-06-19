from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class SafetyResult:
    passed: bool
    score: float
    reason: str | None = None
    details: dict | None = None


class SafetyService(ABC):

    @abstractmethod
    async def validate_input(self, text: str) -> SafetyResult:
        ...

    @abstractmethod
    async def detect_prompt_injection(self, text: str) -> SafetyResult:
        ...

    @abstractmethod
    async def detect_phi(self, text: str) -> SafetyResult:
        ...

    @abstractmethod
    async def validate_output(self, text: str) -> SafetyResult:
        ...

    @abstractmethod
    async def check_safety(self, text: str) -> SafetyResult:
        ...
