"""Validate persisted scores against their exact current local proposal."""
from ..contracts.hashing import digest

VERSION = 'requirement-score-binding/1'


def binding(unit, proposal):
    return {'schema': VERSION, 'method': proposal['method'],
            'original_sha256': digest(unit['original']),
            'proposal_sha256': digest(proposal)}


def applicable_parts(unit, proposal):
    """Return a derived score view without rewriting the historical score parts."""
    expected = binding(unit, proposal)
    result = []
    for part in unit.get('requirement_parts', proposal['parts']):
        if part.get('confidence') is not None and (
                part.get('rule_binding') != expected or part.get('method') != expected['method']):
            result.append(dict(part, confidence=None, calibration_version=None,
                               score_binding_status='stale_or_missing',
                               recorded_confidence=part.get('confidence')))
        else:
            result.append(dict(part))
    return result
