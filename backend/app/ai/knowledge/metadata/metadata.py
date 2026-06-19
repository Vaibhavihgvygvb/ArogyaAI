import os
import re

from app.ai.knowledge.interfaces.interfaces import MetadataExtractor
from app.ai.knowledge.schemas.schemas import DocumentMetadata


class DefaultMetadataExtractor(MetadataExtractor):
    async def extract(self, content: str, filename: str) -> DocumentMetadata:
        title = self._extract_title(content, filename)
        author = self._extract_author(content)
        specialty = self._extract_specialty(content)
        tags = self._extract_tags(content, filename)
        language = self._detect_language(content)
        word_count = len(content.split())
        char_count = len(content)
        return DocumentMetadata(
            title=title,
            author=author,
            specialty=specialty,
            tags=tags,
            language=language,
            word_count=word_count,
            char_count=char_count,
        )

    def _extract_title(self, content: str, filename: str) -> str:
        lines = content.strip().split("\n")
        for line in lines[:20]:
            stripped = line.strip()
            if stripped.startswith("#"):
                return stripped.lstrip("#").strip()
            if stripped.startswith("Title:"):
                return stripped.replace("Title:", "", 1).strip()
        base = os.path.splitext(os.path.basename(filename))[0]
        return base.replace("_", " ").replace("-", " ").title()

    def _extract_author(self, content: str) -> str:
        lines = content.strip().split("\n")[:30]
        for line in lines:
            stripped = line.strip()
            if stripped.lower().startswith("author:"):
                return stripped.replace("Author:", "", 1).strip()
            if stripped.lower().startswith("by "):
                return stripped[3:].strip()
        return ""

    def _extract_specialty(self, content: str) -> str:
        specialties = [
            "cardiology", "neurology", "psychiatry", "pediatrics",
            "oncology", "orthopedics", "dermatology", "ophthalmology",
            "radiology", "surgery", "internal medicine", "family medicine",
            "emergency medicine", "anesthesiology", "pathology",
        ]
        lower = content.lower()
        found = []
        for spec in specialties:
            if spec in lower:
                found.append(spec)
        return found[0] if found else ""

    def _extract_tags(self, content: str, filename: str) -> list[str]:
        tags: list[str] = []
        lines = content.strip().split("\n")[:50]
        for line in lines:
            stripped = line.strip()
            if stripped.lower().startswith("tags:"):
                tag_part = stripped.replace("Tags:", "", 1).replace("tags:", "", 1)
                tags = [t.strip() for t in tag_part.split(",") if t.strip()]
                break
        if not tags:
            base = os.path.splitext(os.path.basename(filename))[0]
            tags = [base.replace("_", " ").replace("-", " ").lower()]
        return tags

    def _detect_language(self, content: str) -> str:
        common_english = {"the", "is", "and", "of", "in", "to", "with", "for", "on", "this"}
        words = set(content.lower().split())
        overlap = len(words & common_english)
        if overlap > 3:
            return "en"
        return ""
