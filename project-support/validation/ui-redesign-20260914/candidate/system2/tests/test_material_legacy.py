from copy import deepcopy
from hashlib import sha256
import json
import sqlite3
import uuid

import pytest

from pdf_extraction.contracts.hashing import encoded
from pdf_extraction.orchestration.material_legacy import legacy_candidate
from pdf_extraction.review.materials import MaterialStore
from pdf_extraction.review import row_store


def unit(identity, text='Original', **extra):
    return dict(id=identity,kind='source_text',version=3,dependencies=[],source_order=0,
        original={'fields':{'body':text},'references':[{'page_index':0}],'structure':[]},**extra)


def setup(root, units, *, indexed=False, file_format='pdf', scope=None):
    store=MaterialStore(root)
    source={'source_id':'TS001','snapshot_id':'TS001-001','content_hash':'a'*64,'file_format':file_format}
    material=store.open(source,'Test material',scope or [{'id':'page:1','kind':'page','location':{'page':1}}])
    doc={'id':'old','source':source,'revision':8,'units':units,'history':[{'actor':'Historical reviewer','action':'correct'}],'issues':[]}
    with store.connect() as db:
        db.execute('CREATE TABLE documents(id TEXT PRIMARY KEY,data TEXT)')
        db.execute('INSERT INTO documents VALUES(?,?)',('old',encoded(doc)))
        if indexed:
            row_store.initialize(db)
            db.execute('INSERT INTO storage_version VALUES(2)')
            for n,u in enumerate(units):
                db.execute('INSERT INTO review_units(document_id,id,ordinal,data,fingerprint) VALUES(?,?,?,?,?)',('old',u['id'],n,encoded(u),'fixture'))
            stripped=dict(doc,units=[])
            db.execute('UPDATE documents SET data=?',(encoded(stripped),))
            db.execute('INSERT INTO review_history VALUES(?,?,?)',('old','history',encoded(doc['history'][0])))
    return store,material


def test_import_hydrates_indexed_effective_corrections_without_any_writes(tmp_path,monkeypatch):
    heading=unit('h','Original heading',edits={'body':'Corrected heading'},source_hierarchy={'type':'heading','heading_level':1},content_human=True)
    paragraph=unit('p','Original paragraph',edits={'body':'Human correction'},source_hierarchy={'type':'paragraph','parent_id':'h'})
    paragraph['source_order']=1
    store,material=setup(tmp_path,[heading,paragraph],indexed=True)
    before=sha256(store.database.read_bytes()).hexdigest()
    from pdf_extraction.domains.requirements import classification
    monkeypatch.setattr(classification,'propose',lambda *a,**k:pytest.fail('Implicit classification'))
    result=legacy_candidate(tmp_path,material)
    assert result['blocks'][0]['text']=='Corrected heading'
    assert result['blocks'][1]['text']=='Human correction'
    assert result['blocks'][1]['parent_id']==result['blocks'][0]['id']
    assert result['blocks'][0]['legacy_provenance']['historical_content_human'] is True
    assert result['provenance']['revision']==8
    assert result['issues']==[]
    assert sha256(store.database.read_bytes()).hexdigest()==before


def test_table_manual_cells_merges_and_derived_rows_not_duplicated(tmp_path):
    table={'row_count':1,'column_count':2,'cells':[{'id':'cell','row':0,'column':0,'row_span':1,'column_span':2,'content':{'native_text':'Original cell'}}]}
    owner=unit('table',json.dumps(table),cell_edits={'cell':'Reviewed merged cell'})
    row=unit('row')
    row['dependencies']=['table']
    row['original']['references']=[{'locator':'cell','page_index':0}]
    image=unit('image','Figure caption',source_hierarchy={'type':'figure'})
    store,material=setup(tmp_path,[owner,row,image])
    result=legacy_candidate(tmp_path,material)
    assert len(result['blocks'])==2
    table=result['blocks'][0]['table']
    assert table['rows']==[['Reviewed merged cell','']]
    assert table['merges']==[{'row':0,'col':0,'rowspan':1,'colspan':2}]
    assert result['blocks'][1]['type']=='image'
    assert result['blocks'][1]['image']['source_ref']['scope_id']=='page:1'


def test_unknown_references_retained_as_draft_and_block_confirmation(tmp_path):
    missing=unit('missing')
    missing['original']['references']=[{'locator':'unknown-opaque-reference'}]
    store,material=setup(tmp_path,[missing])
    result=legacy_candidate(tmp_path,material)
    assert result['blocks'][0]['source_refs']==[]
    assert result['issues']
    assert result['blocks'][0]['legacy_provenance']['effective']['references'][0]['locator']=='unknown-opaque-reference'
    def req(m,**kw):
        return dict(request_id=str(uuid.uuid4()),actor='Isolated Reviewer',material_id=m['id'],expected_revision=m['revision'],**kw)
    saved=store.save(req(material,blocks=result['blocks'],association_reviewed=True))['material']
    with pytest.raises(ValueError,match='original_association'):
        store.confirm(req(saved,explicit_confirmation=True,checked_scope=['page:1']))
    fixed=deepcopy(result['blocks'])
    fixed[0]['source_refs']=[{'scope_id':'page:1','page':1}]
    saved=store.save(req(saved,blocks=fixed,association_reviewed=True))['material']
    assert store.confirm(req(saved,explicit_confirmation=True,checked_scope=['page:1']))['material']['confirmation']


def test_mismatched_source_and_snapshot_are_rejected(tmp_path):
    store,material=setup(tmp_path,[unit('a')])
    material['source']=dict(material['source'],snapshot_id='TS001-002')
    with pytest.raises(ValueError,match='matching_snapshot'):
        legacy_candidate(tmp_path,material)


def test_excel_part_locator_and_html_locator_mapping(tmp_path):
    excel=unit('e')
    excel['original']['references']=[{'locator':'xl/worksheets/sheet1.xml#B2'}]
    store,material=setup(tmp_path/'excel',[excel],file_format='xlsx',scope=[{'id':'sheet:Values','kind':'sheet','location':{'sheet':'Values','part':'xl/worksheets/sheet1.xml'}}])
    mapped=legacy_candidate(store.root,material)['blocks'][0]['source_refs'][0]
    assert mapped['scope_id']=='sheet:Values' and mapped['cell_range']=='B2'
    html=unit('html')
    html['original']['references']=[{'locator':'/html/body/p[1]'}]
    store,material=setup(tmp_path/'html',[html],file_format='html',scope=[{'id':'html:document','kind':'html','location':{}}])
    assert legacy_candidate(store.root,material)['blocks'][0]['source_refs'][0]['scope_id']=='html:document'


def test_dependency_cycle_preserves_content_with_explicit_reassociation_issue(tmp_path):
    a,b=unit('a','A'),unit('b','B')
    a['dependencies']=['b'];b['dependencies']=['a']
    store,material=setup(tmp_path,[a,b])
    result=legacy_candidate(tmp_path,material)
    assert len(result['blocks'])==2
    assert all(b['dependencies']==[] for b in result['blocks'])
    assert any('cycle' in issue['message'] for issue in result['issues'])


@pytest.mark.parametrize('action',['adopt','merge'])
def test_imported_unresolved_issues_survive_adopt_merge_and_retry(tmp_path,action):
    store,material=setup(tmp_path,[unit('a')])
    mapped=legacy_candidate(tmp_path,material)
    issue={'id':'legacy-unresolved','message':'Check missing context against original','resolved':False}
    def req(m,**kw):
        return dict(request_id=str(uuid.uuid4()),actor='Isolated Reviewer',material_id=m['id'],expected_revision=m['revision'],**kw)
    command=req(material)
    imported=store.import_candidate(command,mapped['blocks'],mapped['provenance'],issues=[issue])
    assert store.import_candidate(command,mapped['blocks'],mapped['provenance'],issues=[issue])==imported
    assert imported['candidate']['metadata']['imported_issues']==[issue]
    # Candidate contents and its review needs do not modify the existing draft.
    assert imported['material']['issues']==[]
    # A stale client cannot silently omit or pre-resolve the newly imported issue.
    adopted=store.reconcile(req(imported['material'],candidate_id=imported['candidate']['id'],action=action,
        blocks=mapped['blocks'],reviewed_against_source=True,association_reviewed=True,
        issues=[dict(issue,resolved=True)]))['material']
    assert adopted['issues']==[issue]
    with pytest.raises(ValueError,match='unresolved_content_issues'):
        store.confirm(req(adopted,explicit_confirmation=True,checked_scope=['page:1']))
    saved=store.save(req(adopted,issues=[dict(issue,resolved=True)]))['material']
    assert store.confirm(req(saved,explicit_confirmation=True,checked_scope=['page:1']))['material']['confirmation']
    assert store.history(material['id'])[1]['issues']==[dict(issue,resolved=True)]


def test_keep_retains_imported_issue_in_candidate_history_without_applying_contents(tmp_path):
    store,material=setup(tmp_path,[unit('a')])
    mapped=legacy_candidate(tmp_path,material)
    issue={'id':'mapping','message':'Candidate has unmapped source','resolved':False}
    def req(m,**kw):
        return dict(request_id=str(uuid.uuid4()),actor='Isolated Reviewer',material_id=m['id'],expected_revision=m['revision'],**kw)
    imported=store.import_candidate(req(material),mapped['blocks'],mapped['provenance'],issues=[issue])
    kept=store.reconcile(req(imported['material'],candidate_id=imported['candidate']['id'],action='keep',reviewed_against_source=True))['material']
    assert kept['blocks']==[] and kept['issues']==[]
    assert kept['candidates'][0]['metadata']['imported_issues']==[issue]
