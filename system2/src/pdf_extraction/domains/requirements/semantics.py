from __future__ import annotations

from collections.abc import Iterable
import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


Language = Literal["en", "no"]
ModalityType = Literal[
    "obligation", "prohibition", "permission", "recommendation", "other"
]
ThresholdOperator = Literal[
    "lt", "lte", "eq", "gte", "gt", "range", "unspecified"
]


class SemanticModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SourceSpan(SemanticModel):
    """A lossless half-open character span into the supplied native text."""

    start: int = Field(ge=0)
    end: int = Field(gt=0)
    text: str = Field(min_length=1)


class LanguageEvidence(SemanticModel):
    span: SourceSpan
    language: Language
    cue_type: Literal["legal", "grammar"]
    weight: float = Field(gt=0)


class LanguageAssessment(SemanticModel):
    language: Language
    confidence: float = Field(ge=0, le=1)
    english_score: float = Field(ge=0)
    norwegian_score: float = Field(ge=0)
    evidence: list[LanguageEvidence] = Field(default_factory=list)
    ambiguous: bool = False
    method: Literal["explicit", "source_cues"] = "source_cues"


class ModalityCandidate(SemanticModel):
    span: SourceSpan
    modality_type: ModalityType
    negated: bool
    scope: SourceSpan | None = None
    ambiguous: bool = False
    flags: list[str] = Field(default_factory=list)


class NegationCandidate(SemanticModel):
    span: SourceSpan
    scope: SourceSpan | None = None
    ambiguous: bool = False


class ContextCandidate(SemanticModel):
    marker: SourceSpan
    clause: SourceSpan
    kind: Literal["condition", "exception", "exemption"]
    ambiguous: bool = False
    flags: list[str] = Field(default_factory=list)


class ThresholdCandidate(SemanticModel):
    span: SourceSpan
    operator: ThresholdOperator
    value: str
    normalized_value: float | str | None = None
    end_value: str | None = None
    normalized_end_value: float | None = None
    unit: str | None = None
    ambiguous: bool = False
    flags: list[str] = Field(default_factory=list)


class DateCandidate(SemanticModel):
    """A source-exact temporal window, distinct from a numeric threshold."""

    span: SourceSpan
    scope: SourceSpan | None = None
    ambiguous: bool = False
    flags: list[str] = Field(default_factory=list)


class CrossReferenceCandidate(SemanticModel):
    span: SourceSpan
    target: str
    reference_type: Literal[
        "section",
        "section_range",
        "chapter",
        "paragraph",
        "letter",
        "article",
        "appendix",
        "table",
    ]
    ambiguous: bool = False
    flags: list[str] = Field(default_factory=list)


class RequirementSemanticAnalysis(SemanticModel):
    """Source-faithful legal-semantic candidates from one Requirement string.

    Candidates are deliberately weaker than accepted Canonical fields. Every
    extracted string is backed by an exact character span, and uncertain
    interpretations stay visible through ``ambiguous`` and ``flags``.
    """

    source_text: str
    language: LanguageAssessment
    modalities: list[ModalityCandidate] = Field(default_factory=list)
    negations: list[NegationCandidate] = Field(default_factory=list)
    conditions: list[ContextCandidate] = Field(default_factory=list)
    exceptions: list[ContextCandidate] = Field(default_factory=list)
    exemptions: list[ContextCandidate] = Field(default_factory=list)
    thresholds: list[ThresholdCandidate] = Field(default_factory=list)
    dates: list[DateCandidate] = Field(default_factory=list)
    cross_references: list[CrossReferenceCandidate] = Field(default_factory=list)
    flags: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_source_spans(self) -> "RequirementSemanticAnalysis":
        for span in _all_spans(self):
            if span.end > len(self.source_text):
                raise ValueError("semantic span exceeds source text")
            if self.source_text[span.start : span.end] != span.text:
                raise ValueError("semantic span is not an exact source substring")
        return self


_EN_LANGUAGE_CUES: tuple[tuple[str, float, Literal["legal", "grammar"]], ...] = (
    (r"provided\s+that", 2.0, "legal"),
    (r"shall|must|should|unless", 2.0, "legal"),
    (r"section|chapter|paragraph|article|appendix", 1.5, "legal"),
    (r"may", 1.0, "legal"),
    (r"not|no|if|when|where|after|based\s+on|except", 0.75, "grammar"),
    (r"the|and|or", 0.25, "grammar"),
)
_NO_LANGUAGE_CUES: tuple[tuple[str, float, Literal["legal", "grammar"]], ...] = (
    (r"med\s+mindre", 2.0, "legal"),
    (r"skal|må|dersom|hvis|unntatt|kapittel|ledd|bokstav", 2.0, "legal"),
    (r"kan", 1.0, "legal"),
    (r"ikke|når", 1.25, "grammar"),
    (r"virksomheten|foretaket|og|eller|som|til", 0.25, "grammar"),
)

_EN_MODAL_RE = re.compile(
    r"\b(?:shall\s+not|must\s+not|may\s+not|should\s+not|"
    r"shall|must|may|should|needs?\s+to)\b",
    re.IGNORECASE,
)
_NO_MODAL_RE = re.compile(
    r"\b(?:skal\s+ikke|må\s+ikke|kan\s+ikke|skal|må|kan)\b",
    re.IGNORECASE,
)
_EN_NEGATION_RE = re.compile(r"\b(?:not|no)\b", re.IGNORECASE)
_NO_NEGATION_RE = re.compile(r"\bikke\b", re.IGNORECASE)
_EN_CONDITION_RE = re.compile(
    r"\b(?:in\s+cases\s+where|provided\s+that|in\s+the\s+event\s+of|only\s+if|based\s+on|"
    r"prior\s+to|after|until|if|when|where)\b",
    re.IGNORECASE,
)
_EN_APPLICABILITY_CONDITION_RE = re.compile(
    r"\bfor\b(?=\s+(?:farms?|sites?|operators?|facilities?|units?|entities?)\b"
    r"[^,;.\n]{0,120}\bwith\b[^,;.\n]{0,120}"
    r"(?:[<>≤≥]=?|at\s+least|at\s+most|more\s+than|less\s+than)\s*\d)",
    re.IGNORECASE,
)
_NO_CONDITION_RE = re.compile(r"\b(?:dersom|hvis|når)\b", re.IGNORECASE)
_EN_EXCEPTION_RE = re.compile(r"\b(?:unless|except)\b", re.IGNORECASE)
_NO_EXCEPTION_RE = re.compile(r"\b(?:med\s+mindre|unntatt)\b", re.IGNORECASE)
_EN_EXEMPTION_RE = re.compile(
    r"\b(?:(?:an?|the)\s+)?exemptions?\s+"
    r"(?:applies?|may\s+apply|is\s+(?:available|allowed|permitted))\b|"
    r"\b(?:is|are)\s+exempt(?:ed)?\b",
    re.IGNORECASE,
)

_EN_NUMBER_WORDS = {
    "zero": 0.0,
    "one": 1.0,
    "two": 2.0,
    "three": 3.0,
    "four": 4.0,
    "five": 5.0,
    "six": 6.0,
    "seven": 7.0,
    "eight": 8.0,
    "nine": 9.0,
    "ten": 10.0,
    "eleven": 11.0,
    "twelve": 12.0,
}
_NO_NUMBER_WORDS = {
    "null": 0.0,
    "én": 1.0,
    "en": 1.0,
    "ett": 1.0,
    "to": 2.0,
    "tre": 3.0,
    "fire": 4.0,
    "fem": 5.0,
    "seks": 6.0,
    "sju": 7.0,
    "syv": 7.0,
    "åtte": 8.0,
    "ni": 9.0,
    "ti": 10.0,
    "elleve": 11.0,
    "tolv": 12.0,
}
_NUMBER_WORDS = {**_EN_NUMBER_WORDS, **_NO_NUMBER_WORDS}
_NUMBER_WORD_PATTERN = "|".join(
    sorted((re.escape(value) for value in _NUMBER_WORDS), key=len, reverse=True)
)
_NUMBER_TOKEN = (
    rf"(?:\d+(?:[.,]\d+)?(?!\d|[.,]\d)|"
    rf"(?:{_NUMBER_WORD_PATTERN})(?![\w]))"
)
_KNOWN_UNIT_PATTERN = (
    r"(?:adverse\s+turnover\s+events?|harmful\s+algal\s+blooms?|"
    r"index\s+points?|lethal\s+incidents?|percentage\s+points?|"
    r"percent|prosent|%|days?|dager|hours?|timer|incidents?|mortalities|"
    r"weeks?|uker?|months?|måneder|years?|år|seconds?|sekunder|mg\s*/\s*l|mg\s+l-1|"
    r"kg\s*/\s*m(?:3|³)|kg|mg|[gG]|µg|μg|tonnes?|tons?|tonn|"
    r"kilomet(?:er|re)s?|km|centimet(?:er|re)s?|cm|millimet(?:er|re)s?|mm|"
    r"met(?:er|re)s?|m|lit(?:er|re)s?|liter|litre|ml|l|°\s*C|degrees?\s+Celsius)"
)
_KNOWN_UNIT_RE = re.compile(
    rf"\s*(?P<unit>{_KNOWN_UNIT_PATTERN})(?![\w])", re.IGNORECASE
)
_GENERIC_UNIT_RE = re.compile(r"\s+(?P<unit>[A-Za-zÀ-ÖØ-öø-ÿ][\w/-]*)")
_OF_UNIT_RE = re.compile(
    r"\s+of\s+(?:the\s+)?(?P<unit>incidents?|events?|cases?|items?)\b",
    re.IGNORECASE,
)
_STOP_UNITS = {
    "a",
    "an",
    "and",
    "at",
    "av",
    "eller",
    "enn",
    "for",
    "fra",
    "in",
    "med",
    "of",
    "og",
    "or",
    "som",
    "than",
    "the",
    "til",
    "to",
}

_RANGE_PATTERNS = (
    re.compile(
        rf"\b(?P<prefix>between)\s+(?P<first>{_NUMBER_TOKEN})\s+and\s+"
        rf"(?P<second>{_NUMBER_TOKEN})",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?P<prefix>mellom)\s+(?P<first>{_NUMBER_TOKEN})\s+og\s+"
        rf"(?P<second>{_NUMBER_TOKEN})",
        re.IGNORECASE,
    ),
    re.compile(
        rf"(?<![\w.])(?P<first>{_NUMBER_TOKEN})\s*[–—-]\s*"
        rf"(?P<second>{_NUMBER_TOKEN})",
        re.IGNORECASE,
    ),
)
_COMPARATIVE_RE = re.compile(
    rf"(?P<comparator>at\s+least|no\s+less\s+than|not\s+less\s+than|"
    rf"minimum\s+of|at\s+most|no\s+more\s+than|not\s+more\s+than|"
    rf"maximum\s+of|less\s+than|more\s+than|greater\s+than|equal\s+to|"
    rf"exactly|within|minst|ikke\s+mindre\s+enn|minimum\s+på|høyst|"
    rf"maksimalt|ikke\s+mer\s+enn|maksimum\s+på|mindre\s+enn|mer\s+enn|"
    rf"nøyaktig|innen|>=|=>|≤|<=|=<|≥|>|<|=)\s*"
    rf"(?P<value>{_NUMBER_TOKEN})",
    re.IGNORECASE,
)
_BARE_QUANTITY_RE = re.compile(
    rf"(?<![\w.])(?P<value>{_NUMBER_TOKEN})\s*"
    rf"(?P<unit>{_KNOWN_UNIT_PATTERN})(?![\w])",
    re.IGNORECASE,
)
_QUALITATIVE_LTE_RE = re.compile(
    r"\bat\s+or\s+below\s+(?:the\s+)?"
    r"(?P<value>[A-Za-z][A-Za-z-]*(?:\s+[A-Za-z][A-Za-z-]*){0,5}\s+"
    r"(?:Level|Limit|Threshold|Maximum))\b",
    re.IGNORECASE,
)
_EXACT_RATE_STEP_RE = re.compile(
    rf"\bwith\s+(?P<value>{_NUMBER_TOKEN})\s*(?P<unit>%|percent|prosent)"
    rf"(?=\s+per\s+{_NUMBER_TOKEN}\s+(?:days?|weeks?|months?|years?))",
    re.IGNORECASE,
)
_DATE_PATTERNS = (
    re.compile(
        rf"\bfor\s+(?:the\s+)?first\s+{_NUMBER_TOKEN}\s+"
        rf"(?:days?|weeks?|months?|years?)\b"
        rf"(?:\s+of\s+[^,;.\n]+)?",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?:over|within)\s+(?:(?:the|any)\s+)?"
        rf"(?:(?:rolling|previous|past|prior)\s+)?"
        rf"{_NUMBER_TOKEN}(?:\s*-\s*|\s+)(?:months?|years?)\b"
        rf"(?:\s+period\b)?",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:"
        r"each\s+of\s+(?:the\s+)?(?:previous|prior)\s+"
        r"(?:\d+|one|two|three|four|five)\s+production\s+cycles|"
        r"(?:during|for|over)\s+(?:the\s+most\s+recent|each|the)\s+"
        r"(?:complete\s+)?production\s+cycles?|"
        r"the\s+most\s+recent\s+(?:complete\s+)?production\s+cycle"
        r")\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\bper\s+{_NUMBER_TOKEN}\s+(?:days?|weeks?|months?|years?)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\b(?:annual\s+targets?|annually|yearly|monthly|weekly|daily|quarterly)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bbefore\s+(?:prescribing|reporting|submitting|sampling|monitoring)\b"
        r"(?:\s+[A-Za-z-]+){0,3}",
        re.IGNORECASE,
    ),
)
_SOURCE_FIELD_LABEL_RE = re.compile(
    r"(?<![\w])(?:Indicator|Requirement|Applicability|Scope|Note|Footnote)\s*:",
    re.IGNORECASE,
)

_NORWEGIAN_SECTION_RE = re.compile(
    r"§{1,2}\s*\d+[A-Za-z]?(?:[-.]\d+[A-Za-z]?)*"
    r"(?:\s*(?:til|og)\s*(?:§{1,2}\s*)?\d+[A-Za-z]?(?:[-.]\d+[A-Za-z]?)*\s*)?"
    r"(?:\s+(?:første|andre|annet|tredje|fjerde|femte|\d+\.)\s+ledd)?"
    r"(?:\s+bokstav\s+[A-Za-z])?",
    re.IGNORECASE,
)
_LABELLED_REFERENCE_PATTERNS: tuple[
    tuple[re.Pattern[str], str], ...
] = (
    (
        re.compile(
            r"\bSections?\s+\d+(?:\.\d+)*(?:\s*(?:and|to|[–—-])\s*\d+(?:\.\d+)*)?",
            re.IGNORECASE,
        ),
        "section",
    ),
    (re.compile(r"\bChapters?\s+\d+(?:\.\d+)*", re.IGNORECASE), "chapter"),
    (re.compile(r"\bArticles?\s+\d+(?:\.\d+)*", re.IGNORECASE), "article"),
    (
        re.compile(
            r"\bAppendix\s+[A-Za-z0-9]+(?:\.[A-Za-z0-9]+)*"
            r"(?:\s*\(\d+(?:\.\d+)+(?:\s*(?:,|and|or)\s*\d+(?:\.\d+)+)*\))?",
            re.IGNORECASE,
        ),
        "appendix",
    ),
    (re.compile(r"\bTable\s+\d+(?:\.\d+)*", re.IGNORECASE), "table"),
    (
        re.compile(r"\bparagraph\s+\(?[A-Za-z0-9ivxIVX.]+\)?", re.IGNORECASE),
        "paragraph",
    ),
    (re.compile(r"\bkapittel\s+\d+(?:\.\d+)*", re.IGNORECASE), "chapter"),
    (
        re.compile(
            r"\b(?:første|andre|annet|tredje|fjerde|femte|dette|samme|"
            r"foregående|neste|\d+\.)\s+ledd"
            r"(?:\s+bokstav\s+[A-Za-z])?",
            re.IGNORECASE,
        ),
        "paragraph",
    ),
    (
        re.compile(
            r"\b(?:dette|samme|foregående|neste)\s+kapittel\b", re.IGNORECASE
        ),
        "chapter",
    ),
    (re.compile(r"\bbokstav\s+[A-Za-z]\b", re.IGNORECASE), "letter"),
)


def analyze_requirement_semantics(
    text: str,
    *,
    language: Language | None = None,
) -> RequirementSemanticAnalysis:
    """Extract deterministic English/Norwegian legal-semantic candidates.

    ``text`` is never normalized or rewritten. Passing ``language`` is useful
    when document-level routing has already established the language; without
    it, the function performs a transparent cue-based assessment.
    """

    assessment = assess_language(text, language=language)
    flags: list[str] = []
    if not text:
        flags.append("empty_source_text")
    if assessment.ambiguous:
        flags.append("ambiguous_language")

    active_languages: tuple[Language, ...]
    if language is not None or not assessment.ambiguous:
        active_languages = (assessment.language,)
    else:
        active_languages = ("en", "no")

    modalities = _modalities(text, active_languages, flags)
    negations = _negations(text, active_languages)
    conditions = _contexts(text, active_languages, kind="condition", flags=flags)
    exceptions = _contexts(text, active_languages, kind="exception", flags=flags)
    exemptions = _contexts(text, active_languages, kind="exemption", flags=flags)
    dates = _dates(text)
    thresholds = _thresholds(
        text,
        flags,
        languages=active_languages,
        excluded_spans=[(item.span.start, item.span.end) for item in dates],
    )
    cross_references = _cross_references(text, flags)

    return RequirementSemanticAnalysis(
        source_text=text,
        language=assessment,
        modalities=modalities,
        negations=negations,
        conditions=conditions,
        exceptions=exceptions,
        exemptions=exemptions,
        thresholds=thresholds,
        dates=dates,
        cross_references=cross_references,
        flags=_unique(flags),
    )


def assess_language(
    text: str,
    *,
    language: Language | None = None,
) -> LanguageAssessment:
    """Assess only English versus Norwegian using inspectable source cues."""

    evidence = _language_evidence(text)
    english_score = sum(item.weight for item in evidence if item.language == "en")
    norwegian_score = sum(item.weight for item in evidence if item.language == "no")
    if language is not None:
        return LanguageAssessment(
            language=language,
            confidence=1.0,
            english_score=english_score,
            norwegian_score=norwegian_score,
            evidence=evidence,
            ambiguous=False,
            method="explicit",
        )

    selected: Language = "no" if norwegian_score > english_score else "en"
    total = english_score + norwegian_score
    winner = max(english_score, norwegian_score)
    difference = abs(english_score - norwegian_score)
    ambiguous = winner < 2.0 or difference < max(1.0, total * 0.25)
    confidence = 0.5 if total == 0 else 0.5 + 0.5 * difference / total
    if ambiguous:
        confidence = min(confidence, 0.69)
    return LanguageAssessment(
        language=selected,
        confidence=round(confidence, 4),
        english_score=english_score,
        norwegian_score=norwegian_score,
        evidence=evidence,
        ambiguous=ambiguous,
    )


def _language_evidence(text: str) -> list[LanguageEvidence]:
    result: list[LanguageEvidence] = []
    occupied: dict[Language, list[tuple[int, int]]] = {"en": [], "no": []}
    for selected_language, cues in (("en", _EN_LANGUAGE_CUES), ("no", _NO_LANGUAGE_CUES)):
        for expression, weight, cue_type in cues:
            for match in re.finditer(rf"\b(?:{expression})\b", text, re.IGNORECASE):
                if selected_language == "en" and _is_calendar_may(text, match):
                    continue
                interval = (match.start(), match.end())
                if any(_overlaps(interval, prior) for prior in occupied[selected_language]):
                    continue
                occupied[selected_language].append(interval)
                result.append(
                    LanguageEvidence(
                        span=_span(text, *interval),
                        language=selected_language,
                        cue_type=cue_type,
                        weight=weight,
                    )
                )
    return sorted(result, key=lambda item: (item.span.start, item.span.end, item.language))


def _modalities(
    text: str,
    languages: Iterable[Language],
    flags: list[str],
) -> list[ModalityCandidate]:
    matches: list[tuple[re.Match[str], Language]] = []
    for language in languages:
        pattern = _EN_MODAL_RE if language == "en" else _NO_MODAL_RE
        matches.extend((match, language) for match in pattern.finditer(text))
    result: list[ModalityCandidate] = []
    for match, language in sorted(matches, key=lambda value: value[0].start()):
        if language == "en" and match.group(0).lower() == "may" and _is_calendar_may(text, match):
            flags.append(f"calendar_month_not_modality:{match.start()}")
            continue
        token = match.group(0).lower()
        negated = token.endswith(" not") or token.endswith(" ikke")
        base = token.rsplit(" ", 1)[0] if negated else token
        if negated:
            modality_type: ModalityType = "prohibition"
        elif base in {"shall", "must", "need to", "needs to", "skal", "må"}:
            modality_type = "obligation"
        elif base == "should":
            modality_type = "recommendation"
        elif base in {"may", "kan"}:
            modality_type = "permission"
        else:
            modality_type = "other"
        candidate_flags: list[str] = []
        ambiguous = base == "kan"
        if ambiguous:
            candidate_flags.append("kan_may_express_permission_or_capability")
        scope = _modality_scope(text, match.end(), language=language)
        if scope is None:
            candidate_flags.append("missing_modality_scope")
            flags.append(f"missing_modality_scope:{match.start()}")
        result.append(
            ModalityCandidate(
                span=_span(text, match.start(), match.end()),
                modality_type=modality_type,
                negated=negated,
                scope=scope,
                ambiguous=ambiguous,
                flags=candidate_flags,
            )
        )
    return _deduplicate_by_span(result)


def _negations(
    text: str,
    languages: Iterable[Language],
) -> list[NegationCandidate]:
    matches: list[re.Match[str]] = []
    for language in languages:
        pattern = _EN_NEGATION_RE if language == "en" else _NO_NEGATION_RE
        matches.extend(pattern.finditer(text))
    return _deduplicate_by_span(
        [
            NegationCandidate(
                span=_span(text, match.start(), match.end()),
                scope=_negation_scope(text, match),
            )
            for match in sorted(matches, key=lambda item: item.start())
        ]
    )


def _contexts(
    text: str,
    languages: Iterable[Language],
    *,
    kind: Literal["condition", "exception", "exemption"],
    flags: list[str],
) -> list[ContextCandidate]:
    matches: list[re.Match[str]] = []
    for language in languages:
        if kind == "condition":
            pattern = _EN_CONDITION_RE if language == "en" else _NO_CONDITION_RE
        elif kind == "exception":
            pattern = _EN_EXCEPTION_RE if language == "en" else _NO_EXCEPTION_RE
        elif language == "en":
            pattern = _EN_EXEMPTION_RE
        else:
            continue
        matches.extend(pattern.finditer(text))
        if kind == "condition" and language == "en":
            matches.extend(_EN_APPLICABILITY_CONDITION_RE.finditer(text))

    result: list[ContextCandidate] = []
    for match in sorted(matches, key=lambda item: item.start()):
        if kind == "condition" and _skip_condition_match(text, match):
            continue
        clause = _context_clause(text, match.start(), match.end())
        cue = match.group(0).lower()
        candidate_flags: list[str] = []
        ambiguous = cue == "where" and not re.match(
            r"\s+(?:feasible|applicable|appropriate|necessary|possible|"
            r"practicable|required)\b",
            text[match.end() :],
            re.IGNORECASE,
        )
        if ambiguous:
            candidate_flags.append("where_may_be_locative_or_relative")
            flags.append(f"ambiguous_condition_marker:where:{match.start()}")
        if clause.end == match.end():
            candidate_flags.append("missing_context_body")
            flags.append(f"missing_{kind}_body:{match.start()}")
        result.append(
            ContextCandidate(
                marker=_span(text, match.start(), match.end()),
                clause=clause,
                kind=kind,
                ambiguous=ambiguous,
                flags=candidate_flags,
            )
        )
    return _deduplicate_by_marker(result)


def _skip_condition_match(text: str, match: re.Match[str]) -> bool:
    cue = re.sub(r"\s+", " ", match.group(0).lower())
    sentence_start = max(
        text.rfind(".", 0, match.start()),
        text.rfind(";", 0, match.start()),
        text.rfind("\n", 0, match.start()),
    ) + 1
    prefix = text[sentence_start : match.start()]
    if cue == "after" and re.search(
        r"\b(?:periods?|intervals?|timeframes?|windows?)\s*$",
        prefix,
        re.IGNORECASE,
    ):
        # ``withholding periods after treatments`` names the period itself;
        # it is not a conditional trigger of the Requirement.
        return True
    if cue == "when" and not _EN_MODAL_RE.search(prefix):
        if re.search(
            r"\bnumber\s+of\s+(?:days?|times?|events?|incidents?|cycles?)\b",
            prefix,
            re.IGNORECASE,
        ):
            return True
    if cue == "prior to":
        colon = text.rfind(":", 0, match.start())
        if colon >= 0 and match.start() - colon < 500 and re.search(
            r"(?:^|\s)\d+\.\s",
            text[colon + 1 : match.start()],
        ):
            return True
    return False


def _dates(text: str) -> list[DateCandidate]:
    result: list[DateCandidate] = []
    occupied: list[tuple[int, int]] = []
    for pattern in _DATE_PATTERNS:
        for match in pattern.finditer(text):
            if any(
                match.start() < end and start < match.end()
                for start, end in occupied
            ):
                continue
            span = _span(text, match.start(), match.end())
            result.append(
                DateCandidate(
                    span=span,
                    scope=_enclosing_clause(text, match.start(), match.end()),
                )
            )
            occupied.append((match.start(), match.end()))
    return sorted(result, key=lambda item: (item.span.start, item.span.end))


def _thresholds(
    text: str,
    flags: list[str],
    *,
    languages: Iterable[Language] = ("en", "no"),
    excluded_spans: Iterable[tuple[int, int]] = (),
) -> list[ThresholdCandidate]:
    candidates: list[ThresholdCandidate] = []
    active_languages = tuple(languages)
    occupied: list[tuple[int, int]] = list(excluded_spans)
    structural_comparators: set[int] = set()

    for match in _QUALITATIVE_LTE_RE.finditer(text):
        interval = (match.start(), match.end())
        if any(_overlaps(interval, prior) for prior in occupied):
            continue
        candidates.append(ThresholdCandidate(
            span=_span(text, *interval),
            operator="lte",
            value=match.group("value"),
            normalized_value=match.group("value"),
            unit=None,
        ))
        occupied.append(interval)

    for match in _EXACT_RATE_STEP_RE.finditer(text):
        value_start, value_end = match.span("value")
        unit_end = match.end("unit")
        interval = (value_start, unit_end)
        if any(_overlaps(interval, prior) for prior in occupied):
            continue
        candidates.append(ThresholdCandidate(
            span=_span(text, *interval),
            operator="eq",
            value=match.group("value"),
            normalized_value=_normalize_number(match.group("value")),
            unit=match.group("unit"),
        ))
        occupied.append(interval)

    for pattern in _RANGE_PATTERNS:
        for match in pattern.finditer(text):
            if not all(
                _number_allowed(match.group(name), active_languages)
                for name in ("first", "second")
            ):
                continue
            unit, end, unit_ambiguous = _unit_after(text, match.end(), allow_generic=False)
            if pattern is _RANGE_PATTERNS[2] and unit is None:
                continue
            interval = (match.start(), end)
            if any(_overlaps(interval, prior) for prior in occupied):
                continue
            candidate_flags = ["unit_missing"] if unit is None else []
            number_ambiguous = _ambiguous_number(match.group("first")) or _ambiguous_number(
                match.group("second")
            )
            if number_ambiguous:
                candidate_flags.append("ambiguous_numeric_separator")
                flags.append(f"ambiguous_numeric_separator:{match.start()}")
            candidates.append(
                ThresholdCandidate(
                    span=_span(text, *interval),
                    operator="range",
                    value=match.group("first"),
                    normalized_value=_normalize_number(match.group("first")),
                    end_value=match.group("second"),
                    normalized_end_value=_normalize_number(match.group("second")),
                    unit=unit,
                    ambiguous=unit_ambiguous or number_ambiguous,
                    flags=candidate_flags,
                )
            )
            occupied.append(interval)

    for match in _COMPARATIVE_RE.finditer(text):
        if not _number_allowed(match.group("value"), active_languages):
            continue
        if any(_overlaps((match.start(), match.end()), prior) for prior in occupied):
            continue
        if _is_structural_cardinality(text, match):
            structural_comparators.add(match.start())
            continue
        unit, end, unit_ambiguous = _unit_after(text, match.end(), allow_generic=True)
        end = _extend_within_anchor(
            text,
            end,
            comparator=match.group("comparator"),
            unit=unit,
        )
        interval = (match.start(), end)
        comparator = _normalize_comparator(match.group("comparator"))
        candidate_flags: list[str] = []
        number_ambiguous = _ambiguous_number(match.group("value"))
        if number_ambiguous:
            candidate_flags.append("ambiguous_numeric_separator")
            flags.append(f"ambiguous_numeric_separator:{match.start()}")
        if unit_ambiguous and unit is not None:
            candidate_flags.append("unit_requires_review")
            flags.append(f"threshold_unit_requires_review:{match.start()}:{unit}")
        candidates.append(
            ThresholdCandidate(
                span=_span(text, *interval),
                operator=comparator,
                value=match.group("value"),
                normalized_value=_normalize_number(match.group("value")),
                unit=unit,
                ambiguous=unit_ambiguous or number_ambiguous,
                flags=candidate_flags,
            )
        )
        occupied.append(interval)

    for match in _BARE_QUANTITY_RE.finditer(text):
        if not _number_allowed(match.group("value"), active_languages):
            continue
        interval = (match.start(), match.end())
        if any(_overlaps(interval, prior) for prior in occupied):
            continue
        number_ambiguous = _ambiguous_number(match.group("value"))
        candidate_flags = ["quantity_without_explicit_comparator"]
        if number_ambiguous:
            candidate_flags.append("ambiguous_numeric_separator")
            flags.append(f"ambiguous_numeric_separator:{match.start()}")
        candidates.append(
            ThresholdCandidate(
                span=_span(text, *interval),
                operator="unspecified",
                value=match.group("value"),
                normalized_value=_normalize_number(match.group("value")),
                unit=match.group("unit"),
                ambiguous=True,
                flags=candidate_flags,
            )
        )
        occupied.append(interval)

    for match in re.finditer(
        r"(?:at\s+least|at\s+most|less\s+than|more\s+than|minst|høyst|"
        r"mindre\s+enn|mer\s+enn|>=|<=|≥|≤|>|<)",
        text,
        re.IGNORECASE,
    ):
        if match.start() in structural_comparators:
            continue
        if not any(start <= match.start() < end for start, end in occupied):
            flags.append(f"unparsed_threshold_comparator:{match.start()}")

    return sorted(candidates, key=lambda item: (item.span.start, item.span.end))


def _cross_references(
    text: str,
    flags: list[str],
) -> list[CrossReferenceCandidate]:
    raw: list[tuple[int, int, str, bool]] = []
    for match in _NORWEGIAN_SECTION_RE.finditer(text):
        reference_type = (
            "section_range"
            if re.search(r"\b(?:til|og)\b", match.group(0), re.I)
            else "section"
        )
        raw.append((match.start(), match.end(), reference_type, False))
    for pattern, reference_type in _LABELLED_REFERENCE_PATTERNS:
        for match in pattern.finditer(text):
            selected_type = reference_type
            if reference_type == "section" and re.search(
                r"\b(?:and|to)\b|[–—]", match.group(0), re.IGNORECASE
            ):
                selected_type = "section_range"
            ambiguous = reference_type in {"paragraph", "letter"} or bool(
                re.search(
                    r"\b(?:dette|samme|foregående|neste)\b",
                    match.group(0),
                    re.IGNORECASE,
                )
            )
            raw.append((match.start(), match.end(), selected_type, ambiguous))

    selected: list[tuple[int, int, str, bool]] = []
    for candidate in sorted(raw, key=lambda value: (value[0], -(value[1] - value[0]))):
        interval = candidate[:2]
        if any(_overlaps(interval, prior[:2]) for prior in selected):
            continue
        selected.append(candidate)
    selected.sort(key=lambda value: value[0])

    result = [
        CrossReferenceCandidate(
            span=_span(text, start, end),
            target=text[start:end],
            reference_type=reference_type,  # type: ignore[arg-type]
            ambiguous=ambiguous,
            flags=["enclosing_section_not_explicit"] if ambiguous else [],
        )
        for start, end, reference_type, ambiguous in selected
    ]
    covered = [(item.span.start, item.span.end) for item in result]
    for match in re.finditer(r"§{1,2}", text):
        if not any(start <= match.start() < end for start, end in covered):
            flags.append(f"unparsed_cross_reference_symbol:{match.start()}")
    return result


def _modality_scope(
    text: str,
    start: int,
    *,
    language: Language,
) -> SourceSpan | None:
    """Find the action governed by a modal, skipping a leading qualifier."""

    cursor = start
    while cursor < len(text) and (text[cursor].isspace() or text[cursor] in ",:"):
        cursor += 1
    condition_pattern = _EN_CONDITION_RE if language == "en" else _NO_CONDITION_RE
    while (leading := condition_pattern.match(text, cursor)) is not None:
        clause = _context_clause(text, leading.start(), leading.end())
        boundary = clause.end
        if boundary >= len(text) or text[boundary] != ",":
            break
        cursor = boundary + 1
        while cursor < len(text) and (
            text[cursor].isspace() or text[cursor] in ",:"
        ):
            cursor += 1
    return _local_scope(text, cursor)


def _negation_scope(text: str, match: re.Match[str]) -> SourceSpan | None:
    """Keep the negated phrase local; ``no`` noun phrases stop at a comma."""

    if match.group(0).lower() != "no":
        return _local_scope(text, match.end())
    cursor = match.end()
    while cursor < len(text) and text[cursor].isspace():
        cursor += 1
    boundary = _first_clause_boundary(text, cursor, include_comma=True)
    end = boundary if boundary is not None else len(text)
    while end > cursor and text[end - 1].isspace():
        end -= 1
    return _span(text, cursor, end) if end > cursor else None


def _local_scope(text: str, start: int) -> SourceSpan | None:
    cursor = start
    while cursor < len(text) and (text[cursor].isspace() or text[cursor] in ",:"):
        cursor += 1
    if cursor >= len(text):
        return None
    tail = text[cursor:]
    stop = len(tail)
    punctuation = _first_clause_boundary(text, cursor, include_comma=False)
    if punctuation is not None:
        stop = min(stop, punctuation - cursor)
    context = re.search(
        r",?\s+\b(?:provided\s+that|in\s+the\s+event\s+of|only\s+if|"
        r"based\s+on|prior\s+to|after|"
        r"if|when|where|unless|except|dersom|hvis|"
        r"når|unntatt|med\s+mindre)\b",
        tail,
        re.IGNORECASE,
    )
    if context:
        stop = min(stop, context.start())
    next_modality = re.search(
        r"(?:,\s*)?(?:(?:and|or|og|eller)\s+)?"
        r"\b(?:shall(?:\s+not)?|must(?:\s+not)?|may(?:\s+not)?|"
        r"should(?:\s+not)?|needs?\s+to|skal(?:\s+ikke)?|"
        r"må(?:\s+ikke)?|kan(?:\s+ikke)?)\b",
        tail,
        re.IGNORECASE,
    )
    if next_modality:
        modal_stop = next_modality.start()
        relative = re.search(
            r"\b(?:which|that|who)\s*$",
            tail[:modal_stop],
            re.IGNORECASE,
        )
        if relative is not None:
            modal_stop = relative.start()
        stop = min(stop, modal_stop)
    end = cursor + stop
    while end > cursor and (text[end - 1].isspace() or text[end - 1] in ",:;-"):
        end -= 1
    return _span(text, cursor, end) if end > cursor else None


def _context_clause(text: str, start: int, marker_end: int) -> SourceSpan:
    boundary = _first_clause_boundary(
        text,
        marker_end,
        include_comma=True,
        include_colon=True,
    )
    end = boundary if boundary is not None else len(text)
    while end > marker_end and text[end - 1].isspace():
        end -= 1
    return _span(text, start, max(marker_end, end))


def _first_clause_boundary(
    text: str,
    start: int,
    *,
    include_comma: bool,
    include_colon: bool = False,
) -> int | None:
    field_boundary = _next_source_field_label_start(text, start)
    boundaries = ";.\n"
    if include_comma:
        boundaries += ","
    if include_colon:
        boundaries += ":"
    for index in range(start, len(text)):
        if field_boundary is not None and index >= field_boundary:
            return field_boundary
        character = text[index]
        if character not in boundaries:
            continue
        if character == "." and _period_is_non_boundary(text, index, start):
            continue
        return index
    return None


def _period_is_non_boundary(text: str, index: int, field_start: int) -> bool:
    if (
        index > 0
        and index + 1 < len(text)
        and text[index - 1].isdigit()
        and text[index + 1].isdigit()
    ):
        return True
    window = text[max(0, index - 4):min(len(text), index + 4)].casefold()
    if "e.g." in window or "i.e." in window:
        return True
    marker = re.search(r"(?<!\w)(\d+)\.$", text[field_start:index + 1])
    if marker is None or index + 1 >= len(text) or not text[index + 1].isspace():
        return False
    field_end = _next_source_field_label_start(text, index + 1) or len(text)
    prior = text[field_start:marker.start()]
    following = text[index + 1:field_end]
    return bool(
        ":" in prior
        or re.search(r"(?<!\w)\d+\.\s", prior)
        or re.search(r"(?<!\w)\d+\.\s", following)
    )


def _enclosing_clause(text: str, start: int, end: int) -> SourceSpan:
    """Return the smallest punctuation-bounded clause containing a span."""

    field_start, field_end = source_field_value_bounds(text, start)
    left = start
    while left > field_start and text[left - 1] not in ";.\n":
        left -= 1
    right = end
    while right < field_end and text[right] not in ";.\n,":
        right += 1
    while left < right and (text[left].isspace() or text[left] in ",:"):
        left += 1
    while right > left and text[right - 1].isspace():
        right -= 1
    return _span(text, left, right)


def _unit_after(
    text: str,
    start: int,
    *,
    allow_generic: bool,
) -> tuple[str | None, int, bool]:
    known = _KNOWN_UNIT_RE.match(text, start)
    if known and not _crosses_source_field_boundary(text, start, known.end()):
        return known.group("unit"), known.end(), False
    if not allow_generic:
        return None, start, False
    of_unit = _OF_UNIT_RE.match(text, start)
    if of_unit and not _crosses_source_field_boundary(text, start, of_unit.end()):
        return of_unit.group("unit"), of_unit.end(), False
    generic = _GENERIC_UNIT_RE.match(text, start)
    if (
        not generic
        or generic.group("unit").lower() in _STOP_UNITS
        or _crosses_source_field_boundary(text, start, generic.end())
    ):
        return None, start, False
    return generic.group("unit"), generic.end(), True


def source_field_value_bounds(text: str, position: int) -> tuple[int, int]:
    """Return the source-exact value interval around ``position``.

    Parser-produced legal records commonly concatenate labelled fields, for
    example ``Requirement: < 1.2 Applicability: All``.  Those labels are hard
    semantic boundaries even when the source renderer omitted a newline.  The
    returned half-open bounds exclude the labels themselves and never rewrite
    the supplied text.
    """

    lower = 0
    upper = len(text)
    for match in _SOURCE_FIELD_LABEL_RE.finditer(text):
        if match.end() <= position:
            lower = match.end()
            continue
        if match.start() >= position:
            upper = match.start()
            break
        # ``position`` inside a label is not expected for semantic candidates,
        # but fail closed to the label's empty value side if it occurs.
        lower = match.end()
    return lower, upper


def _next_source_field_label_start(text: str, start: int) -> int | None:
    match = _SOURCE_FIELD_LABEL_RE.search(text, start)
    return match.start() if match is not None else None


def _crosses_source_field_boundary(text: str, start: int, end: int) -> bool:
    boundary = _next_source_field_label_start(text, start)
    return boundary is not None and boundary < end


def _is_structural_cardinality(text: str, match: re.Match[str]) -> bool:
    """Exclude list-selection grammar such as ``at least one of the following``."""

    if _normalize_number(match.group("value")) != 1:
        return False
    following = text[match.end() : match.end() + 40]
    return bool(re.match(r"\s+of\s+(?:the\s+)?following\b", following, re.IGNORECASE))


def _number_allowed(value: str, languages: Iterable[Language]) -> bool:
    normalized = value.strip().lower()
    if normalized not in _NUMBER_WORDS:
        return True
    selected = set(languages)
    return (
        "en" in selected and normalized in _EN_NUMBER_WORDS
    ) or (
        "no" in selected and normalized in _NO_NUMBER_WORDS
    )


def _extend_within_anchor(
    text: str,
    end: int,
    *,
    comparator: str,
    unit: str | None,
) -> int:
    """Keep a source-exact event anchor in ``within N days of ...`` thresholds."""

    if comparator.strip().lower() != "within" or not unit:
        return end
    if unit.lower() not in {"day", "days", "week", "weeks", "hour", "hours"}:
        return end
    if not re.match(r"\s+of\s+", text[end:], re.IGNORECASE):
        return end
    cursor = end
    field_boundary = _next_source_field_label_start(text, end)
    limit = field_boundary if field_boundary is not None else len(text)
    while cursor < limit and text[cursor] not in ",;.\n":
        cursor += 1
    while cursor > end and text[cursor - 1].isspace():
        cursor -= 1
    return cursor


def _normalize_comparator(value: str) -> ThresholdOperator:
    normalized = re.sub(r"\s+", " ", value.strip().lower())
    if normalized in {
        "at least",
        "no less than",
        "not less than",
        "minimum of",
        "minst",
        "ikke mindre enn",
        "minimum på",
        ">=",
        "=>",
        "≥",
    }:
        return "gte"
    if normalized in {
        "at most",
        "no more than",
        "not more than",
        "maximum of",
        "within",
        "høyst",
        "maksimalt",
        "ikke mer enn",
        "maksimum på",
        "innen",
        "<=",
        "=<",
        "≤",
    }:
        return "lte"
    if normalized in {"less than", "mindre enn", "<"}:
        return "lt"
    if normalized in {"more than", "greater than", "mer enn", ">"}:
        return "gt"
    return "eq"


def _normalize_number(value: str) -> float | None:
    normalized = value.strip().lower()
    if normalized in _NUMBER_WORDS:
        return _NUMBER_WORDS[normalized]
    if _ambiguous_number(normalized):
        return None
    try:
        return float(normalized.replace(",", "."))
    except ValueError:
        return None


def _ambiguous_number(value: str) -> bool:
    """Flag comma forms that can be decimal or thousands notation."""

    return bool(re.fullmatch(r"\d{1,3},\d{3}", value.strip()))


def _is_calendar_may(text: str, match: re.Match[str]) -> bool:
    if match.group(0) != "May":
        return False
    after = text[match.end() : match.end() + 8]
    before = text[max(0, match.start() - 4) : match.start()]
    return bool(re.match(r"\s+\d{4}\b", after) or re.search(r"\b(?:in|on)\s*$", before, re.I))


def _span(text: str, start: int, end: int) -> SourceSpan:
    return SourceSpan(start=start, end=end, text=text[start:end])


def _overlaps(left: tuple[int, int], right: tuple[int, int]) -> bool:
    return left[0] < right[1] and right[0] < left[1]


def _deduplicate_by_span(
    values: Iterable[ModalityCandidate | NegationCandidate],
) -> list[ModalityCandidate] | list[NegationCandidate]:
    result: list[ModalityCandidate | NegationCandidate] = []
    seen: set[tuple[int, int]] = set()
    for value in values:
        key = (value.span.start, value.span.end)
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result  # type: ignore[return-value]


def _deduplicate_by_marker(values: Iterable[ContextCandidate]) -> list[ContextCandidate]:
    result: list[ContextCandidate] = []
    seen: set[tuple[int, int]] = set()
    for value in values:
        key = (value.marker.start, value.marker.end)
        if key not in seen:
            seen.add(key)
            result.append(value)
    return result


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _all_spans(analysis: RequirementSemanticAnalysis) -> Iterable[SourceSpan]:
    for item in analysis.language.evidence:
        yield item.span
    for item in analysis.modalities:
        yield item.span
        if item.scope is not None:
            yield item.scope
    for item in analysis.negations:
        yield item.span
        if item.scope is not None:
            yield item.scope
    for item in [*analysis.conditions, *analysis.exceptions, *analysis.exemptions]:
        yield item.marker
        yield item.clause
    for item in analysis.thresholds:
        yield item.span
    for item in analysis.dates:
        yield item.span
        if item.scope is not None:
            yield item.scope
    for item in analysis.cross_references:
        yield item.span
