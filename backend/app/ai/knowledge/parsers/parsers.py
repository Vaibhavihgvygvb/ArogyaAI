import re

from app.ai.knowledge.interfaces.interfaces import Parser
from app.ai.knowledge.schemas.schemas import DocumentFormat


class DocumentParser(Parser):
    async def parse(self, content: str, format: DocumentFormat) -> str:
        return content.strip()

    async def extract_headings(self, content: str) -> list[tuple[str, int]]:
        headings: list[tuple[str, int]] = []
        lines = content.split("\n")
        for i, line in enumerate(lines):
            stripped = line.strip()
            if stripped.startswith("#") and stripped.replace("#", "").strip():
                level = len(stripped) - len(stripped.lstrip("#"))
                heading_text = stripped.lstrip("#").strip()
                if heading_text:
                    headings.append((heading_text, i))
            elif re.match(r"^[A-Z][A-Za-z\s]+$", stripped) and len(stripped) > 3:
                if i + 1 < len(lines) and re.match(r"^[-=]+\s*$", lines[i + 1]):
                    headings.append((stripped, i))
        return headings

    async def extract_paragraphs(self, content: str) -> list[str]:
        paragraphs = re.split(r"\n\s*\n", content.strip())
        return [p.strip() for p in paragraphs if p.strip()]
