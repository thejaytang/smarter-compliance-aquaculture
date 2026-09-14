"""Three independent local workspaces; synthetic source TS001 only.
Run with workbench environment and PYTHONPATH=workbench/src.
Does not exercise or claim actual Windows acceptance.
"""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace
import uuid
from local_workbench.adapter import System1, System2
from local_workbench.collaboration import Collaboration, PackageSourceAdapter
from local_workbench.store import Store

ROOT=Path(__file__).resolve().parents[2]
FIX=ROOT/'workbench/runtime/offline-collaboration-acceptance'
ACTOR='Weijie Tang';A='Ana Jokic';B='Daniel Restad'
def uid():return str(uuid.uuid4())
def app(name, reviewer=False):
    root=FIX/name;runtime=root/'runtime';runtime.mkdir(parents=True,exist_ok=True)
    source=System1(ROOT/'system1',FIX/'config/config.json')
    a=SimpleNamespace(root=root,runtime=runtime,store=Store(runtime/'workbench.sqlite'),adapter=source,
        system2=System2(ROOT/'system2',ROOT/'system1',source.config,runtime/'system2-workflow'),snapshot_time=0)
    a.collaboration=Collaboration(a,reviewer)
    if reviewer:a.adapter=PackageSourceAdapter(a.collaboration,ROOT/'system1')
    return a

def save(c,actor,m,text,index=0,checked=None):
    blocks=deepcopy(m['blocks']);blocks[index]['text']=text
    r=c.material_action(actor,'save',{'material_id':m['id'],'expected_revision':m['revision'],
        'request_id':uid(),'blocks':blocks,'issues':m['issues'],
        'checked_scope':checked or [],'association_reviewed':True})
    assert r['status']=='applied',r
    return r['material']

def take(c,preview):
    if preview['unresolved']:
        preview=c.resolve(ACTOR,{'merge_id':preview['merge_id'],
            'decisions':{key:{'action':'incoming'} for key in preview['unresolved']}})
    result=c.adopt(ACTOR,{'merge_id':preview['merge_id'],'request_id':uid()})
    assert result['status']=='adopted',result
    return result

def run():
    identity=uid()[:8]
    main=app('coordinator-'+identity);c=main.collaboration
    ra=app('reviewer-a-'+identity,True);rb=app('reviewer-b-'+identity,True)
    m=c.material_action(ACTOR,'open',{'source_id':'TS001','request_id':uid()});mid=m['id']
    baseline=c.read_material(ACTOR,mid,view='master');assert not baseline['blocks']
    r=c.material_action(ACTOR,'extract',{'material_id':mid,'expected_revision':m['revision'],'request_id':uid()})
    c.tick();m=c.read_material(ACTOR,mid)
    candidate=next(x for x in m['candidates'] if x['status'] in ('ready','partial'))
    detail=c.personal_adapter(ACTOR,mid).call('material_candidate',material_id=mid,candidate_id=candidate['id'])
    print('candidate keys',list(detail),flush=True)
    result=c.material_action(ACTOR,'adopt',{'material_id':mid,'expected_revision':m['revision'],
        'request_id':uid(),'candidate_id':candidate['id'],'action':'adopt','reviewed_against_source':True})
    assert result['status']=='applied',result
    assert not c.read_material(ACTOR,mid,view='master')['blocks'],'personal extraction changed master'
    take(c,c.prepare_own(ACTOR,{'source_id':'TS001','material_id':mid}))
    first=c.read_material(ACTOR,mid,view='master');assert first['blocks']
    work,_=c.work_export(ACTOR,{'source_id':'TS001','material_id':mid})
    ra.collaboration.import_package(A,work);rb.collaboration.import_package(B,work)
    for reviewer,actor,text in [(ra,A,'Ana: corrected water record'),(rb,B,'Daniel: different water record')]:
        m=reviewer.collaboration.read_material(actor,mid)
        save(reviewer.collaboration,actor,m,text)
        assert c.read_material(ACTOR,mid,view='master')['blocks'][0]['text']==first['blocks'][0]['text']
    ba,_=ra.collaboration.submission_export(A,{'source_id':'TS001','material_id':mid,'summary':'A partial review'})
    bb,_=rb.collaboration.submission_export(B,{'source_id':'TS001','material_id':mid,'summary':'B parallel review'})
    ia=c.import_package(ACTOR,ba);ib=c.import_package(ACTOR,bb)
    assert c.import_package(ACTOR,ba)['status']=='already_imported'
    pa=c.preview(ACTOR,{'submission_id':ia['id']});assert not pa['unresolved'],pa['unresolved']
    assert pa['material']['blocks'][0]['text']=='Ana: corrected water record'
    take(c,pa)
    pb=c.preview(ACTOR,{'submission_id':ib['id']});assert pb['unresolved'],'same paragraph must conflict'
    d=next(x for x in pb['differences'] if x['conflict'])
    assert d['current']=='Ana: corrected water record' and d['incoming']=='Daniel: different water record',d
    pb=c.resolve(ACTOR,{'merge_id':pb['merge_id'],'decisions':{d['id']:{'action':'edit','value':'Coordinator: combined review'}}})
    rid=uid();receipt=c.adopt(ACTOR,{'merge_id':pb['merge_id'],'request_id':rid})
    assert receipt['status']=='adopted',receipt
    assert c.adopt(ACTOR,{'merge_id':pb['merge_id'],'request_id':rid})==receipt
    current=c.read_material(ACTOR,mid,view='master');assert current['blocks'][0]['text']=='Coordinator: combined review'
    assert current['content_status']!='content_review_complete'
    historical=main.system2.call('material_export',request={'material_id':mid})['history']
    assert any(x['blocks'] and x['blocks'][0]['text']=='Ana: corrected water record' for x in historical)
    restored=app('reviewer-a-'+identity,True).collaboration.read_material(A,mid)
    assert restored['blocks'][0]['text']=='Ana: corrected water record'
    result={'status':'PASS','scope':'macOS isolated three-workspace collaboration; Windows not exercised',
        'coordinator':str(main.root),'reviewer_a':str(ra.root),'reviewer_b':str(rb.root),
        'material_id':mid,'checks':['real extraction only in personal branch','work package independent imports','personal saves preserve master',
        'disjoint prefill','same paragraph conflict and manual selection','duplicate import and adoption replay','master history retention',
        'partial adoption is not review complete','reviewer restart recovery']}
    (FIX/'latest-check.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2),flush=True)
if __name__=='__main__':run()
