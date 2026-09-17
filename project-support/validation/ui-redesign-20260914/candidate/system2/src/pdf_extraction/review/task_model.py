"""Human-facing task descriptions derived from actual acceptance evidence."""
from ..domains.requirements.classification import propose


def passed(value): return value in {'human_accepted','machine_accepted'}

REASONS = {
 'human_followup':'This item needs human review before it can be complete. Check the current content and evidence; no completed review is implied.',
 'classification_score_binding_stale':'The recorded score belongs to a different or unbound classification proposal. Obtain current validated evidence or review the result; the historical score is retained.',
 'table_has_independent_row_items':'This table already has original row items. Classify those rows; keep the complete table as shared context to avoid double counting.',
 'requirement_subdivision_stale':'The accepted original or shared context changed. Recheck the requirement subitems against the current complete parent.',
 'review_draft_pending':'An unfinished review draft remains. Submit the decision before this item can be complete.',
 'source_verification_stale':'Content or the comparison method changed after the page check. Run the original page check again.',
 'table_assembly_header_changed':'The selected original column headings changed. Repair or undo this table combination.',
 'table_assembly_columns_changed':'A table fragment now has different columns. Repair its layout or undo the combination.',
 'table_assembly_fragment_unavailable':'An original table fragment is no longer current. Repair the table correspondence.',
 'overlap_evidence_only':'Retained evidence from another parsing window. It cannot be delivered as a separate Requirement.',
 'confidence_missing':'No reliable confidence score is available for this judgment.',
 'confidence_uncalibrated':'This scoring method has not been validated for this content.',
 'confidence_below_threshold':'The score is below the current acceptance threshold.',
 'image_content_not_transcribed':'An image may contain text that has not been transcribed.',
 'content_dependencies_unverified':'Related content must be checked first.',
 'classification_undetermined':'The local rules cannot determine whether this is a Requirement.',
 'human_location':'A reviewer reported that the original region is incorrect.',
 'human_table_row_gaps':'Some original table rows have no review scope. Create a row item or keep the row within the complete-table review.',
 'human_table_grid_gaps':'Some table positions are still uncovered. Complete the missing cells before accepting the table.',
 'human_unreadable':'A reviewer could not read the original.',
 'unclassified_residual':'Content was found outside the mapped original structure.',
}


def reason(code):
    if code.startswith('confidence_dimension_missing:'):return 'No validated score is available for '+code.split(':',1)[1]+'. This stage is not fully scored.'
    if code.startswith('confidence_dimension_'):return 'The confidence dimensions are incomplete or inconsistent. Recheck their evidence before automatic acceptance.'
    if code.startswith('source_check:'): return 'Original-page comparison found a located discrepancy. Inspect its evidence and repair or resolve it.'
    if code.startswith('source_scope:'): return 'Part of this original page has not been independently verified. Inspect the declared scope.'
    if code in REASONS: return REASONS[code]
    if 'footnote' in code or 'relationship' in code: return 'A footnote or content relationship needs checking.'
    if 'duplicate' in code: return 'A duplicate location or repeated element needs checking.'
    if 'image' in code: return 'Image evidence needs checking.'
    if 'conflict' in code or 'structure' in code: return 'The extracted structure contains an unresolved conflict.'
    if 'human_' in code: return 'A reviewer reported an unresolved issue.'
    return 'A source evidence check needs human confirmation. Open technical details for the recorded finding.'


def describe(unit, units=None):
    fields=readable_fields(unit, units)
    content=not passed(unit.get('content_status'))
    waiting=not content and unit.get('requirement_status')=='blocked' and not unit.get('superseded_by')
    codes=unit.get('content_reasons',[]) if content else unit.get('requirement_reasons',[])
    issues=unit.get('blockers',[]) if content else unit.get('requirement_blockers',[])
    def explain(code):
        if code.startswith('weekly_qa:'):
            finding=unit.get('weekly_findings',{}).get(code[len('weekly_qa:'):],{})
            return 'Weekly original check reported: '+finding.get('note','An unresolved problem needs repair and follow-up.')
        report=unit.get('source_verification',{})
        for finding in report.get('findings',[]):
            if code=='source_check:'+finding['id']:
                return 'PDF page '+str(finding['page_index']+1)+': '+finding['code'].replace('_',' ')+'. '+finding.get('source_text','')[:160]
        if code.startswith('source_scope:'):
            from ..contracts.hashing import digest
            item=next((x for x in report.get('unverified',[]) if code=='source_scope:'+digest(x)[:24]),None)
            if item:return 'Unverified: '+item['code'].replace('_',' ')
        return reason(code)
    from .effective import resolve
    kind=resolve(unit,units)['kind']
    typ='coverage' if kind=='coverage' else 'structure' if any(any(s in c for s in ('structure','relationship','footnote','location','merged_cell','table_grid','table_row')) for c in issues) else 'content' if content else 'requirement'
    questions={'content':'Is this text complete and faithful to the original?', 'structure':'Are the source region and content relationships correct?', 'requirement':'Does this content contain a Requirement?', 'coverage':'Has all content in this exact source range been accounted for?'}
    title=fields.get('identifier') or fields.get('title') or ' '.join(fields.get('body','').split())[:110] or ('Image or non-text content' if 'image' in kind else 'Original content')
    if kind=='source_section' and fields.get('body'): title=fields['body'].strip().split('\n')[0][:110]
    if kind=='coverage': title=fields.get('title') or 'Source range completeness'
    if unit.get('table_assembly'):questions['content']='Do these original page fragments form one table with matching columns?'
    done=passed(unit.get('content_status')) and passed(unit.get('requirement_status'))
    return {'type':typ,'title':title,'chapter':unit.get('chapter','Original order'),'question':questions[typ],
            'reason':explain((issues or codes or ['confidence_missing'])[0]),'reasons':[explain(c) for c in dict.fromkeys(issues+codes)],
            'actionable':not done and not waiting and not unit.get('superseded_by'), 'waiting':waiting,
            'confidence':unit.get('content_confidence' if content else 'requirement_confidence'),
            'stage':'content' if content else 'requirement', 'proposal':propose(dict(unit['original'],kind=kind,fields=fields))}


def readable_fields(unit, units=None):
    from .effective import resolve
    return resolve(unit, units)['fields']
