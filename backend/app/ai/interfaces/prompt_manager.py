from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class PromptTemplate:
    name: str
    version: str
    system_prompt: str
    template: str
    variables: list[str]
    description: str
    tags: list[str] | None = None
    model: str | None = None


class PromptManager(ABC):

    @abstractmethod
    async def get_prompt(self, name: str, version: str | None = None) -> PromptTemplate:
        ...

    @abstractmethod
    async def register_prompt(self, prompt: PromptTemplate) -> None:
        ...

    @abstractmethod
    async def render_prompt(self, name: str, variables: dict, version: str | None = None) -> str:
        ...

    @abstractmethod
    async def list_prompts(self, tag: str | None = None) -> list[PromptTemplate]:
        ...
