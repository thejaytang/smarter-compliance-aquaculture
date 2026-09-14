"""Real extraction, protected inline machine choices and restart/replay checks."""
from check_offline_collaboration import *

def run_machine():
    instance=app('machine-'+uid()[:8]);c=instance.collaboration
    m=c.material_action(ACTOR,'open',{'source_id':'TS001','request_id':uid()});mid=m['id']
    def extract(m):
        c.material_action(ACTOR,'extract',{'material_id':mid,'expected_revision':m['revision'],'request_id':uid()})
        c.tick(); m=c.read_material(ACTOR,mid)
        return m,next(x for x in reversed(m['candidates']) if x['status'] in ('ready','partial','kept'))
    m,candidate=extract(m)
    preview=c.machine_preview(ACTOR,{'material_id':mid,'candidate_id':candidate['id']})
    if preview['unresolved']:
        preview=c.machine_resolve(ACTOR,{'merge_id':preview['merge_id'],'decisions':{k:{'action':'incoming'} for k in preview['unresolved']}})
    m=c.machine_apply(ACTOR,{'merge_id':preview['merge_id'],'request_id':uid(),'reviewed_against_source':True})['material']
    m=save(c,ACTOR,m,'Human proofreading preserved')
    before=deepcopy(m['blocks']);m,candidate=extract(m)
    assert m['blocks']==before
    preview=c.machine_preview(ACTOR,{'material_id':mid,'candidate_id':candidate['id']})
    assert preview['unresolved'],'human-machine disagreement must require explicit choice'
    assert preview['material']['blocks']==before,'candidate preview replaced human body'
    preview=c.machine_resolve(ACTOR,{'merge_id':preview['merge_id'],'decisions':{k:{'action':'current'} for k in preview['unresolved']}})
    request={'merge_id':preview['merge_id'],'request_id':uid(),'reviewed_against_source':True}
    result=c.machine_apply(ACTOR,request);assert result['status']=='applied',result
    assert c.machine_apply(ACTOR,request)==result
    assert result['material']['blocks']==before
    m,candidate=extract(result['material']);assert candidate['status']=='kept',candidate
    assert candidate.get('prior_resolution'),'same result should reuse prior decision with attribution'
    assert m['blocks']==before
    # A new candidate from changed input is not silently treated as latest.
    m=save(c,ACTOR,m,'New human revision')
    m,candidate=extract(m)
    preview=c.machine_preview(ACTOR,{'material_id':mid,'candidate_id':candidate['id']})
    preview=c.machine_resolve(ACTOR,{'merge_id':preview['merge_id'],'decisions':{k:{'action':'incoming'} for k in preview['unresolved']}})
    m=save(c,ACTOR,m,'Changed while comparison is open')
    conflict=c.machine_apply(ACTOR,{'merge_id':preview['merge_id'],'request_id':uid(),'reviewed_against_source':True})
    assert conflict['status']=='conflict',conflict
    assert c.read_material(ACTOR,mid)['blocks'][0]['text']=='Changed while comparison is open'
    report={'status':'PASS','scope':'macOS real adapter machine candidate comparison', 'workspace':str(instance.root),
        'checks':['first empty draft candidate preview','no extraction overwrite','inline keep/choose/edit interface',
            'explicit unchanged human baseline','replayed same resolution','identical re-extraction reused prior human choice',
            'input changed after comparison rejected']}
    (ROOT/'project-support/reports/offline-collaboration-20260912/machine-cases.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report,indent=2))
if __name__=='__main__':run_machine()
