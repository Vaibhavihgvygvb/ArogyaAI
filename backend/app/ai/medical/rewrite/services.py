from app.ai.medical.rewrite.interfaces import QueryRewriterABC
from app.ai.medical.engine.schemas import RewriteResult
import re


_ABBREVIATIONS: dict[str, str] = {
    "sob": "shortness of breath",
    "cva": "cerebrovascular accident",
    "mi": "myocardial infarction",
    "htn": "hypertension",
    "dm": "diabetes mellitus",
    "copd": "chronic obstructive pulmonary disease",
    "uti": "urinary tract infection",
    "gi": "gastrointestinal",
    "gu": "genitourinary",
    "cxr": "chest x-ray",
    "ekg": "electrocardiogram",
    "ecg": "electrocardiogram",
    "lft": "liver function test",
    "bmp": "basic metabolic panel",
    "cbc": "complete blood count",
    "bp": "blood pressure",
    "hr": "heart rate",
    "rr": "respiratory rate",
    "tbi": "traumatic brain injury",
    "cabg": "coronary artery bypass graft",
    "dvt": "deep vein thrombosis",
    "pe": "pulmonary embolism",
    "tia": "transient ischemic attack",
    "sbo": "small bowel obstruction",
    "oed": "occupational exposure dose",
    "pvd": "peripheral vascular disease",
    "aro": "acute renal obstruction",
    "ibd": "inflammatory bowel disease",
    "ibs": "irritable bowel syndrome",
    "ckd": "chronic kidney disease",
    "afib": "atrial fibrillation",
    "pid": "pelvic inflammatory disease",
    "uri": "upper respiratory infection",
    "cvd": "cardiovascular disease",
    "pad": "peripheral artery disease",
    "gerd": "gastroesophageal reflux disease",
}


class QueryRewriter(QueryRewriterABC):
    async def rewrite(self, query: str) -> RewriteResult:
        expansions, abbreviations_expanded, current_query = self._expand_abbreviations(query)
        return RewriteResult(
            original_query=query,
            rewritten_query=current_query,
            expansions=expansions,
            abbreviations_expanded=abbreviations_expanded,
            normalized=bool(abbreviations_expanded),
        )

    def _expand_abbreviations(self, query: str) -> tuple[list[str], list[str], str]:
        words = re.findall(r'\b[a-zA-Z]+\b', query)
        expanded_terms = []
        result = query
        for word in words:
            clean_word = word.lower().strip(".")
            if clean_word in _ABBREVIATIONS:
                expanded = _ABBREVIATIONS[clean_word]
                expanded_terms.append(f"{word} → {expanded}")
                result = re.sub(
                    r'\b' + re.escape(word) + r'\b',
                    f"{word} ({expanded})",
                    result,
                    count=1,
                    flags=re.IGNORECASE,
                )
        return [], expanded_terms, result
