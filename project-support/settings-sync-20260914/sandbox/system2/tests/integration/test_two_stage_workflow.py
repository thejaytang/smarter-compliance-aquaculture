from copy import deepcopy
from hashlib import sha256
import json
import uuid

import pytest

from pdf_extraction.review.workflow import Workflow
from pdf_extraction.verification.acceptance import assess, DEFAULT_POLICY


def request(**kwargs):
    return dict(request_id=str(uuid.uuid4()), actor='Ana Jokic', **kwargs)


def unit(identity, kind='source_clause', score=.96):
    from pdf_extraction.verification.acceptance import ASPECTS
    refs = [{'locator':'source:'+identity}]
    part = {'confidence':score,'calibration_version':'isolated-test-calibration', 'evidence':refs}
    result = {'id':identity,'kind':kind,'original':{'fields':{'identifier':identity,'body':'Fish farms shall keep records.'},
            'references':refs,'structure':[]}, 'content_parts':[dict(part,aspect=a) for a in ASPECTS['content']],
            'requirement_parts':[dict(part,aspect=a) for a in ASPECTS['requirement']],
            'dependencies': [] if kind=='coverage' else ['coverage'], 'blockers':[]}
    # This fixture represents a validated score, so bind the supplied test
    # evidence to its exact proposal. No real calibration is asserted.
    bind_test_scores(result)
    return result


def bind_test_scores(value):
    from pdf_extraction.domains.requirements.classification import propose
    from pdf_extraction.verification.requirement_scores import binding
    proposal=propose(dict(value['original'],kind=value['kind']))
    for part in value['requirement_parts']:
        part.update(method=proposal['method'],rule_binding=binding(value,proposal))


@pytest.fixture
def system(tmp_path):
    store=Workflow(tmp_path)
    source={'source_id':'PA001','snapshot_id':'PA001-001','content_hash':'a'*64,'selection_status':'INCLUDE'}
    identity=store.enqueue([source], request())['documents'][0]
    path=tmp_path/'canonical.json';path.write_text('{}')
    store.install(identity,[unit('coverage','coverage'),unit('clause')],
                  [{'path':str(path),'sha256':sha256(path.read_bytes()).hexdigest()}])
    return store,identity


def current(system):
    return system[0].snapshot()['documents'][0]


def decide(system, action, identity='clause', **kwargs):
    store, docid=system;doc=current(system)
    req=request(document_id=docid,unit_id=identity,revision=doc['revision'],
                policy_revision=store.policy()['revision'],source_sha256=doc['source']['content_hash'],action=action,**kwargs)
    return store.decision(req)


def threshold(system, content, requirement):
    store,_=system
    policy=dict(store.policy(),revision=store.policy()['revision']+1,content=content,requirement=requirement)
    return store.set_policy(policy,request(policy=policy))


def test_two_stages_publish_only_after_both_pass(system):
    assert len(current(system)['published'])==1
    threshold(system,.98,.95)
    assert not current(system)['published']
    decide(system,'accept_content','coverage')
    decide(system,'accept_content')
    assert len(current(system)['published'])==1


def test_raise_and_lower_threshold_events_and_dedup(system):
    threshold(system,.95,.98)
    assert not current(system)['published']
    assert current(system)['units'][1]['requirement_status']=='pending'
    threshold(system,.95,.95)
    assert len(current(system)['published'])==1
    kinds=[e['kind'] for e in system[0].feed()['events']]
    assert kinds.count('suspend')==1
    assert kinds.count('add')==2


def test_named_human_is_retained_at_higher_threshold(system):
    decide(system,'accept_content','coverage')
    decide(system,'classify','coverage',classification='context',note='Document completeness context')
    decide(system,'accept_content')
    decide(system,'classify',classification='requirement')
    threshold(system,1,1)
    assert len(current(system)['published'])==1
    assert current(system)['units'][1]['requirement_confidence']==.96


def test_draft_and_report_survive_lowering(system):
    decide(system,'draft',draft={'body':'draft'})
    threshold(system,.50,.50)
    assert not current(system)['published']
    assert current(system)['units'][1]['drafts']['Ana Jokic']['body']=='draft'


def test_correction_invalidates_second_gate_and_original_unchanged(system):
    old=deepcopy(current(system)['units'][1]['original'])
    decide(system,'correct',fields={'body':'Fish farms shall retain original records.'},note='Compared with source')
    assert not current(system)['published']
    assert current(system)['units'][1]['original']==old
    decide(system,'accept_content')
    assert current(system)['units'][1]['version']==2


def test_unknown_scores_cannot_pass_and_cannot_skip_first_gate(system):
    with system[0].transaction() as db:
        doc=system[0]._load(db,system[1]);doc['units'][1]['content_parts'][0]['confidence']=None
        system[0]._recompute(db,doc,system[0].policy(db));system[0]._save(db,doc)
    with pytest.raises(ValueError,match='content_gate'):
        decide(system,'classify',classification='requirement')
    assert assess([{'confidence':.999,'evidence':['source']}],.95)['status']=='pending'


def test_request_replay_staleness_and_changed_payload(system):
    store,identity=system;doc=current(system)
    req=request(document_id=identity,unit_id='clause',revision=doc['revision'],policy_revision=1,
                source_sha256='a'*64,action='accept_content')
    first=store.decision(req)
    assert store.decision(req)==first
    with pytest.raises(ValueError,match='request_id_reused'):
        store.decision(dict(req,action='reject'))
    with pytest.raises(ValueError,match='stale'):
        store.decision(dict(req,request_id=str(uuid.uuid4())))


def test_source_change_suspends_but_retains_history(system):
    decide(system,'accept_content')
    system[0].reconcile_sources({'PA001':{'effective_selection':'INCLUDE','content_hash':'b'*64}})
    assert not current(system)['published']
    assert current(system)['history']
    assert current(system)['state']=='paused'


def test_tampered_canonical_suspends(system):
    (system[0].root/'canonical.json').write_text('{"changed":true}')
    system[0].reconcile_sources({'PA001':{'effective_selection':'INCLUDE','content_hash':'a'*64}})
    assert not current(system)['published']
    assert 'canonical_artifact_changed' in current(system)['issues']


def test_restart_keeps_receipts_and_publication_cursor(system):
    decide(system,'accept_content')
    cursor=system[0].feed()['cursor']
    reopened=Workflow(system[0].root)
    assert reopened.feed(cursor)['events']==[]
    assert reopened.snapshot()==system[0].snapshot()


def test_split_and_merge_preserve_source_and_require_review(system):
    decide(system,'split',split_parts=['Fish farms shall ', 'keep records.'],note='Correct source item boundary')
    doc=current(system)
    assert len(doc['units'])==4
    assert not doc['published']
    assert doc['units'][1]['original']['fields']['body']=='Fish farms shall keep records.'
    assert all(u.get('content_status')=='pending' for u in doc['units'][2:])


def test_reject_never_means_accepted(system):
    decide(system,'reject',note='Wrong table ownership')
    threshold(system,.01,.01)
    assert not current(system)['published']
    with pytest.raises(ValueError,match='explicit_issue_resolution'):
        decide(system,'accept_content')


def test_missing_coverage_blocks_even_high_scores(system):
    with system[0].transaction() as db:
        doc=system[0]._load(db,system[1]);doc['units'][0]['blockers']=['page_missing']
        system[0]._recompute(db,doc,system[0].policy(db));system[0]._save(db,doc)
    assert not current(system)['published']


@pytest.mark.parametrize('value',[float('nan'),float('inf'),-.1,1.1,True])
def test_invalid_thresholds_rejected(system,value):
    with pytest.raises(ValueError):threshold(system,value,.95)


def test_weekly_sampling_is_persistent_and_wrong_result_reopens(system):
    batches=system[0].weekly_qa()
    assert len(batches[0]['items'])==1
    assert batches[0]['accuracy'] is None
    assert system[0].weekly_qa()==batches
    item=batches[0]['items'][0]
    req=request(week=batches[0]['week'],item_id=item['id'],verdict='INCORRECT',note='Wrong ownership found in source')
    system[0].qa_decision(req)
    assert system[0].qa_decision(req)['status']=='applied'
    assert system[0].weekly_qa()[0]['accuracy']==0
    threshold(system,.01,.01)
    assert not current(system)['published']
    assert 'human_reported_qa_issue' in current(system)['units'][1]['blockers']


def test_simultaneous_writers_do_not_apply_stale_decisions(system):
    from concurrent.futures import ThreadPoolExecutor
    store,identity=system;doc=current(system)
    base=dict(document_id=identity,unit_id='clause',revision=doc['revision'],policy_revision=1,
              source_sha256='a'*64,action='accept_content')
    def apply(req):
        try:return store.decision(req)['status']
        except ValueError:return 'stale'
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(apply,[request(**base),request(**base)]))==['applied','stale']


def test_content_correction_cannot_reuse_prior_requirement_calibration(system):
    decide(system,'correct',fields={'body':'A different obligation shall apply.'},note='Source correction')
    decide(system,'accept_content')
    assert not current(system)['published']
    assert current(system)['units'][1]['requirement_status']=='pending'


def test_validated_score_not_a_model_self_report():
    from pdf_extraction.verification.calibration import calibrate,calibrated_score
    rows=[{'id':str(i),'score':.99,'correct':True,'split':'calibration','label_origin':'independent_human'} for i in range(100)]
    artifact=calibrate(rows,method='frozen-method',scope='html/no/clauses',prediction_hash='a'*64)
    value=calibrated_score(artifact,.99,'frozen-method','html/no/clauses')
    assert .95<value<1
    assert calibrated_score(artifact,.99,'changed-method','html/no/clauses') is None
    with pytest.raises(ValueError):calibrate(rows+rows,method='x',scope='x',prediction_hash='a'*64)


def test_optional_provider_disabled_and_failure_fallback():
    from pdf_extraction.domains.suggestions import Suggestions
    assert Suggestions({}).propose('requirements',[])['mode']=='NO_API'
    assert Suggestions({'enabled':True}).propose('requirements',[])['mode']=='NO_API_FALLBACK'


def test_new_pending_range_preserves_accepted_incremental_items(system):
    store,identity=system
    fresh=unit('coverage-next','coverage',score=None)
    store.install(identity,[fresh],[],complete=False,cursor=3)
    doc=current(system)
    assert len(doc['published'])==1 and not doc['source_complete'] and not doc['complete']
    assert store.feed()['documents'][0]['remaining']>=1


def test_dependency_blocks_classification_until_content_reviewed(system):
    decide(system,'reject','coverage',note='Reading order is unresolved')
    assert current(system)['units'][1]['requirement_status']=='blocked'
    with pytest.raises(ValueError,match='content_gate'):
        decide(system,'classify',classification='requirement')


def test_human_exclusion_emits_withdraw_and_reprocessing_keeps_evidence(system):
    decide(system,'classify',classification='non_requirement',note='The clause is an example.')
    assert any(e['kind']=='withdraw' for e in system[0].feed()['events'])
    doc=current(system)
    system[0].control(request(document_id=doc['id'],revision=doc['revision'],action='reprocess'))
    after=current(system)
    assert not after['units'] and after['state']=='queued'
    assert after['history'] and any(e['kind']=='retired_generation' for e in system[0].feed()['events'])


def test_snapshot_version_change_invalidates_identical_bytes(system):
    system[0].reconcile_sources({'PA001':{'selection_status':'INCLUDE','content_hash':'a'*64,'snapshot_id':'PA001-002'}})
    assert not current(system)['eligible'] and not current(system)['published']


def test_reprocess_discards_inflight_old_generation(system):
    store,identity=system;old=current(system)
    store.control(request(document_id=identity,revision=old['revision'],action='reprocess'))
    assert store.install(identity,[unit('late')],old['canonical'],generation=0)=={'status':'superseded'}
    assert not current(system)['units'] and current(system)['generation']==1
