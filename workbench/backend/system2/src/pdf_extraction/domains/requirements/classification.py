"""Conservative offline proposals. Classification is reviewed separately from text."""
import re
from .applicability import signals
from .context_signals import signals as context_signals
from .classification_evidence import context_role, indicator_row

VERSION = 'literal-requirements/6'
NORMATIVE = re.compile(r'\b(shall|must|required|prohibited|should|may not|skal|må|plikt|forbudt|kan ikke)\b', re.I)
MODAL_DEFINITION = re.compile(
    r'''^["'“‘](?:shall|must|should|may)["'”’]\s+(?:denotes|means|indicates|is used to express)\s+[^.!?]+[.!]?\s*$''', re.I)
HEADING_LOCATOR = re.compile(r'(?:^|>\s*)h[1-6](?::nth-of-type\(\d+\))?\s*$', re.I)


def propose(unit):
    kind = unit.get('kind', '')
    body = unit.get('fields', {}).get('body', '')
    fields = [str(v).strip() for k,v in unit.get('fields',{}).items()
              if k in {'body','title','criteria','notes','context'} and str(v).strip()]
    definitions = [v for v in fields if MODAL_DEFINITION.fullmatch(v)]
    text = '\n'.join(v for v in fields if v not in definitions)
    refs = unit.get('references', [])
    heading = kind in {'source_heading', 'source_title'} or bool(
        refs and all(HEADING_LOCATOR.search(str(r.get('locator', ''))) for r in refs))
    matches = list(NORMATIVE.finditer(text))
    scope_evidence = signals(text)
    context_evidence = context_signals(text)
    role_evidence = context_role(unit)
    row_evidence = indicator_row(unit)
    if kind == 'source_table_assembly':
        result, rule = 'context', 'This view combines retained table fragments. Individual source rows keep their own Requirement judgments.'
    elif kind == 'coverage':
        result, rule = 'context', 'Coverage checks account for original regions; they are not source obligations.'
    elif role_evidence and (role_evidence['mixed_roles'] or row_evidence):
        result, rule = 'undetermined', 'This source unit mixes explicit context and possible formal content. Check its boundaries and preserve every part before judging it.'
    elif role_evidence:
        result, rule = 'context', 'An explicit source label or nearest source heading identifies rationale or interpretation. Retain the original wording and its related Requirement; normative words in this context do not create a separate formal item.'
    elif row_evidence:
        result, rule = 'requirement', 'The complete selected source row pairs an Indicator with a nonempty Requirement value beneath explicit, located column headers. Preserve both cells and verify the candidate; this is not a calibrated decision.'
    elif matches:
        result, rule = 'requirement', 'The original contains normative wording. Its role and scope still require verification.'
    elif scope_evidence:
        result, rule = 'requirement', 'The original states an applicability or exemption rule for requirements. Preserve the complete clause and check its scope; this is not a new standalone obligation.'
    elif kind in {'standard_principle', 'standard_indicator'}:
        result, rule = 'requirement', 'The parser identified a numbered standard item; this does not establish that it is an obligation.'
    elif definitions and not text:
        result, rule = 'context', 'The complete source unit defines a quoted modal word; it does not itself prescribe an action.'
    elif heading:
        result, rule = 'context', 'The bound source element is a heading without normative wording. Preserve it as context for its content.'
    elif context_evidence:
        result, rule = 'context', 'The complete original matches a bibliographic citation or a questions-only support contact. Preserve its located context; this is a local proposal, not a calibrated decision.'
    else:
        result, rule = 'undetermined', 'No conclusive local rule matched. Absence of a keyword does not establish non-Requirement content.'
    return {'classification': result, 'method': VERSION, 'rule':rule, 'matches':[{'text':m.group(0),'start':m.start(),'end':m.end()} for m in matches],
            'scope_evidence': scope_evidence,
            'context_evidence': context_evidence,
            'source_role_evidence': role_evidence, 'table_role_evidence': row_evidence,
            'uncertainty':'Local rules cannot resolve examples, exceptions, references or applicability without review.',
            'parts': [{'confidence': None, 'calibration_version': None,
                       'evidence': unit.get('references', [])}]}
