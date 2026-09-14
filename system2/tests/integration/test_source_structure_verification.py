"""Isolated seeded structure controls, not independent human reference labels."""
from copy import deepcopy
import json

from pdf_extraction.contracts.hashing import digest
from pdf_extraction.review.source_verification import comparison_input, refresh_staleness
from pdf_extraction.verification.source_comparison import compare
from .test_two_stage_workflow import system, current, unit
from .test_pdf_repairs import table_units, get
from .test_review_rows import guarded
from .test_table_assembly import setup, join_request, assembly
from .test_original_page_verification import page, record


def table_document():
    table, row = table_units()
    raw = json.loads(table['original']['fields']['body'])
    for cell in raw['cells']:
        cell['page_index'] = 0
    for u in (table, row):
        for ref in u['original']['references']:
            ref['page_index'] = 0
    table['original']['fields']['body'] = json.dumps(raw)
    return dict(units=[table, row])


def structure_records(doc, p=0):
    return [r for r in comparison_input(doc,p) if r.get('record_kind')=='structure_only']


def test_grid_only_change_is_visible_and_does_not_repeat_cell_text():
    doc=table_document(); before=comparison_input(doc,0)
    raw=json.loads(doc['units'][0]['original']['fields']['body'])
    for cell in raw['cells']:cell['column']=1-cell['column']
    doc['units'][0]['table_geometry']={k:raw[k] for k in ('row_count','column_count','cells')}
    after=comparison_input(doc,0)
    lexical=lambda rs:[r for r in rs if r.get('record_kind')!='structure_only']
    assert lexical(before)==lexical(after)
    assert digest(before)!=digest(after)
    assert len(lexical(after))==2


def test_structure_cannot_explain_an_omitted_original_region():
    doc=table_document()
    result=compare(page(),structure_records(doc))
    assert any(f['code']=='source_region_unmapped' for f in result['findings'])
    clean=compare(page(),[record(page()['lines'][0]['text']),*structure_records(doc)])
    assert clean['findings']==[]
    assert not any(u['code']=='output_spatial_ownership_ambiguous' for u in clean['unverified'])


def test_typed_link_same_wording_new_target_and_target_edit_are_bound():
    doc=table_document(); table,row=doc['units']
    for identity in ('note-a','note-b'):
        note=unit(identity,'source_note');note['original']['fields']={'body':'Same original note', 'version':'1.5'}
        note['original']['references']=[dict(page_index=1,bbox=[10,600,200,620])];doc['units'].append(note)
    table['content_relations']=[dict(role='notes',target_unit_id='note-a')]
    before=comparison_input(doc,0)
    claims=structure_records(doc)
    assert next(r for r in claims if r['unit_id']=='row')['structure']['related_content'][0]['inherited_from_table']=='table'
    assert next(r for r in claims if r['unit_id']=='table')['structure']['related_content'][0]['fields']['version']=='1.5'
    table['content_relations'][0]['target_unit_id']='note-b'
    assert digest(before)!=digest(comparison_input(doc,0))
    before=comparison_input(doc,0)
    doc['units'][-1]['edits']={'body':'Only below 5 kg'}
    assert digest(before)!=digest(comparison_input(doc,0))
    result=compare(page(),comparison_input(doc,0))
    scopes=[u for u in result['unverified'] if u['code']=='output_relation_source_unverified']
    assert len(scopes)==1 and set(scopes[0]['unit_ids'])=={'table','row','note-b'}
    assert scopes[0]['target_references'][0]['page_index']==1


def test_review_versions_do_not_change_semantic_check_input():
    doc=table_document();before=comparison_input(doc,0)
    for u in doc['units']:
        u['version']=u.get('version',1)+1;u['content_human']=True;u['requirement_human']=True
    assert before==comparison_input(doc,0)


def test_grid_reversal_and_bad_span_are_located_without_claiming_independent_truth():
    doc=table_document();packets=structure_records(doc)
    table=next(r for r in packets if r['unit_id']=='table')['structure']['table']
    for c in table['cells']:c['column']=1-c['column']
    findings=compare(page(),packets)['findings']
    f=next(f for f in findings if f['code']=='output_table_position_order_conflict')
    assert f['axis']=='column' and f['severity']=='critical'
    assert len(f['source_regions'])==2 and f['confidence'] is None
    assert f['evidence_origin']=='output_structure_and_claimed_positions'
    table['cells'][0]['column_span']=3
    assert any(f['code']=='output_table_cell_outside_grid' for f in compare(page(),packets)['findings'])


def test_clean_merged_cell_and_nonseparated_positions_do_not_imply_reversal():
    doc=table_document();packets=structure_records(doc)
    table=next(r for r in packets if r['unit_id']=='table')['structure']['table']
    table['column_count']=3;table['cells'][0]['column_span']=2;table['cells'][1]['column']=2
    assert not any(f['code'].startswith('output_table_') for f in compare(page(),packets)['findings'])
    table['cells'][0]['references'][0]['bbox']=[0,0,200,100]
    table['cells'][0]['column']=1;table['cells'][0]['column_span']=2;table['cells'][1]['column']=0
    assert not any(f['code']=='output_table_position_order_conflict' for f in compare(page(),packets)['findings'])


def test_row_relation_edit_stales_checked_page_through_existing_transaction(system):
    s,did=system;doc=table_document();note=unit('note','source_note')
    note['original']['references']=[dict(page_index=1,bbox=[10,600,200,620])]
    s.install(did,[*doc['units'],note],[])
    from pdf_extraction.verification.source_comparison import METHOD
    with s.transaction() as db:
        d=s._load(db,did)
        cov=next(u for u in d['units'] if u['id']=='coverage')
        cov['source_verification']=dict(page_index=0,input_sha256=digest(comparison_input(d,0)),method=METHOD,stale=False)
        d['source_verification_pages']=[0];s._save(db,d)
    original=deepcopy(get(system,'table')['original'])
    s.decision(guarded(system,'row',action='relation',target_unit_id='note',target_fingerprint=digest(get(system,'note')),
                       role='notes',note='Isolated relation change after a machine check'))
    cov=get(system,'coverage')
    assert cov['source_verification']['stale'] and 'source_verification_stale' in cov['blockers']
    assert get(system,'row')['content_status']=='pending'
    assert get(system,'table')['original']==original


def test_assembly_other_page_change_and_fragment_order_are_bound(system):
    s,did=setup(system);s.decision(join_request(system));d=current(system)
    before=comparison_input(d,18)
    logical=next(r for r in before if r['unit_id']==assembly(system)['id'])
    assert logical['record_kind']=='structure_only'
    assert len(logical['structure']['table_assembly']['fragments'])==2
    for u in d['units']:u['version']=u.get('version',1)+1
    assert comparison_input(d,18)==before
    other=next(u for u in d['units'] if u['id']=='second');other['cell_edits']={'c1':'≥ 7 taxa'}
    assert digest(before)!=digest(comparison_input(d,18))
    d=current(system);a=next(u for u in d['units'] if u.get('table_assembly'))
    a['table_assembly']['fragments'].reverse()
    p=dict(page(),page_index=18)
    result=compare(p,comparison_input(d,18))
    assert any(f['code']=='output_table_fragment_order_conflict' for f in result['findings'])
    assert any(u['code']=='output_cross_page_relation_unverified' for u in result['unverified'])


def test_hierarchy_order_and_linked_target_role_change_stale_input():
    d=table_document();table=d['units'][0];before=comparison_input(d,0)
    table['hierarchy_edit']={'type':'table','heading_level':2}
    assert digest(before)!=digest(comparison_input(d,0))
    before=comparison_input(d,0);table['reading_order_key']='3/2'
    assert digest(before)!=digest(comparison_input(d,0))
    note=unit('note','source_note');d['units'].append(note)
    table['content_relations']=[dict(role='notes',target_unit_id='note')]
    before=comparison_input(d,0);note['hierarchy_edit']={'type':'caption'}
    assert digest(before)!=digest(comparison_input(d,0))
    before=comparison_input(d,0);note['version']=50
    assert before==comparison_input(d,0)


def test_unknown_structure_packet_declares_scope():
    r=record('');r.update(record_kind='structure_only',structure={'schema':'future/1'})
    result=compare(page(),[r])
    assert any(u['code']=='output_structure_schema_unverified' for u in result['unverified'])
    assert any(f['code']=='source_region_unmapped' for f in result['findings'])


def test_geometry_only_repair_invalidates_saved_original_check(system,tmp_path,monkeypatch):
    from .test_original_page_verification import prepare
    from .test_table_geometry import request as geometry_request
    s,did,source,h,run=prepare(system,tmp_path,monkeypatch)
    s.install(did,table_document()['units'],[])
    original=deepcopy(get(system,'table')['original'])
    first=run();artifact=first['report']['evidence_artifact'];saved=(s.root/artifact['path']).read_bytes()
    r=geometry_request(system)
    r['source_sha256']=h
    for c in r['table_geometry']['cells']:c['column']=1-c['column']
    s.decision(r)
    cov=get(system,first['unit_id'])
    assert cov['source_verification']['stale'] and not cov['content_human']
    assert get(system,'row')['content_status']=='pending'
    second=run()
    assert not second['report']['stale']
    assert any(f['code']=='output_table_position_order_conflict' for f in second['report']['findings'])
    assert (s.root/artifact['path']).read_bytes()==saved
    assert get(system,'table')['original']==original
    assert len([e for e in s.feed()['events'] if e['kind']=='source_verification'])==2
