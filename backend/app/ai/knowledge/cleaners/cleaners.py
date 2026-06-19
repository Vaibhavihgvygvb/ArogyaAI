import re

from app.ai.knowledge.interfaces.interfaces import Cleaner


class BoilerplateRemover(Cleaner):
    _patterns = [
        r"(?i)copyright\s+©?\s*\d{4}.*?(?:\n|$)",
        r"(?i)all rights reserved\.?",
        r"(?i)confidentiality\s+notice.*?(?:\n|$)",
        r"(?i)this\s+(document|message)\s+(is|contains).*?(?:\n|$)",
        r"(?i)disclaimer:.*?(?:\n|$)",
        r"(?i)powered\s+by\s+\w+.*?(?:\n|$)",
        r"_{3,}",
        r"={3,}",
    ]

    async def clean(self, content: str) -> str:
        result = content
        for pattern in self._patterns:
            result = re.sub(pattern, "", result)
        return result.strip()


class HeaderFooterStripper(Cleaner):
    async def clean(self, content: str) -> str:
        lines = content.split("\n")
        if len(lines) <= 6:
            return content
        body = lines[3:-3] if len(lines) > 6 else lines
        return "\n".join(body).strip()


class CompositeCleaner(Cleaner):
    def __init__(self, cleaners: list[Cleaner] | None = None):
        self._cleaners = cleaners or [
            BoilerplateRemover(),
            HeaderFooterStripper(),
        ]

    async def clean(self, content: str) -> str:
        result = content
        for cleaner in self._cleaners:
            result = await cleaner.clean(result)
        return result
