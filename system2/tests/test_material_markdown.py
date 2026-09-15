"""Markdown redlines remain material data across saves and historical reads."""
from copy import deepcopy
import uuid
import pytest
from pdf_extraction.review.materials import MaterialStore, validate_blocks

def request(m,blocks):
    return dict(request_id=str(uuid.uuid4()),actor='Isolated Reviewer',material_id=m['id'],expected_revision=m['revision'],blocks=blocks)

@pytest.fixture
def setup(tmp_path):
    store=MaterialStore(tmp_path)
    material=store.open(dict(source_id='markdown-fixture',snapshot_id='one',content_hash='hash',file_format='html'),'Markdown fixture',[dict(id='page:1',kind='page',label='Page 1',location={'page':1})])
    original=dict(id='p',type='text',text='The fish shall swim.',source_refs=[dict(scope_id='page:1',page=1)])
    return store,material,original

def test_markdown_baseline_reopen_history_and_replay(setup):
    store,m,original=setup
    m=store.save(request(m,[original]))['material']
    modified=dict(original,text='The fish shall wait.',markdown=dict(version=1,source='The **fish** shall wait.',baseline='The fish shall swim.',original=deepcopy(original)))
    req=request(m,[modified]);saved=store.save(req);assert store.save(req)==saved
    reopened=MaterialStore(store.root).read(m['id'])
    assert reopened['blocks']==[modified]
    assert reopened['confirmation'] is None
    assert reopened['blocks'][0]['source_refs']==original['source_refs']
    assert store.read(m['id'],revision=m['revision'])['blocks']==[original]
    assert any('/markdown' in x['path'] for x in reopened['collaboration_provenance'])
    modified=deepcopy(modified);modified['text']='The fish shall sleep.';modified['markdown']['source']='The **fish** shall sleep.'
    later=store.save(request(reopened,[modified]))['material']
    assert later['blocks'][0]['markdown']['baseline']=='The fish shall swim.'
    assert later['checked_scope']==[]

def test_deleted_cell_retains_history_and_valid_source(setup):
    store,m,original=setup
    deleted=dict(original,text='',markdown=dict(version=1,source='',baseline=original['text'],original=original))
    saved=store.save(request(m,[deleted]))['material']
    assert saved['blocks'][0]['text']==''
    assert MaterialStore(store.root).read(m['id'])['blocks'][0]['markdown']['original']['text']==original['text']

@pytest.mark.parametrize('bad',[{'version':2,'source':'x','baseline':'y'},{'version':1,'source':[],'baseline':'y'},{'version':1,'source':'x','baseline':'y','original':{'id':'other'}}])
def test_invalid_markdown_does_not_reach_saved_store(setup,bad):
    store,m,original=setup
    with pytest.raises(ValueError,match='invalid_markdown'):
        store.save(request(m,[dict(original,markdown=bad)]))
    assert store.read(m['id'])['blocks']==[]

def test_document_information_edits_keep_body_history_and_role(setup):
    store,m,body=setup
    original=dict(id='metadata',type='text',role='document_information',text='Original title',markdown_source='# Original title',source_refs=deepcopy(body['source_refs']))
    m=store.save(request(m,[original,body]))['material']
    edited=dict(original,text='Corrected title',markdown={'version':1,'source':'# Corrected title','baseline':'# Original title','original':deepcopy(original)})
    saved=store.save(request(m,[edited,body]))['material']
    reopened=MaterialStore(store.root).read(m['id'])
    assert reopened['blocks']==[edited,body]
    assert reopened['confirmation'] is None
    assert store.read(m['id'],revision=m['revision'])['blocks'][0]==original
