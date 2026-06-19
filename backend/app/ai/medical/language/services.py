import re
from app.ai.medical.engine.schemas import LanguageInfo


_ABBREVIATIONS_SET = {
    "sob", "cva", "mi", "htn", "dm", "copd", "uti", "gi", "gu", "cxr",
    "ekg", "ecg", "lft", "bmp", "cbc", "bp", "hr", "rr", "tbi", "cabg",
    "dvt", "pe", "tia", "sbo", "oed", "pvd", "aro", "ibd", "ibs", "ckd",
    "afib", "pid", "uri", "cvd", "pad", "gerd",
}

_INFORMAL_PATTERNS = [
    r"\b(gonna|wanna|gotta|ain't|yeah|nah|kinda|sorta)\b",
    r"\b(doc|meds|physio|psych)\b",
]

_TYPO_INDICATORS = [
    r"(.)\1{2,}",  # repeated chars like "reeeally"
    r"\b[a-z]{1,2}\b",  # very short words typically not medical
]


class LanguageDetector:
    def detect(self, query: str) -> LanguageInfo:
        query_lower = query.lower()
        words = re.findall(r'\b[a-zA-Z]+\b', query_lower)

        abbreviations_found = [w for w in words if w in _ABBREVIATIONS_SET]
        acronyms_found = [w for w in words if len(w) >= 2 and w.isupper() and w not in _ABBREVIATIONS_SET]
        informal = any(re.search(p, query_lower) for p in _INFORMAL_PATTERNS)
        typos = any(re.search(p, query_lower) for p in _TYPO_INDICATORS)

        normalized = query
        for abbr in abbreviations_found:
            normalized = re.sub(r'\b' + abbr + r'\b', abbr.upper(), normalized, flags=re.IGNORECASE)

        return LanguageInfo(
            language="en",
            confidence=0.95,
            has_abbreviations=len(abbreviations_found) > 0,
            has_acronyms=len(acronyms_found) > 0,
            has_informal_phrasing=informal,
            has_typos=typos,
            normalized_query=normalized,
            detected_abbreviations=abbreviations_found,
            detected_acronyms=acronyms_found,
        )
