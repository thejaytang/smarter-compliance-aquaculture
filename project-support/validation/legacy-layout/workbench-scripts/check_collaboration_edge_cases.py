"""Isolated real-adapter collaboration journeys; no normal stores or browser roots.

Run: PYTHONPATH=workbench/backend/application workbench/.venv/bin/python workbench/scripts/check_collaboration_edge_cases.py
This uses macOS local processes. It never claims actual Windows verification.
"""
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import time
import traceback
from types import SimpleNamespace
import uuid

from local_workbench.adapter import System1, System2
from local_workbench.collaboration import Collaboration, PackageSourceAdapter, fingerprint
from local_workbench.collaboration_exchange import pack, unpack
from local_workbench.store import Store
from check_offline_collaboration import ROOT, FIX, ACTOR, A, B, uid, save, take

REPORT = ROOT/'project-support/reports/offline-collaboration-20260912'
RUN = FIX/('edge-'+uid())
CONFIG = RUN/'config/config.json'


def setup():
    RUN.mkdir(parents=True)
    shutil.copytree(FIX/'Data', RUN/'Data')
    shutil.copy2(FIX/'source-register.xlsx', RUN/'source-register.xlsx')
    (RUN/'governance').mkdir();(RUN/'config').mkdir()
    with sqlite3.connect((FIX/'governance/governance.sqlite').as_uri()+'?mode=ro', uri=True) as src:
        with sqlite3.connect(RUN/'governance/governance.sqlite') as dst: src.backup(dst)
    for original in (FIX/'governance').iterdir():
        if original.suffix == '.xlsx': shutil.copy2(original, RUN/'governance'/original.name)
    raw = json.loads((FIX/'config/config.json').read_text())
    CONFIG.write_text(json.dumps(raw), encoding='utf-8')


def app(name, reviewer=False):
    root=RUN/name;runtime=root/'runtime';runtime.mkdir(parents=True,exist_ok=True)
    source=System1(ROOT/'system1',CONFIG)
    a=SimpleNamespace(root=root,runtime=runtime,store=Store(runtime/'workbench.sqlite'),adapter=source,
        system2=System2(ROOT/'system2',ROOT/'system1',source.config,runtime/'system2-workflow'),snapshot_time=0)
    a.collaboration=Collaboration(a,reviewer)
    if reviewer:a.adapter=PackageSourceAdapter(a.collaboration,ROOT/'system1')
    return a


def source_change(source_id, updates):
    """Simulated independent local operator/source change, using the owning store."""
    program = '''
import json,sys
from pathlib import Path
import source_updater as u
import human_operations as h
from system1.workbook_guard import exclusive_process_lock
cfg=u.read_config(Path(sys.argv[1]));request=json.load(sys.stdin)
with exclusive_process_lock(cfg['log_root']/'.system1-run.lock'),u.registry_lock(cfg,12):
 wb=u.open_registry(cfg);stamp=u.registry_revision(cfg);wb._governance_actor='isolated_edge_fixture'
 ws=wb[cfg['sheet_name']];hs=u.workbook_headers(ws,2);row=h.find_source_row(ws,hs,request['source_id'])
 for key,value in request['updates'].items():ws.cell(row,hs[key]).value=value
 u.save_registry(wb,cfg,stamp);wb.close()
'''
    subprocess.run([str(ROOT/'workbench/backend/system1/Code/.venv/bin/python'),'-c',program,str(CONFIG)],
        input=json.dumps({'source_id':source_id,'updates':updates}), text=True, check=True,
        cwd=ROOT,env=dict(os.environ,PYTHONPATH=str(ROOT/'workbench/backend/system1/Code/src')),capture_output=True)


def write_blocks(c, actor, material, blocks, association=True):
    result=c.material_action(actor,'save',{'material_id':material['id'],'expected_revision':material['revision'],
        'request_id':uid(),'blocks':blocks,'issues':material['issues'],'association_reviewed':association})
    assert result['status']=='applied',result
    return result['material']


def setup_material(main, sid, blocks):
    c=main.collaboration
    material=c.material_action(ACTOR,'open',{'source_id':sid,'request_id':uid()})
    created=blocks(material)
    write_blocks(c,ACTOR,material,created)
    result=take(c,c.prepare_own(ACTOR,{'source_id':sid,'material_id':material['id']}))
    return result['material']


def pdf_blocks(material):
    assert len(material['scope'])==3,material['scope']
    return [{'id':'p'+str(i+1),'type':'text','text':'Isolated transcription page '+str(i+1),
        'source_refs':[{'scope_id':scope['id'],'page':i+1}]} for i,scope in enumerate(material['scope'])]


def import_work(main, reviewer, actor, sid, mid=None):
    blob,_=main.collaboration.work_export(ACTOR,{'source_id':sid,'material_id':mid})
    result=reviewer.collaboration.import_package(actor,blob)
    assert result['status']=='imported',result
    return blob


def submit(main, reviewer, actor, sid, mid=None):
    blob,_=reviewer.collaboration.submission_export(actor,{'source_id':sid,'material_id':mid,'summary':'Isolated edge case'})
    receipt=main.collaboration.import_package(ACTOR,blob)
    return main.collaboration.preview(ACTOR,{'submission_id':receipt['id']}),blob


def confirm_personal(c, actor, material):
    result=c.material_action(actor,'confirm',{'request_id':uid(),'material_id':material['id'],
        'expected_revision':material['revision'],'explicit_confirmation':True,
        'checked_scope':[s['id'] for s in material['scope']], 'omissions_checked':True,
        'dependencies_checked':True,'association_reviewed':True})
    assert result['status']=='applied',result
    return result['material']


def owner_hash(main):
    return {str(p):sha256(p.read_bytes()).hexdigest() for p in [RUN/'governance/governance.sqlite',
        main.system2.runtime/'workflow.sqlite'] if p.exists()}


def source_draft(c, actor, sid, mutate):
    draft=c.source_draft(actor,sid);review=deepcopy(draft['source_review']);mutate(review)
    result=c.save_source(actor,{'source_id':sid,'expected_revision':draft['draft_revision'],'source_review':review})
    assert result['status']=='saved_personal',result
    return result


def serial_ranges():
    main=app('serial-main');ra=app('serial-a',True);rb=app('serial-b',True)
    c=main.collaboration;material=setup_material(main,'TS003',pdf_blocks);mid=material['id']
    import_work(main,ra,A,'TS003',mid)
    am=confirm_personal(ra.collaboration,A,ra.collaboration.read_material(A,mid))
    receipt=take(c,submit(main,ra,A,'TS003',mid)[0]);master=receipt['material']
    assert master['checked_scope']==['page:1','page:2','page:3'],master['checked_scope']
    assert master['confirmation'] is None
    assert {v['actor'] for v in master['review_checks'].values()}=={A}
    import_work(main,rb,B,'TS003',mid)
    bm=save(rb.collaboration,B,rb.collaboration.read_material(B,mid),'Daniel corrected page 1',0)
    assert bm['checked_scope']==['page:2','page:3'],bm['checked_scope']
    after=take(c,submit(main,rb,B,'TS003',mid)[0])['material']
    assert after['checked_scope']==['page:2','page:3'],after['checked_scope']
    assert {v['actor'] for v in after['review_checks'].values()}=={A}
    history=main.system2.call('material_export',request={'material_id':mid})['history']
    assert any(r.get('review_checks',{}).get('page:1',{}).get('actor')==A for r in history)
    assert after['confirmation'] is None
    return {'material_id':mid,'retained_scope':after['checked_scope'],'retained_reviewers':after['review_checks'],
        'ana_confirmed_revision':am['revision'],'history_count':len(history)}


def disjoint_blocks_cells():
    main=app('disjoint-main');ra=app('disjoint-a',True);rb=app('disjoint-b',True);c=main.collaboration
    def cells(material):
        scope=material['scope'][0]['id'];refs=[{'scope_id':scope}]
        return [{'id':'table-1','type':'table','text':'Isolated measurement table','source_refs':refs,
                 'table':{'rows':[['A0','B0'],['C0','D0']],'merges':[],'notes':[]}},
                {'id':'text-a','type':'text','text':'Base paragraph A','source_refs':refs},
                {'id':'text-b','type':'text','text':'Base paragraph B','source_refs':refs}]
    material=setup_material(main,'TS002',cells);mid=material['id']
    blob,_=c.work_export(ACTOR,{'source_id':'TS002','material_id':mid})
    for reviewer,actor,index,value in [(ra,A,0,'Ana'),(rb,B,1,'Daniel')]:
        reviewer.collaboration.import_package(actor,blob);m=reviewer.collaboration.read_material(actor,mid)
        blocks=deepcopy(m['blocks']);blocks[0]['table']['rows'][0][index]=value+' cell'
        blocks[index+1]['text']=value+' paragraph';write_blocks(reviewer.collaboration,actor,m,blocks)
    pa,_=submit(main,ra,A,'TS002',mid);pb_blob=rb.collaboration.submission_export(B,{'source_id':'TS002','material_id':mid})[0]
    take(c,pa);incoming=c.import_package(ACTOR,pb_blob);pb=c.preview(ACTOR,{'submission_id':incoming['id']})
    assert not pb['unresolved'],pb['unresolved']
    result=take(c,pb)['material']
    assert result['blocks'][0]['table']['rows'][0]==['Ana cell','Daniel cell']
    assert [b['text'] for b in result['blocks'][1:]]==['Ana paragraph','Daniel paragraph']
    contributors={r.get('actor') for r in result.get('collaboration_provenance',[])}
    assert {A,B} <= contributors, result.get('collaboration_provenance')
    return {'material_id':mid,'row':result['blocks'][0]['table']['rows'][0],
        'provenance':result['collaboration_provenance']}


def source_only_conflict_partial():
    source_change('TS001',{'scope_relevance':'MEDIUM','operator_selection_decision':'PENDING'})
    main=app('source-main');ra=app('source-a',True);rb=app('source-b',True);c=main.collaboration
    blob,_=c.work_export(ACTOR,{'source_id':'TS001'})
    assert unpack(blob)['metadata']['material'] is None
    ra.collaboration.import_package(A,blob);rb.collaboration.import_package(B,blob)
    def full(review):
        review['fields']['issuer']='Ana verified issuer';review['scores']={k:'HIGH' for k in review['scores']}
        review['selection']='INCLUDE';review['note']='Ana checked the official provenance.'
    def partial(review):
        review['fields']['issuer']='Daniel proposed issuer';review['scores']={k:'' for k in review['scores']}
        review['scores']['authority_quality']='LOW';review['selection']='PENDING'
        review['note']='Daniel partially checked authority and left the remaining ratings unfinished.'
    source_draft(ra.collaboration,A,'TS001',full);source_draft(rb.collaboration,B,'TS001',partial)
    pa,_=submit(main,ra,A,'TS001');bb=rb.collaboration.submission_export(B,{'source_id':'TS001'})[0]
    ra_receipt=take(c,pa);assert ra_receipt['source_status']=='applied'
    b_id=c.import_package(ACTOR,bb)['id'];pb=c.preview(ACTOR,{'submission_id':b_id})
    conflicts=[d for d in pb['differences'] if d['conflict']]
    assert any('issuer' in d['path'] for d in conflicts),conflicts
    assert any('scores' in d['path'] for d in conflicts),conflicts
    pb=c.resolve(ACTOR,{'merge_id':pb['merge_id'],'decisions':{d['id']:{'action':'incoming'} for d in conflicts}})
    receipt=c.adopt(ACTOR,{'merge_id':pb['merge_id'],'request_id':uid()})
    assert receipt['status']=='adopted_partial' and receipt['source_status']=='saved_partial',receipt
    source=c.source('TS001')
    assert source['issuer']=='Daniel proposed issuer'
    assert all(source[k]=='HIGH' for k in ('authority_quality','scope_relevance','version_currency','traceability','access_permission'))
    assert source['effective_selection']=='INCLUDE'
    assert 'Ana checked' in source['notes'] and 'Daniel partially' in source['notes']
    return {'conflict_paths':[d['path'] for d in conflicts],'receipt':receipt,'append_only_notes':source['notes']}


def stale_preview():
    main=app('stale-main');ra=app('stale-a',True);c=main.collaboration
    material=setup_material(main,'TS003',pdf_blocks);mid=material['id'];import_work(main,ra,A,'TS003',mid)
    save(ra.collaboration,A,ra.collaboration.read_material(A,mid),'Incoming pending change')
    preview,_=submit(main,ra,A,'TS003',mid)
    current=c.read_material(ACTOR,mid,view='master');blocks=deepcopy(current['blocks']);blocks[1]['text']='New independent main change'
    main.system2.call('material_save',request={'request_id':uid(),'actor':ACTOR,'material_id':mid,
        'expected_revision':current['revision'],'blocks':blocks})
    before=owner_hash(main)
    result=c.adopt(ACTOR,{'merge_id':preview['merge_id'],'request_id':uid()})
    assert result['status']=='conflict',result
    assert owner_hash(main)==before
    return {'material_id':mid,'receipt':result}


def unknown_and_reused():
    main=app('unknown-main');ra=app('unknown-a',True);c=main.collaboration
    material=setup_material(main,'TS003',pdf_blocks);mid=material['id'];import_work(main,ra,A,'TS003',mid)
    blob=ra.collaboration.submission_export(A,{'source_id':'TS003','material_id':mid})[0]
    before=owner_hash(main);receipt=c.import_package(ACTOR,blob);assert owner_hash(main)==before
    decoded=unpack(blob);metadata=deepcopy(decoded['metadata']);metadata['summary']='Different content under the same id'
    altered=pack('submission',metadata,{})
    try:c.import_package(ACTOR,altered)
    except ValueError as exc:reuse_error=str(exc)
    else:raise AssertionError('Reused id with different content was accepted')
    assert owner_hash(main)==before
    metadata['id']=uid();metadata['base']['source']['version']='Unknown independent baseline'
    metadata['base_digest']=fingerprint(metadata['base'])
    unknown=pack('submission',metadata,{})
    imported=c.import_package(ACTOR,unknown)
    assert c.get('submission',imported['id'])['status']=='unknown_baseline'
    try:c.preview(ACTOR,{'submission_id':imported['id']})
    except ValueError as exc:unknown_error=str(exc)
    else:raise AssertionError('Unknown baseline was silently merged')
    assert owner_hash(main)==before
    return {'reused_id_error':reuse_error,'unknown_baseline_error':unknown_error,'imported_id':receipt['id']}


def source_then_material_failure():
    main=app('resume-main');ra=app('resume-a',True);c=main.collaboration
    material=setup_material(main,'TS003',pdf_blocks);mid=material['id'];import_work(main,ra,A,'TS003',mid)
    save(ra.collaboration,A,ra.collaboration.read_material(A,mid),'Saved incoming content after source receipt')
    source_draft(ra.collaboration,A,'TS003',lambda r:r.update(note='Isolated coordinator adopted source note before an injected material interruption.'))
    preview,_=submit(main,ra,A,'TS003',mid);rid=uid();original=main.system2.call
    def fail(command,**kwargs):
        if command=='material_adopt-master':raise RuntimeError('Injected interruption after source commit, before material write')
        return original(command,**kwargs)
    main.system2.call=fail
    try:
        try:c.adopt(ACTOR,{'merge_id':preview['merge_id'],'request_id':rid})
        except RuntimeError:pass
        else:raise AssertionError('Injected material interruption did not run')
    finally:main.system2.call=original
    merge=c.get('merge',preview['merge_id']);assert merge['source_receipt']['status']=='applied'
    assert not merge.get('material_receipt') and not c.get('adoption_receipt',rid)
    source_hash=sha256((RUN/'governance/governance.sqlite').read_bytes()).hexdigest()
    result=c.adopt(ACTOR,{'merge_id':preview['merge_id'],'request_id':rid})
    assert result['status']=='adopted',result
    assert sha256((RUN/'governance/governance.sqlite').read_bytes()).hexdigest()==source_hash
    assert result['material']['blocks'][0]['text']=='Saved incoming content after source receipt'
    assert c.adopt(ACTOR,{'merge_id':preview['merge_id'],'request_id':rid})==result
    return {'material_id':mid,'source_receipt':merge['source_receipt'],'replayed_final_status':result['status']}


def changed_original():
    main=app('original-main');ra=app('original-a',True);c=main.collaboration
    material=setup_material(main,'TS003',pdf_blocks);mid=material['id'];import_work(main,ra,A,'TS003',mid)
    save(ra.collaboration,A,ra.collaboration.read_material(A,mid),'Reviewed old original only')
    preview,_=submit(main,ra,A,'TS003',mid);source=c.source('TS003')
    original=RUN/'Data'/source['folder_code']/source['stored_filename'];before_original=original.read_bytes()
    new_name='TS003-002_edge-version.pdf';changed=before_original+b'\n% isolated later original version\n'
    (original.parent/new_name).write_bytes(changed)
    source_change('TS003',{'snapshot_id':'TS003-002','stored_filename':new_name,'content_hash':sha256(changed).hexdigest()})
    result=c.adopt(ACTOR,{'merge_id':preview['merge_id'],'request_id':uid()})
    assert result['status']=='conflict',result
    historical=c.read_material(ACTOR,mid,view='master');assert historical['source_stale']
    assert historical['blocks'][0]['text']!='Reviewed old original only'
    try:main.system2.call('material_confirm',request={'request_id':uid(),'actor':ACTOR,'material_id':mid,
        'expected_revision':historical['revision'],'explicit_confirmation':True,'checked_scope':['page:1','page:2','page:3']})
    except (ValueError,RuntimeError) as exc:error=str(exc)
    else:raise AssertionError('Historical original was incorrectly confirmed as current')
    assert original.read_bytes()==before_original
    return {'material_id':mid,'adoption_status':result['status'],'old_source_stale':historical['source_stale'],
        'confirmation_rejection':error,'original_preserved':True}


def run():
    setup();REPORT.mkdir(parents=True,exist_ok=True)
    report={'status':'RUNNING','platform':'macOS','actual_windows':'NOT_EXERCISED',
        'scope':'Isolated real System1/System2 adapters and offline work packages; no browser interaction',
        'run_root':str(RUN),'checks':[]}
    log=REPORT/'edge-cases.log';log.write_text('Run root: '+str(RUN)+'\n',encoding='utf-8')
    for case in [serial_ranges,disjoint_blocks_cells,source_only_conflict_partial,stale_preview,
                 unknown_and_reused,source_then_material_failure,changed_original]:
        started=time.monotonic();print('START '+case.__name__,flush=True)
        try:entry={'case':case.__name__,'status':'PASS','evidence':case()}
        except Exception as exc:
            entry={'case':case.__name__,'status':'FAIL','error':str(exc),'traceback':traceback.format_exc()}
        entry['seconds']=round(time.monotonic()-started,3);report['checks'].append(entry)
        text=json.dumps(entry,ensure_ascii=False,indent=2);print(text,flush=True)
        with log.open('a',encoding='utf-8') as output:output.write(text+'\n')
        (REPORT/'edge-cases.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    report['status']='PASS' if all(c['status']=='PASS' for c in report['checks']) else 'FAIL'
    (REPORT/'edge-cases.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('FINAL '+report['status'],flush=True)
    return 0 if report['status']=='PASS' else 1

if __name__=='__main__':raise SystemExit(run())
