from abc import ABC, abstractmethod

from app.ai.clinical_safety.schemas import PHIValidationReport


class PHIValidator(ABC):
    @abstractmethod
    async def validate(
        self,
        text: str,
    ) -> PHIValidationReport:
        ...
