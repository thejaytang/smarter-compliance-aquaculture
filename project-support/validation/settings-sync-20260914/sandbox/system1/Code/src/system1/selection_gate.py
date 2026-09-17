"""Re-review holds are owned by open source operations, not a new decision value."""
REVIEW_TYPES={'SOURCE_REVIEW','SELECTION_REVIEW','MANUAL_FILE_REPLACEMENT'}

def pending_include_tasks(source,tasks):
    if source.get('operator_selection_decision')!='INCLUDE':return []
    return [t for t in tasks if t.get('source_id')==source.get('source_id')
            and t.get('is_open',True) and t.get('operation_type') in REVIEW_TYPES
            and t.get('trigger')!='OFFLINE_COLLABORATION_ADOPTION']

def project(sources,tasks):
    for source in sources:
        holds=pending_include_tasks(source,tasks)
        if holds and source.get('effective_selection')!='EXCLUDE':source['effective_selection']='PENDING'
        source['decision_display']='Pending-Include' if source.get('effective_selection')=='PENDING' and source.get('operator_selection_decision')=='INCLUDE' else source.get('effective_selection','PENDING')
        source['include_review_required']=bool(holds)
