import re
import unicodedata

from app.ai.knowledge.interfaces.interfaces import Normalizer


class WhitespaceNormalizer(Normalizer):
    async def normalize(self, content: str) -> str:
        text = re.sub(r"\r\n", "\n", content)
        text = re.sub(r"\r", "\n", text)
        text = re.sub(r"\t", " ", text)
        text = re.sub(r" +", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()


class UnicodeNormalizer(Normalizer):
    async def normalize(self, content: str) -> str:
        text = unicodedata.normalize("NFKC", content)
        return text


class QuoteNormalizer(Normalizer):
    async def normalize(self, content: str) -> str:
        text = content.replace("\u2018", "'").replace("\u2019", "'")
        text = text.replace("\u201c", '"').replace("\u201d", '"')
        text = text.replace("\u2013", "-").replace("\u2014", "--")
        text = text.replace("\u2026", "...")
        return text


class NumberingNormalizer(Normalizer):
    async def normalize(self, content: str) -> str:
        text = re.sub(r"^\s*[\d]+[\.\)]\s*", "", content, flags=re.MULTILINE)
        text = re.sub(r"^\s*[\-\*\+]\s+", "", content, flags=re.MULTILINE)
        return text


class CompositeNormalizer(Normalizer):
    def __init__(self, normalizers: list[Normalizer] | None = None):
        self._normalizers = normalizers or [
            WhitespaceNormalizer(),
            UnicodeNormalizer(),
            QuoteNormalizer(),
        ]

    async def normalize(self, content: str) -> str:
        result = content
        for normalizer in self._normalizers:
            result = await normalizer.normalize(result)
        return result
