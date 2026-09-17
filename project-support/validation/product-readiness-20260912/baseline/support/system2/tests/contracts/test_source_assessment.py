"""Known engineering labels test counting and integrity, not source accuracy."""
from copy import deepcopy
import pytest
from pdf_extraction.contracts.hashing import digest
from pdf_extraction.evaluation.source_assessment import evaluate, DIMENSIONS


def fixture():
    records=[dict(id='output',unit_id='unit',text='5',references=[dict(page_index=0,bbox=[10,10,20,20])])]
    reference=dict(schema='pdf-source-reference/1',source_sha256='a'*64,pages=[0],status='frozen_candidate',
        origin='engineering_fixture',regions=[dict(id='original',page_index=0,bbox=[10,10,20,20],text='6'),
            dict(id='omitted-original',page_index=0,bbox=[10,40,180,60],text='Footnote: this exception does not apply.')],
        page_survey=[dict(page_index=0,complete=True,dimensions=sorted(DIMENSIONS),unverified_regions=[])])
    verification=dict(source_sha256='a'*64,page_index=0,input_sha256=digest(records),
        findings=[dict(id=i) for i in ['found','repeat','false']],
        unverified=[dict(code='entire_page_requires_human_review')])
    errors=[dict(id='number',category='critical_token',severity='critical',region_ids=['original'],output_ids=['output'],explanation='Known test substitution 6 to 5.'),
            dict(id='missing',category='text_omission',severity='critical',region_ids=['omitted-original'],output_ids=[],explanation='Known synthetic omitted region without a finding.')]
    assessment=dict(schema='pdf-source-assessment/1',source_sha256='a'*64,status='complete',evidence_class='synthetic',
        reference_sha256=digest(reference),records_sha256=digest(records),verification_sha256=digest(verification),
        reviewed_region_ids=['original','omitted-original'],reviewed_output_ids=['output'],reviewed_dimensions=sorted(DIMENSIONS),unresolved=[],
        errors=errors,finding_decisions=[dict(id='found',verdict='matched',error_ids=['number'],localization='incorrect'),
            dict(id='repeat',verdict='duplicate',error_ids=['number'],localization='correct'),
            dict(id='false',verdict='false_positive',error_ids=[])])
    return reference,assessment,records,verification


def run(values):return evaluate(*values,source_sha256='a'*64)


def test_original_only_miss_duplicates_and_localization_are_separate():
    r=run(fixture());m=r['diagnostic_metrics']
    assert m['verifier_recall']==.5
    assert m['finding_relevance_precision']==pytest.approx(2/3)
    assert m['actionable_finding_precision']==pytest.approx(1/3)
    assert m['localized_error_recall']==.5
    assert m['critical_miss_ids']==['missing']
    assert m['duplicate_findings']==1 and m['false_positive_findings']==1
    assert r['counts']['unverified_scope_items']==1
    assert r['independent_metrics'] is None and r['independent_acceptance']=='not_assessed'
    assert m['by_error_category']['cross_page_link']['recall'] is None


@pytest.mark.parametrize('change,reason',[
    (lambda r,a,o,v:a.update(reviewed_region_ids=[]),'original_region_review_incomplete'),
    (lambda r,a,o,v:a.update(reviewed_output_ids=[]),'output_review_incomplete'),
    (lambda r,a,o,v:a['finding_decisions'].pop(),'finding_adjudication_incomplete'),
    (lambda r,a,o,v:a.update(unresolved=['A note link is unclear']),'assessment_has_unresolved_questions'),
    (lambda r,a,o,v:a.update(status='draft'),'assessment_not_complete'),
    (lambda r,a,o,v:r['page_survey'][0].update(complete=False),'original_page_survey_incomplete'),
])
def test_partial_review_never_gets_quality_metrics(change,reason):
    values=fixture();change(*values);values[1]['reference_sha256']=digest(values[0])
    result=run(values)
    assert reason in result['incomplete'] and result['diagnostic_metrics'] is None


@pytest.mark.parametrize('change,reason',[
    (lambda r,a,o,v:r['regions'][0].update(text='Changed reference'),'reference_binding_mismatch'),
    (lambda r,a,o,v:o[0].update(text='Changed output'),'output_binding_mismatch'),
    (lambda r,a,o,v:v['findings'].append(dict(id='other')),'verification_binding_mismatch'),
    (lambda r,a,o,v:a.update(source_sha256='b'*64),'source_binding_mismatch'),
    (lambda r,a,o,v:a['errors'][0].update(severity='minor'),'critical_token_cannot_be_downgraded'),
    (lambda r,a,o,v:a['finding_decisions'][1].update(verdict='matched'),'one_error_cannot_credit_multiple_findings'),
    (lambda r,a,o,v:a['errors'][0].update(region_ids=['invented']),'error_evidence_reference_missing'),
])
def test_mismatches_and_double_counting_are_rejected(change,reason):
    values=fixture();change(*values)
    with pytest.raises(ValueError,match=reason):run(values)


def test_no_events_is_unknown_not_perfect():
    r,a,o,v=fixture();v['findings']=[];a['verification_sha256']=digest(v)
    a.update(errors=[],finding_decisions=[])
    m=run((r,a,o,v))['diagnostic_metrics']
    assert m['verifier_recall'] is None and m['finding_relevance_precision'] is None


def test_wrong_page_and_support_only_error_cannot_change_denominator():
    r,a,o,v=fixture();r['pages']=[1];a['reference_sha256']=digest(r)
    with pytest.raises(ValueError,match='single_frozen_page_check'):run((r,a,o,v))
    r,a,o,v=fixture();r['supporting_pages']=[1];r['regions'].append(dict(id='context',page_index=1,bbox=[10,10,20,20]))
    a['reference_sha256']=digest(r);a['errors'][1]['region_ids']=['context']
    with pytest.raises(ValueError,match='error_outside_evaluated_page'):run((r,a,o,v))


def test_file_claim_of_human_authority_does_not_authenticate_independence():
    r,a,o,v=fixture();r['origin']='workbench_human';r['reviewer']='Claimed reviewer'
    r['receipt']={'independent':True};a['reference_sha256']=digest(r)
    assert run((r,a,o,v))['independent_metrics'] is None


def test_offline_cli_binds_original_and_does_not_replace_evidence(tmp_path):
    from hashlib import sha256
    import json
    from pdf_extraction.evaluation.source_assessment_cli import main
    r,a,o,v=fixture();original=tmp_path/'original.pdf';original.write_bytes(b'%PDF-engineering-fixture')
    for value in (r,a,v):value['source_sha256']=sha256(original.read_bytes()).hexdigest()
    a['reference_sha256']=digest(r);a['verification_sha256']=digest(v)
    args=['--original',str(original)]
    for key,value in [('reference',r),('assessment',a),('records',o),('verification',v)]:
        path=tmp_path/(key+'.json');path.write_text(json.dumps(value));args.extend(['--'+key,str(path)])
    target=tmp_path/'result.json';args.extend(['--output',str(target)])
    assert main(args)==0
    saved=target.read_bytes()
    assert json.loads(saved)['independent_metrics'] is None
    with pytest.raises(FileExistsError):main(args)
    assert target.read_bytes()==saved
    original.write_bytes(b'%PDF-changed-fixture')
    with pytest.raises(ValueError,match='source_binding_mismatch'):main(args)
    assert target.read_bytes()==saved
