import re

from app.ai.assistant.interfaces.interfaces import ResponseFormatterABC
from app.ai.assistant.schemas.schemas import ChatResponse, PersonalizationPreferences


class ResponseFormatter(ResponseFormatterABC):

    async def format_chat_response(self, response: ChatResponse, preferences: PersonalizationPreferences | None = None) -> str:
        parts = []

        if response.has_emergency and response.emergency_message:
            parts.append(response.emergency_message)
            parts.append("")

        parts.append(response.message)

        if response.key_takeaways:
            parts.append("")
            parts.append("**Key Takeaways:**")
            for i, t in enumerate(response.key_takeaways, 1):
                parts.append(f"{i}. {t}")

        if response.recommended_actions:
            parts.append("")
            parts.append("**Recommended Actions:**")
            for i, a in enumerate(response.recommended_actions, 1):
                parts.append(f"{i}. {a}")

        if response.citations:
            parts.append("")
            parts.append("**References:**")
            for i, c in enumerate(response.citations, 1):
                source = c.get("source", c.get("title", f"Source {i}"))
                parts.append(f"[{i}] {source}")

        if response.disclaimers:
            for d in response.disclaimers:
                parts.append("")
                parts.append(f"*{d}*")

        if response.follow_up_questions:
            parts.append("")
            parts.append("**You may also ask:**")
            for q in response.follow_up_questions:
                parts.append(f"- {q}")

        return "\n".join(parts)

    async def format_markdown(self, text: str, audience: str = "patient") -> str:
        text = re.sub(r"\*\*(.*?)\*\*", r"**\1**", text)
        text = re.sub(r"### (.*?)\n", r"### \1\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    async def extract_key_takeaways(self, text: str, max_items: int = 5) -> list[str]:
        takeaways = []
        lines = text.split("\n")
        in_takeaway = False
        for line in lines:
            stripped = line.strip()
            if stripped.lower().startswith(("key takeaway", "takeaway", "important point", "key point")):
                in_takeaway = True
                content = re.sub(r"^[^:]*:\s*", "", stripped)
                if content:
                    takeaways.append(content)
                continue
            if in_takeaway and stripped.startswith(("- ", "* ", "1. ", "2.")):
                content = re.sub(r"^[-*]\s*|\d+\.\s*", "", stripped)
                if content:
                    takeaways.append(content)
                continue
            if stripped and not stripped.startswith(("-", "*", "1.", "2.")):
                in_takeaway = False
            if len(takeaways) >= max_items:
                break
        return takeaways

    async def generate_follow_up_questions(self, text: str, max_questions: int = 3) -> list[str]:
        questions = []
        lines = text.split("\n")
        in_questions = False
        for line in lines:
            stripped = line.strip()
            if stripped.lower().startswith(("you may also ask", "follow-up", "related question")):
                in_questions = True
                continue
            if in_questions and stripped.startswith(("- ", "* ")):
                q = stripped[2:].strip().rstrip("?") + "?"
                questions.append(q)
                continue
            if stripped and not stripped.startswith(("-", "*")):
                in_questions = False
            if len(questions) >= max_questions:
                break
        if not questions:
            sentences = text.replace("! ", "!||").replace("? ", "?||").replace(". ", ".||")
            parts = sentences.split("||")
            for p in parts[-5:]:
                if "?" in p:
                    questions.append(p.strip())
                    if len(questions) >= max_questions:
                        break
        return questions

    async def generate_recommended_actions(self, text: str, max_actions: int = 3) -> list[str]:
        actions = []
        lines = text.split("\n")
        in_actions = False
        for line in lines:
            stripped = line.strip()
            if stripped.lower().startswith(("recommended action", "recommendation", "you should", "consider")):
                in_actions = True
                content = re.sub(r"^[^:]*:\s*", "", stripped)
                if content:
                    actions.append(content)
                continue
            if in_actions and stripped.startswith(("- ", "* ", "1. ", "2.")):
                content = re.sub(r"^[-*]\s*|\d+\.\s*", "", stripped)
                if content:
                    actions.append(content)
                continue
            if stripped and not stripped.startswith(("-", "*", "1.", "2.")):
                in_actions = False
            if len(actions) >= max_actions:
                break
        return actions

    async def simplify_for_audience(self, text: str, audience: str) -> str:
        if audience == "patient":
            replacements = {
                " administer": " give",
                " contraindicated": " should not be used",
                " contraindication": " reason not to use",
                " adverse effect": " side effect",
                " adverse event": " side effect",
                " efficacy": " how well it works",
                " mortality": " death rate",
                " morbidity": " illness rate",
                " etiology": " cause",
                " pathogenesis": " how it develops",
                " prognosis": " likely outcome",
                " idiopathic": " unknown cause",
                " asymptomatic": " no symptoms",
                " acute": " sudden and severe",
                " chronic": " long-term",
                " benign": " non-cancerous",
                " malignant": " cancerous",
            }
            for medical, plain in replacements.items():
                text = text.replace(medical, plain)
        return text
