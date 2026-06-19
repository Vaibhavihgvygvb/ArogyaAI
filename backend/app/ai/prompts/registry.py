from app.ai.interfaces.prompt_manager import PromptManager, PromptTemplate
from app.ai.exceptions.exceptions import PromptNotFoundError, PromptValidationError


class PromptRegistry(PromptManager):

    def __init__(self):
        self._prompts: dict[str, dict[str, PromptTemplate]] = {}

    async def get_prompt(self, name: str, version: str | None = None) -> PromptTemplate:
        versions = self._prompts.get(name)
        if not versions:
            raise PromptNotFoundError(f"Prompt '{name}' not found")
        if version:
            if version not in versions:
                raise PromptNotFoundError(f"Prompt '{name}' version '{version}' not found")
            return versions[version]
        latest = max(versions.keys(), key=lambda v: [int(x) for x in v.split(".")])
        return versions[latest]

    async def register_prompt(self, prompt: PromptTemplate) -> None:
        if not prompt.name or not prompt.template:
            raise PromptValidationError("Prompt must have a name and template")
        if not prompt.variables:
            from string import Formatter
            parsed = [fn for _, fn, _, _ in Formatter().parse(prompt.template) if fn is not None]
            prompt.variables = list(dict.fromkeys(parsed))
        if prompt.name not in self._prompts:
            self._prompts[prompt.name] = {}
        self._prompts[prompt.name][prompt.version] = prompt

    async def render_prompt(self, name: str, variables: dict, version: str | None = None) -> str:
        prompt = await self.get_prompt(name, version)
        missing = [v for v in prompt.variables if v not in variables]
        if missing:
            raise PromptValidationError(f"Missing variables: {', '.join(missing)}")
        content = prompt.template.format(**variables)
        if prompt.system_prompt:
            return f"{prompt.system_prompt}\n\n{content}"
        return content

    async def list_prompts(self, tag: str | None = None) -> list[PromptTemplate]:
        result = []
        for versions in self._prompts.values():
            for prompt in versions.values():
                if tag is None or (prompt.tags and tag in prompt.tags):
                    result.append(prompt)
        return result
