import re

from app.ai.clinical_safety.exceptions import HallucinationDetectionError
from app.ai.clinical_safety.interfaces.hallucination import HallucinationDetector
from app.ai.clinical_safety.schemas import (
    HallucinationReport,
    HallucinationResult,
    HallucinationType,
)


class DefaultHallucinationDetector(HallucinationDetector):

    KNOWN_MEDICATIONS = frozenset({
        "aspirin", "metformin", "amoxicillin", "lisinopril", "omeprazole",
        "atorvastatin", "metoprolol", "albuterol", "levothyroxine", "losartan",
        "gabapentin", "pantoprazole", "sertraline", "cetirizine", "ibuprofen",
        "paracetamol", "salbutamol", "insulin", "warfarin", "prednisolone",
    })

    KNOWN_DISEASES = frozenset({
        "diabetes", "hypertension", "asthma", "copd", "cancer",
        "pneumonia", "tuberculosis", "malaria", "hiv", "hepatitis",
        "arthritis", "depression", "anxiety", "stroke",
    })

    KNOWN_MULTI_WORD_DISEASES = frozenset({
        "heart disease",
    })

    DRUG_SUFFIX_PATTERNS: list[tuple[re.Pattern, float]] = [
        (re.compile(r'(umab|imab|mab|zumab|ximab)$', re.IGNORECASE), 0.9),
        (re.compile(r'(tinib|ciclib|parib)$', re.IGNORECASE), 0.85),
        (re.compile(r'(pril|sartan|vastatin)$', re.IGNORECASE), 0.85),
        (re.compile(r'(cillin|mycin|oxacin)$', re.IGNORECASE), 0.85),
        (re.compile(r'(prazole|tidine)$', re.IGNORECASE), 0.8),
        (re.compile(r'(vir|navir)$', re.IGNORECASE), 0.8),
        (re.compile(r'(olol|dipine)$', re.IGNORECASE), 0.8),
        (re.compile(r'(dronate|caine|profen|coxib)$', re.IGNORECASE), 0.8),
        (re.compile(r'(gliptin|gliflozin|lukast)$', re.IGNORECASE), 0.8),
        (re.compile(r'(thiazide|asone|semide)$', re.IGNORECASE), 0.7),
    ]

    CITATION_RE = re.compile(
        r'\[(\d+)\]|\([A-Z][a-z]+ et al\.\s*\d{4}\)|\([A-Z][a-z]+,\s*\d{4}\)'
    )
    GUIDELINE_RE = re.compile(
        r'\b(guideline|protocol|standard of care|recommends|clinical practice guideline)\b',
        re.IGNORECASE,
    )
    STATISTIC_RE = re.compile(
        r'\b\d+%|\b\d+\s+in\s+\d+\b|\b\d+\s+out\s+of\s+\d+\b'
    )
    RECOMMENDATION_RE = re.compile(
        r'\b(should|recommend|advise|prescribe|ought to)\b',
        re.IGNORECASE,
    )
    SENTENCE_RE = re.compile(r'(?<=[.!?])\s+')
    CLAIM_INDICATOR_RE = re.compile(
        r'\b(causes?|treats?|prevents?|diagnoses?|increases?|decreases?|'
        r'reduces?|improves?|is|are|was|were|has|have|had|contains?|'
        r'leads?\s*to|results?\s*in|associated\s*with|linked\s*to|effective|'
        r'safe|dangerous|contraindicated|indicated|studies?\s*show|'
        r'research\s*suggests|evidence\s*indicates)\b',
        re.IGNORECASE,
    )
    WORD_RE = re.compile(r'\b[a-zA-Z]+\b')
    DISEASE_MULTI_RE = re.compile(r'\bheart\s+disease\b', re.IGNORECASE)

    def __init__(self, config=None):
        self.max_claims = getattr(config, 'CLINICAL_SAFETY_MAX_CLAIMS', 100) if config else 100

    async def detect(
        self,
        text: str,
        claims: list[str],
        evidence: dict | None = None,
    ) -> HallucinationReport:
        try:
            if not claims and text:
                claims = self._extract_claims(text)

            if not claims:
                return HallucinationReport(
                    results=[], total_claims=0, hallucinated_count=0,
                    hallucination_rate=0.0, passed=True,
                    summary="No claims to analyze.",
                )

            claims = claims[:self.max_claims]
            results: list[HallucinationResult] = []

            for claim in claims:
                result = self._analyze_claim(claim, evidence)
                if result is not None:
                    results.append(result)

            total = len(results)
            hallucinated_count = sum(
                1 for r in results
                if r.hallucination_type not in (
                    HallucinationType.UNSUPPORTED_CLAIM,
                    HallucinationType.UNKNOWN,
                )
            )
            rate = hallucinated_count / total if total > 0 else 0.0

            return HallucinationReport(
                results=results,
                total_claims=total,
                hallucinated_count=hallucinated_count,
                hallucination_rate=rate,
                passed=rate < 0.5,
                summary=(
                    f"Found {hallucinated_count}/{total} potentially hallucinated "
                    f"claims (rate: {rate:.1%})."
                ),
            )
        except Exception as e:
            raise HallucinationDetectionError(
                f"Hallucination detection failed: {e}"
            ) from e

    def _extract_claims(self, text: str) -> list[str]:
        sentences = self.SENTENCE_RE.split(text)
        return [
            s.strip() for s in sentences
            if self.CLAIM_INDICATOR_RE.search(s) and len(s.strip()) > 10
        ]

    def _analyze_claim(
        self,
        claim: str,
        evidence: dict | None,
    ) -> HallucinationResult | None:
        claim_lower = claim.lower()

        citations = self.CITATION_RE.findall(claim)
        if citations:
            if evidence is None or not evidence:
                return HallucinationResult(
                    claim=claim,
                    hallucination_type=HallucinationType.FABRICATED_CITATION,
                    confidence=0.8,
                    evidence_snippet=str(citations[:3]),
                    details="Citation found but no evidence provided to verify.",
                    span_start=0,
                    span_end=len(claim),
                )
            if not self._verify_citations(citations, evidence):
                return HallucinationResult(
                    claim=claim,
                    hallucination_type=HallucinationType.FABRICATED_CITATION,
                    confidence=0.7,
                    evidence_snippet=str(citations[:3]),
                    details="Citation could not be verified against provided evidence.",
                    span_start=0,
                    span_end=len(claim),
                )

        medications = self._find_medications(claim_lower)
        for med in medications:
            if med not in self.KNOWN_MEDICATIONS:
                confidence = self._assess_drug_likeness(med)
                return HallucinationResult(
                    claim=claim,
                    hallucination_type=HallucinationType.FABRICATED_MEDICATION,
                    confidence=min(0.9, confidence),
                    evidence_snippet=med,
                    details=f"Medication '{med}' is not in the known medications list.",
                    span_start=0,
                    span_end=len(claim),
                )

        diseases = self._find_diseases(claim_lower)
        for disease in diseases:
            if (
                disease not in self.KNOWN_DISEASES
                and disease not in self.KNOWN_MULTI_WORD_DISEASES
            ):
                return HallucinationResult(
                    claim=claim,
                    hallucination_type=HallucinationType.FABRICATED_DISEASE,
                    confidence=0.75,
                    evidence_snippet=disease,
                    details=f"Disease '{disease}' is not in the known diseases list.",
                    span_start=0,
                    span_end=len(claim),
                )

        if self.GUIDELINE_RE.search(claim) and not self._claim_supported_by_evidence(
            claim, evidence
        ):
            return HallucinationResult(
                claim=claim,
                hallucination_type=HallucinationType.FABRICATED_GUIDELINE,
                confidence=0.7,
                details="Guideline reference found but no supporting evidence.",
                span_start=0,
                span_end=len(claim),
            )

        if self.STATISTIC_RE.search(claim) and not self._claim_supported_by_evidence(
            claim, evidence
        ):
            return HallucinationResult(
                claim=claim,
                hallucination_type=HallucinationType.FABRICATED_STATISTIC,
                confidence=0.6,
                details="Statistical claim found but could not be verified.",
                span_start=0,
                span_end=len(claim),
            )

        if self.RECOMMENDATION_RE.search(
            claim
        ) and not self._claim_supported_by_evidence(claim, evidence):
            return HallucinationResult(
                claim=claim,
                hallucination_type=HallucinationType.FABRICATED_RECOMMENDATION,
                confidence=0.5,
                details="Recommendation found but no supporting evidence.",
                span_start=0,
                span_end=len(claim),
            )

        if not self._claim_supported_by_evidence(claim, evidence):
            return HallucinationResult(
                claim=claim,
                hallucination_type=HallucinationType.UNSUPPORTED_CLAIM,
                confidence=0.4,
                details="Claim appears unsupported by provided evidence.",
                span_start=0,
                span_end=len(claim),
            )

        return None

    def _find_medications(self, text: str) -> set[str]:
        words = set(m.group().lower() for m in self.WORD_RE.finditer(text))
        meds: set[str] = set()
        for w in words:
            if w in self.KNOWN_MEDICATIONS:
                meds.add(w)
            elif len(w) > 4:
                for pattern, _ in self.DRUG_SUFFIX_PATTERNS:
                    if pattern.search(w):
                        meds.add(w)
                        break
        return meds

    def _find_diseases(self, text: str) -> set[str]:
        words = set(m.group().lower() for m in self.WORD_RE.finditer(text))
        diseases: set[str] = set()
        for w in words:
            if w in self.KNOWN_DISEASES:
                diseases.add(w)
        multi_matches = self.DISEASE_MULTI_RE.findall(text)
        diseases.update(m.lower() for m in multi_matches)
        return diseases

    def _assess_drug_likeness(self, name: str) -> float:
        for pattern, score in self.DRUG_SUFFIX_PATTERNS:
            if pattern.search(name):
                return score
        return 0.3

    @staticmethod
    def _verify_citations(citations: list, evidence: dict) -> bool:
        for citation in citations:
            citation_str = (
                " ".join(str(c) for c in citation)
                if isinstance(citation, tuple)
                else str(citation)
            )
            found = any(citation_str.lower() in key.lower() for key in evidence)
            if not found:
                return False
        return True

    @staticmethod
    def _claim_supported_by_evidence(claim: str, evidence: dict | None) -> bool:
        if evidence is None or not evidence:
            return False
        claim_lower = claim.lower()
        claim_words = set(re.findall(r'\b[a-zA-Z]+\b', claim_lower))
        for key in evidence:
            key_words = set(re.findall(r'\b[a-zA-Z]+\b', key.lower()))
            if len(claim_words & key_words) >= min(3, len(claim_words)):
                return True
        return False
