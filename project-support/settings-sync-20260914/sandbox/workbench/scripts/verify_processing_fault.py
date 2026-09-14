"""Kill one owned parser subprocess after real output, then resume its durable candidate."""
from pathlib import Path
import hashlib
import argparse
import json
import os
import signal
import subprocess
import sys
import time
import uuid

ROOT=Path(__file__).resolve().parents[2]
FIXTURE=ROOT/'workbench/runtime/round2-acceptance'
AREA=ROOT/'workbench/runtime/round2-processing-faults'
BASE={'root':str(AREA),'system1':str(ROOT/'system1'),'system1_config':str(FIXTURE/'config/config.json')}
COMMAND=[str(ROOT/'system2/.venv/bin/python'),'-m','pdf_extraction.orchestration.material_service']
ENV=dict(os.environ,PYTHONPATH=str(ROOT/'system2/src'))

def call(command,**kw):
    process=subprocess.run(COMMAND,input=json.dumps(dict(BASE,command='material_'+command,**kw)),capture_output=True,text=True,
        cwd=ROOT/'system2',env=ENV,timeout=900)
    reply=json.loads(process.stdout)
    if not reply.get('ok'):raise RuntimeError(reply.get('error'))
    return reply['data']

def mutate(action,material,**kw):
    return call(action,request=dict(request_id=str(uuid.uuid4()),material_id=material['id'],expected_revision=material['revision'],actor='Weijie Tang',**kw))

def main():
    global AREA, BASE
    parser=argparse.ArgumentParser(); parser.add_argument('--destination', type=Path, default=AREA)
    AREA=parser.parse_args().destination.resolve()
    if not AREA.is_relative_to(ROOT/'workbench/runtime'):raise ValueError('Use isolated workbench runtime directory')
    BASE=dict(BASE,root=str(AREA))
    AREA.mkdir(exist_ok=False)
    evidence={'scope':'isolated_parser_store_using_readonly_round2_source_handoff','started_at':time.time()}
    opened=call('open',request={'request_id':str(uuid.uuid4()),'source_id':'TS004','actor':'Weijie Tang'})
    material=opened.get('material',opened)
    block={'id':'fault-human-text','type':'text','text':'ENGINEERING manual work before parser interruption',
        'source_refs':[{'scope_id':material['scope'][0]['id'],**material['scope'][0].get('location',{})}]}
    material=mutate('save',material,blocks=[block])['material']
    start=mutate('extract',material);candidate=start['candidate'];material=start['material']
    log=AREA/'interrupted-parser-output.json'
    with log.open('w') as stdout:
        process=subprocess.Popen(COMMAND,stdin=subprocess.PIPE,stdout=stdout,stderr=subprocess.STDOUT,text=True,cwd=ROOT/'system2',env=ENV)
        process.stdin.write(json.dumps(dict(BASE,command='material_tick')));process.stdin.close()
        observed=[]
        for _ in range(3000):
            observed=list((AREA/'material-artifacts').rglob('pdf-native-*.json'))
            if observed:
                process.kill();break
            if process.poll() is not None:raise RuntimeError('Parser completed before interruption could be observed')
            time.sleep(.01)
        else:
            process.kill();raise RuntimeError('No real parser evidence appeared before bounded wait')
        returncode=process.wait(timeout=10)
    persisted=call('candidate',material_id=material['id'],candidate_id=candidate['id'])
    interrupted=call('read',material_id=material['id'])
    evidence['interruption']={'owned_pid':process.pid,'exit_code':returncode,'candidate_id':candidate['id'],
        'observed_native_artifacts':len(observed),'durable_status_after_kill':persisted['status'],
        'human_body_unchanged':interrupted['blocks']==[block],
        'input_revision':candidate['input_revision']}
    # An intentional new human input version must not be replaced by old-input output.
    edited=dict(block,text='ENGINEERING manual work changed after interruption')
    changed=mutate('save',interrupted,blocks=[edited])['material']
    old_artifacts={str(p.relative_to(AREA)):hashlib.sha256(p.read_bytes()).hexdigest() for p in observed}
    resumed=call('tick')
    final=call('read',material_id=material['id']);detail=call('candidate',material_id=material['id'],candidate_id=candidate['id'])
    evidence['resume']={'same_candidate':resumed['candidate']['id']==candidate['id'],'candidate_status':detail['status'],
        'stale_input_marked':resumed['candidate'].get('stale'), 'input_revision':detail['input_revision'],
        'current_content_revision':final['content_revision'],'human_body_preserved':final['blocks']==[edited],
        'interrupted_artifacts_preserved':all(hashlib.sha256((AREA/p).read_bytes()).hexdigest()==h for p,h in old_artifacts.items()),
        'attempt_directories':len(list((AREA/'material-artifacts'/material['id']/candidate['id']).iterdir()))}
    # Failure injection affects an isolated pinned copy only, after the Extract request.
    opened=call('open',request={'request_id':str(uuid.uuid4()),'source_id':'TS003','actor':'Weijie Tang'})
    small=opened.get('material',opened)
    small=mutate('save',small,blocks=[dict(block,id='small-human-text',source_refs=[{'scope_id':small['scope'][0]['id'],**small['scope'][0].get('location',{})}])])['material']
    queued=mutate('extract',small);small=queued['material'];failed_id=queued['candidate']['id']
    pinned=AREA/'material-originals'/(small['source']['content_hash']+'.pdf');holding=pinned.with_suffix('.pdf.fault-held')
    pinned.rename(holding)
    try:failed=call('tick')
    finally:holding.rename(pinned)
    idle=call('tick');retained=call('read',material_id=small['id'])
    retry=mutate('extract',retained);completed=call('tick');after=call('read',material_id=small['id'])
    evidence['failure_and_manual_retry']={'failed_candidate_id':failed_id,'failed_status':failed['candidate']['status'],
        'next_tick_status_without_new_request':idle['status'],'new_request_candidate_id':retry['candidate']['id'],
        'new_candidate_created':retry['candidate']['id']!=failed_id,'retry_result_status':completed['candidate']['status'],
        'human_body_preserved':after['blocks']==small['blocks'],
        'failed_candidate_retained':call('candidate',material_id=small['id'],candidate_id=failed_id)['status']=='failed',
        'pinned_original_restored':hashlib.sha256(pinned.read_bytes()).hexdigest()==small['source']['content_hash']}
    evidence['finished_at']=time.time()
    evidence['passed']=evidence['interruption']['durable_status_after_kill']=='running' and evidence['interruption']['human_body_unchanged'] and all(evidence['resume'][k] for k in ('same_candidate','stale_input_marked','human_body_preserved','interrupted_artifacts_preserved')) and evidence['failure_and_manual_retry']['failed_status']=='failed' and evidence['failure_and_manual_retry']['next_tick_status_without_new_request']=='idle' and all(evidence['failure_and_manual_retry'][k] for k in ('new_candidate_created','human_body_preserved','failed_candidate_retained','pinned_original_restored'))
    path=ROOT/'project-support/reports/human-led-round2-20260911/fault-evidence.json'
    report=json.loads(path.read_text()) if path.exists() else {};report['processing_fault']=evidence;path.write_text(json.dumps(report,indent=2))
    (AREA/'evidence.json').write_text(json.dumps(evidence,indent=2));print(json.dumps(evidence),flush=True)
if __name__=='__main__':main()
