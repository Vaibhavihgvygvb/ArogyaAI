import re
from app.ai.interfaces.safety_service import SafetyService, SafetyResult
from app.core.config import settings


class DefaultSafetyService(SafetyService):

    _PHI_PATTERNS: list[re.Pattern] = [
        re.compile(r"\b\d{3}-\d{2}-\d{4}\b"),
        re.compile(r"\b\d{3}\s*\d{2}\s*\d{4}\b"),
        re.compile(r"\b[A-Z]{2}\d{6}\b"),
        re.compile(r"\b\d{10}\b"),
        re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"),
        re.compile(r"\b(?:\+?91|0)?[6-9]\d{9}\b"),
        re.compile(r"\b\d{16}\b"),
    ]

    _INJECTION_PATTERNS: list[re.Pattern] = [
        re.compile(r"ignore\s+(all\s+)?(previous|above|prior)\s+instructions", re.IGNORECASE),
        re.compile(r"forget\s+(all\s+)?(previous|above|prior)", re.IGNORECASE),
        re.compile(r"you\s+are\s+(now|free|not\s+bound)", re.IGNORECASE),
        re.compile(r"system\s+prompt", re.IGNORECASE),
        re.compile(r"act\s+as\s+(if\s+you\s+are|though)", re.IGNORECASE),
        re.compile(r"bypass\s+(the\s+)?(rules|safety|guardrails)", re.IGNORECASE),
        re.compile(r"role\s*(play|playing)", re.IGNORECASE),
        re.compile(r"do\s+(not\s+)?(any|all|the)\s+(safety|filter|check)", re.IGNORECASE),
        re.compile(r"<\|[a-z]+\|>", re.IGNORECASE),
        re.compile(r"DAN|jailbreak|hypnosis", re.IGNORECASE),
    ]

    _DANGEROUS_KEYWORDS: list[re.Pattern] = [
        re.compile(r"how\s+to\s+(make|create|synthesize|manufacture)\s+(a\s+)?(bomb|weapon|explosive|poison|drug)", re.IGNORECASE),
        re.compile(r"suicide\s+(method|how|guide|way)", re.IGNORECASE),
        re.compile(r"self[- ]?harm\s+(method|how|guide)", re.IGNORECASE),
    ]

    async def validate_input(self, text: str) -> SafetyResult:
        if not text or not text.strip():
            return SafetyResult(passed=False, score=0.0, reason="Empty input")
        if len(text) > 100000:
            return SafetyResult(passed=False, score=0.0, reason="Input exceeds maximum length")
        return SafetyResult(passed=True, score=1.0)

    async def detect_prompt_injection(self, text: str) -> SafetyResult:
        if not settings.AI.SAFETY_ENABLED:
            return SafetyResult(passed=True, score=1.0)
        for pattern in self._INJECTION_PATTERNS:
            match = pattern.search(text)
            if match:
                return SafetyResult(
                    passed=False,
                    score=0.0,
                    reason=f"Prompt injection pattern detected: '{match.group()}'",
                    details={"matched_pattern": match.group(), "pattern_type": "injection"},
                )
        return SafetyResult(passed=True, score=1.0)

    async def detect_phi(self, text: str) -> SafetyResult:
        if not settings.AI.SAFETY_ENABLED:
            return SafetyResult(passed=True, score=1.0)
        matches = []
        for pattern in self._PHI_PATTERNS:
            match = pattern.search(text)
            if match:
                matches.append(match.group())
        if matches:
            return SafetyResult(
                passed=False,
                score=0.0,
                reason=f"Potential PHI detected",
                details={"matched_patterns": matches, "phi_type": "identifier"},
            )
        return SafetyResult(passed=True, score=1.0)

    async def validate_output(self, text: str) -> SafetyResult:
        if not text:
            return SafetyResult(passed=False, score=0.0, reason="Empty output")
        if len(text) > 100000:
            return SafetyResult(passed=False, score=0.0, reason="Output exceeds maximum length")
        for pattern in self._DANGEROUS_KEYWORDS:
            match = pattern.search(text)
            if match:
                return SafetyResult(
                    passed=False,
                    score=0.0,
                    reason=f"Dangerous content detected",
                    details={"matched_pattern": match.group(), "pattern_type": "dangerous"},
                )
        return SafetyResult(passed=True, score=1.0)

    async def check_safety(self, text: str) -> SafetyResult:
        for check in [self.validate_input, self.detect_prompt_injection, self.detect_phi]:
            result = await check(text)
            if not result.passed:
                return result
        return SafetyResult(passed=True, score=1.0)
