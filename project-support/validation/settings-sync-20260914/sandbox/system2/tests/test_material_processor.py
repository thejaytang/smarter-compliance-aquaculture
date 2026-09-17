"""Dormant generic adapter bindings, using synthetic envelopes only."""
from copy import deepcopy

import pytest

from pdf_extraction.review.material_processor import input_envelope, process, validate_output


@pytest.fixture
def material():
    return {'id':'material-a','source':{'source_id':'TS001','snapshot_id':'TS001-001','content_hash':'a'*64},
        'content_revision':4,'source_stale':False,
        'scope':[{'id':'page:1'},{'id':'page:2'}],
        'blocks':[{'id':'b1','type':'text','text':'Confirmed original','source_refs':[{'scope_id':'page:1'}],'dependencies':[]}],
        'confirmation':{'content_revision':4,'actor':'Isolated Reviewer','checked_scope':['page:1','page:2']}}


def test_unavailable_output_echoes_complete_frozen_binding(material):
    envelope=input_envelope(material,request_id='fixture-request')
    result=process(envelope)
    assert validate_output(envelope,result) is result
    assert result['state']=='unavailable' and result['candidate_payload'] is None
    assert result['material_id']==material['id'] and result['source']==material['source']
    assert result['input_hash']==envelope['input_hash'] and result['scope']==envelope['scope']
    material['source']['content_hash']='b'*64
    material['blocks'][0]['text']='Changed after capture'
    assert result['source']['content_hash']=='a'*64
    assert envelope['blocks'][0]['text']=='Confirmed original'
    result['source']['snapshot_id']='mutated output'
    assert envelope['source']['snapshot_id']=='TS001-001'


@pytest.mark.parametrize('field,value',[
    ('material_id','material-b'),('input_revision',5),('input_hash','different-content'),
    ('request_id','other-request'),('scope',['page:1'])])
def test_output_cannot_cross_material_revision_hash_request_or_scope(material,field,value):
    envelope=input_envelope(material,request_id='fixture-request')
    result=process(envelope)
    result[field]=value
    with pytest.raises(ValueError,match='input_identity_mismatch'):
        validate_output(envelope,result)


@pytest.mark.parametrize('field,value',[
    ('source_id','TS002'),('snapshot_id','TS001-002'),('content_hash','b'*64)])
def test_output_rejects_stale_source_identity(material,field,value):
    envelope=input_envelope(material,request_id='fixture-request')
    result=process(envelope)
    result['source'][field]=value
    with pytest.raises(ValueError,match='input_identity_mismatch'):
        validate_output(envelope,result)


@pytest.mark.parametrize('state',['empty','partial','failed','unavailable','candidate'])
def test_run_states_remain_distinct_and_arbitrary_payload_never_auto_adopted(material,state):
    before=deepcopy(material)
    envelope=input_envelope(material,request_id='fixture-request')
    payload={'unknown_future_field':{'nested':[{'arbitrary':7},['preserved',None]]}}
    output=dict(process(envelope),state=state,candidate_payload=payload,
        processor_version='isolated-fixture-only',schema_version='unspecified-fixture')
    result=validate_output(envelope,output)
    assert result is output and result['candidate_payload'] is payload
    assert result['state']==state and result['human_adoption_required'] is True
    assert material==before
    with pytest.raises(ValueError,match='cannot_confirm_human'):
        validate_output(envelope,dict(output,human_confirmed=True))


def test_input_hash_binds_scope_even_when_identical_blocks_are_selected(material):
    whole=input_envelope(material,request_id='fixture-request')
    first=input_envelope(material,request_id='fixture-request',scope_ids=['page:1'])
    assert whole['blocks']==first['blocks']
    assert whole['input_hash']!=first['input_hash']
    changed=deepcopy(material)
    changed['blocks'][0]['text']='Another confirmed input with same revision number'
    assert input_envelope(changed,request_id='fixture-request')['input_hash']!=whole['input_hash']
