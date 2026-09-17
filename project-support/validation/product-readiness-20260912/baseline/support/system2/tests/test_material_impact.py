from copy import deepcopy
import uuid

from pdf_extraction.review.materials import MaterialStore


def request(material, **kwargs):
    return dict(request_id=str(uuid.uuid4()), actor='Engineering reviewer', material_id=material['id'],
                expected_revision=material['revision'], **kwargs)


def make(tmp_path, blocks=None):
    store = MaterialStore(tmp_path)
    scopes = [dict(id=f'page:{p}', kind='page', location={'page': p}) for p in (1, 2, 3)]
    m = store.open(dict(source_id='fixture', snapshot_id='one', content_hash='hash'), 'Engineering only', scopes)
    blocks = blocks or [dict(id=f'b{p}', type='text', text=f'Page {p}',
                            source_refs=[{'scope_id': f'page:{p}'}]) for p in (1, 2, 3)]
    m = store.save(request(m, blocks=blocks, association_reviewed=True))['material']
    m = store.confirm(request(m, checked_scope=[s['id'] for s in scopes], explicit_confirmation=True))['material']
    return store, m


def test_local_edit_keeps_other_checks_with_original_provenance(tmp_path):
    store, m = make(tmp_path)
    blocks = deepcopy(m['blocks']); blocks[0]['text'] = 'Corrected page one'
    updated = store.save(request(m, blocks=blocks, checked_scope=['page:1','page:2','page:3']))['material']
    assert updated['checked_scope'] == ['page:2','page:3']
    assert updated['review_checks']['page:2'] == m['review_checks']['page:2']
    assert updated['review_impact']['affected_scope'] == ['page:1']
    assert updated['confirmation'] is None
    assert store.read(m['id'], revision=m['revision'])['confirmation'] == m['confirmation']


def test_dependency_and_cross_page_table_expand_impact(tmp_path):
    blocks = [dict(id='t', type='table', table={'rows':[['A']]}, source_refs=[{'scope_id':'page:1'}, {'scope_id':'page:2'}]),
              dict(id='note', type='text', text='Shared note', dependencies=['t'], source_refs=[{'scope_id':'page:3'}])]
    store, m = make(tmp_path, blocks)
    edited = deepcopy(m['blocks']); edited[0]['table']['rows'][0][0] = 'B'
    result = store.save(request(m, blocks=edited))['material']
    assert result['checked_scope'] == []
    assert result['review_impact']['affected_scope'] == ['page:1','page:2','page:3']


def test_heading_change_invalidates_descendants(tmp_path):
    blocks = [dict(id='h', type='heading', level=1, text='Chapter', source_refs=[{'scope_id':'page:1'}]),
              dict(id='p', type='text', parent_id='h', text='Body', source_refs=[{'scope_id':'page:2'}]),
              dict(id='other', type='text', text='Independent', source_refs=[{'scope_id':'page:3'}])]
    store, m = make(tmp_path, blocks)
    edited = deepcopy(blocks); edited[0]['text'] = 'New chapter'
    result = store.save(request(m, blocks=edited))['material']
    assert result['checked_scope'] == ['page:3']
    assert result['association_review_required'] is True


def test_unknown_reference_or_global_issue_requires_full_review(tmp_path):
    store, m = make(tmp_path)
    edited = deepcopy(m['blocks']); edited[0]['source_refs'] = []
    result = store.save(request(m, blocks=edited))['material']
    assert result['checked_scope'] == []
    assert result['review_impact']['reason'] == 'unknown_original_association'
    other = store.save(request(m, issues=[{'id':'missing','message':'Missing appendix','resolved':False}]))
    assert other['status'] == 'conflict'
    current = other['material']
    result = store.save(request(current, issues=[{'id':'missing','message':'Missing appendix','resolved':False}]))['material']
    assert result['review_impact']['reason'] == 'material_issue_changed'


def test_source_replacement_preserves_confirmation_only_as_history(tmp_path):
    store, m = make(tmp_path)
    store.mark_source_version('fixture', 'two', 'different')
    result = store.read(m['id'])
    assert result['checked_scope'] == []
    assert result['review_checks'] == {}
    assert result['source_stale']
    assert result['confirmation'] == m['confirmation']
    assert store.read(m['id'], revision=m['revision'])['checked_scope'] == m['checked_scope']


def test_reorder_and_candidate_merge_use_same_impact(tmp_path):
    store, m = make(tmp_path)
    started = store.start_candidate(request(m))
    ready = store.finish_candidate(m['id'], started['candidate']['id'], m['blocks'])
    moved = [m['blocks'][1],m['blocks'][0],m['blocks'][2]]
    result = store.reconcile(request(ready['material'], candidate_id=started['candidate']['id'],
                            action='merge', reviewed_against_source=True, blocks=moved))['material']
    assert result['checked_scope'] == ['page:3']
    assert result['confirmation'] is None


def test_legacy_checks_without_provenance_are_not_inherited(tmp_path):
    from pdf_extraction.review.material_impact import review_impact
    store, m = make(tmp_path)
    m.pop('review_checks')
    blocks = deepcopy(m['blocks']); blocks[0]['text'] = 'Changed'
    impact = review_impact(m, blocks, m['issues'])
    assert impact['full_review_required']
    assert impact['retained_scope'] == []


def test_unchecking_scope_revokes_current_confirmation(tmp_path):
    store, m = make(tmp_path)
    saved = store.save(request(m, checked_scope=['page:1']))['material']
    assert saved['confirmation'] is None
    assert saved['content_status'] == 'review_in_progress'
    assert store.read(m['id'], revision=m['revision'])['confirmation'] == m['confirmation']


def test_withdrawing_association_check_revokes_confirmation(tmp_path):
    store, m = make(tmp_path)
    saved=store.save(request(m,association_reviewed=False))['material']
    assert saved['confirmation'] is None
    assert saved['association_review_required']
    assert saved['content_status'] == 'review_in_progress'


def test_new_source_open_invalidates_checks_without_erasing_old_confirmation(tmp_path):
    store, m = make(tmp_path)
    store.open(dict(m['source'], snapshot_id='replacement',content_hash='changed'), 'New original', m['scope'])
    old=store.read(m['id'])
    assert old['checked_scope'] == []
    assert old['confirmation'] == m['confirmation']


def test_long_dependency_chain_and_cycle_are_handled_without_recursion(tmp_path):
    from pdf_extraction.review.materials import validate_blocks
    import pytest
    blocks=[dict(id=str(i),type='text',text='Engineering',dependencies=[str(i+1)] if i<1999 else []) for i in range(2000)]
    validate_blocks(blocks, [])
    blocks[-1]['dependencies']=['0']
    with pytest.raises(ValueError, match='cycle'): validate_blocks(blocks, [])


def test_return_to_prior_source_version_requires_new_confirmation(tmp_path):
    store,original=make(tmp_path)
    store.mark_source_version('fixture','replacement','different-bytes')
    historical=store.read(original['id'])
    assert historical['source_stale'] and historical['confirmation']==original['confirmation']
    store.mark_source_version('fixture','one','hash')
    current=store.read(original['id'])
    assert not current['source_stale'] and current['content_status']=='draft'
    assert current['checked_scope']==[] and current['review_checks']=={} and current['confirmation'] is None
    assert current['association_review_required'] and store.counts()['current_reviewed']==0
    assert current['blocks']==original['blocks']
    assert store.read(original['id'],revision=original['revision'])['confirmation']==original['confirmation']
    assert store.read(original['id'],revision=historical['revision'])['confirmation']==original['confirmation']
    reviewed=store.confirm(request(current,checked_scope=['page:1','page:2','page:3'],association_reviewed=True,explicit_confirmation=True))['material']
    assert reviewed['content_status']=='content_review_complete' and store.counts()['current_reviewed']==1
    assert reviewed['confirmation']['at']!=original['confirmation']['at']


def test_excluded_source_reincluded_never_reactivates_historical_confirmation(tmp_path):
    store,original=make(tmp_path)
    store.mark_source_version('fixture',None,None)
    excluded=store.read(original['id'])
    # Partial historical work can be saved, but cannot carry a final decision
    # automatically into the later current-source state.
    historical=store.save(request(excluded,checked_scope=['page:1','page:2','page:3'],association_reviewed=True))['material']
    store.mark_source_version('fixture','one','hash')
    included=store.read(original['id'])
    assert not included['source_stale'] and included['confirmation'] is None
    assert included['checked_scope']==[] and included['association_review_required']
    assert included['review_impact']['reason']=='source_current_again_requires_review'
    assert store.counts()['current_reviewed']==0
    assert included['blocks']==original['blocks']
    assert store.read(original['id'],revision=original['revision'])['confirmation']==original['confirmation']


def test_confirmation_cannot_override_explicitly_unchecked_associations(tmp_path):
    import pytest
    store,original=make(tmp_path)
    assert not original['association_review_required']
    before=store.history(original['id'])
    with pytest.raises(ValueError,match='structural_associations_require_review'):
        store.confirm(request(original,checked_scope=original['checked_scope'],association_reviewed=False,explicit_confirmation=True))
    assert store.history(original['id'])==before
    assert store.read(original['id'])['confirmation']==original['confirmation']
