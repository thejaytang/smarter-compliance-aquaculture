"""Located, uncalibrated applicability signals for local review proposals."""
import re

SCOPE = re.compile(
    r'\b(?:(?:requirements?|standards?|criteria|criterion|provisions?|rules?)\s+'
    r'(?:(?:is|are)\s+(?:not\s+)?applicable|(?:does|do)\s+not\s+apply|appl(?:y|ies))\s+'
    r'(?:to|for|within|when|unless|regardless)\b|'
    r'(?:is|are)\s+(?:not\s+)?exempt\s+from\s+(?:the\s+)?'
    r'(?:requirements?|standards?|criteria|criterion|provisions?|rules?)\b)', re.I)
UNRESOLVED = re.compile(
    r'\b(?:example|hypothetical|whether|which|asks?|asked|says?|said|reported?|'
    r'describes?|described|formerly|previously|historically|proposed|proposal|draft|'
    r'might|could|would)\b', re.I)


def signals(text):
    """Retain the clause and exact offsets; never infer its concrete applicability."""
    # A quoted/example/question preamble can govern the following sentence or
    # line. Abstain for the whole supplied context rather than stripping it.
    framing = any(m.group().lower() not in {'which', 'whether'}
                  for m in UNRESOLVED.finditer(text))
    if ('?' in text or any(q in text for q in ('"', '“', '”', '‘', '’')) or framing
            or re.search(r'^\s*(?:which|whether)\b', text, re.I | re.M)):
        return []
    found, offset = [], 0
    # Keep separators to preserve offsets, including decimal points and newlines.
    for sentence in re.split(r'((?<=[.!?])\s+|\n+)', text):
        # A relative clause in earlier rationale is not a question about the
        # later applicability statement. Preserve local which/whether ambiguity.
        for match in (() if UNRESOLVED.search(sentence) else SCOPE.finditer(sentence)):
            found.append({'text': match.group(), 'start': offset+match.start(),
                          'end': offset+match.end(), 'clause': sentence})
        offset += len(sentence)
    return found
