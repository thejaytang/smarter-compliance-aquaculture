"""Evidence-bound acceptance. Percentages are routing scores, not guarantees."""
from __future__ import annotations

import math

DEFAULT_POLICY = {"revision": 1, "system1": .95, "content": .95,
                  "requirement": .95, "system3": .95}
ASPECTS = {'content': ('text','coverage','structure','order'),
           'requirement': ('classification','association','subdivision')}
GATE_VERSION = 'required-confidence-dimensions/1'


def validate_policy(policy):
    if set(policy) != set(DEFAULT_POLICY):
        raise ValueError('policy_fields_invalid')
    if type(policy['revision']) is not int or policy['revision'] < 1:
        raise ValueError('policy_revision_invalid')
    for key in DEFAULT_POLICY.keys() - {'revision'}:
        value = policy[key]
        if type(value) not in (float, int) or not math.isfinite(value) or not 0 < value <= 1:
            raise ValueError('threshold_must_be_between_zero_and_one')
    return dict(policy)


def assess(parts, threshold, *, blockers=(), human=False, touched=False, stage=None):
    """An uncalibrated generator score never grants automatic acceptance."""
    reasons = list(blockers)
    if stage is not None:
        if stage not in ASPECTS:raise ValueError('unknown_acceptance_stage')
        aspects=[p.get('aspect') for p in parts]
        for aspect in ASPECTS[stage]:
            if aspect not in aspects:reasons.append('confidence_dimension_missing:'+aspect)
            elif aspects.count(aspect)!=1:reasons.append('confidence_dimension_duplicate:'+aspect)
        if any(a not in ASPECTS[stage] for a in aspects):reasons.append('confidence_dimension_unknown')
    values = []
    for part in parts:
        value = part.get('confidence')
        if value is None:
            reasons.append('confidence_missing')
        elif type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
            reasons.append('confidence_invalid')
        else:
            values.append(value)
        if not part.get('calibration_version'):
            reasons.append('confidence_uncalibrated')
        if not part.get('evidence'):
            reasons.append('evidence_missing')
        if part.get('conflict'):
            reasons.append('evidence_conflict')
    if not parts:
        reasons.append('confidence_missing')
    unsupported = {'confidence_invalid', 'confidence_uncalibrated', 'evidence_missing', 'evidence_conflict'}
    score = min(values) if (len(values) == len(parts) and values
        and not unsupported.intersection(reasons)
        and not any(r.startswith('confidence_dimension_') for r in reasons)) else None
    if score is not None and score < threshold:
        reasons.append('confidence_below_threshold')
    if human and not blockers:
        return {'status': 'human_accepted', 'confidence': score, 'reasons': []}
    if touched:
        reasons.append('human_followup')
    return {'status': 'pending' if reasons else 'machine_accepted',
            'confidence': score, 'reasons': sorted(set(reasons))}


def accepted(value):
    return value in {'machine_accepted', 'human_accepted'}


def dimension_details(parts, stage, threshold):
    result=[]
    for aspect in ASPECTS[stage]:
        matches=[p for p in parts if p.get('aspect')==aspect]
        check=assess(matches,threshold)
        reason=('missing' if not matches else 'duplicate' if len(matches)>1 else
                'validated' if check['status']=='machine_accepted' else 'not_validated')
        result.append({'aspect':aspect,'status':reason,'confidence':check['confidence'] if len(matches)==1 else None,
            'reasons':(['confidence_dimension_duplicate:'+aspect] if len(matches)>1 else check['reasons']),
            'evidence':matches[0].get('evidence',[]) if len(matches)==1 else [],
            'calibration_version':matches[0].get('calibration_version') if len(matches)==1 else None,
            'method':matches[0].get('method') if len(matches)==1 else None})
    return result
