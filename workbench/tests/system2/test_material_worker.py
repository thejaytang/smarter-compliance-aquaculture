import copy
import json
import os
from pathlib import Path
import sys
import pytest
from .test_material_service import integration, request
from pdf_extraction.orchestration.material_job import compute
from backend.shared.component_process import ComponentPool
from backend.shared.material_work import pending_work
from backend.shared.workspace_storage import alias


def test_three_stage_job_preserves_manual_edit_and_rejects_changed_binding(integration):
    service,_=integration
    opened=service.open(request(source_id='TS001'))
    started=service.mutate('extract',request(opened))
    job=service.prepare_job()
    assert pending_work(service.root)=={'run':True,'resolve':False}
    content=compute(service.root,job)
    assert content['status']=='candidate_available'
    material=service.store.read(opened['id'])
    block=dict(id='human',type='text',text='Retained manual text',source_refs=[{'scope_id':'html:document'}])
    saved=service.mutate('save',request(material,blocks=[block]))['material']
    bad=copy.deepcopy(job);bad['input_revision']+=1
    with pytest.raises(ValueError,match='candidate_input_changed'):service.finish_job(bad,content)
    finished=service.finish_job(job,content)
    assert finished['candidate']['stale']
    assert service.store.read(saved['id'])['blocks']==[block]
    assert pending_work(service.root)=={'run':False,'resolve':True}
    before=(service.root/'workflow.sqlite').read_bytes()
    pending_work(service.root)
    assert (service.root/'workflow.sqlite').read_bytes()==before


def test_worker_reuses_process_reads_new_work_and_recovers_after_exit(integration):
    service,_=integration
    workbench=Path(__file__).resolve().parents[2]
    component=workbench/'backend/system2'
    env=dict(os.environ,PYTHONPATH=os.pathsep.join(map(str,[component/'src',workbench,workbench/'backend/application'])),PYTHONUTF8='1')
    payload=dict(root=str(service.root),system1=str(service.system1),command='material_prepare-job')
    module='pdf_extraction.orchestration.material_service'
    pool=ComponentPool()
    try:
        def call():return pool.request(sys.executable,module,component,env,payload,30)
        assert call()=={'ok':True,'data':None}
        worker=next(iter(pool.workers.values()));process=worker.process
        assert call()=={'ok':True,'data':None}
        assert worker.process.pid==process.pid
        opened=service.open(request(source_id='TS001'))
        candidate=service.mutate('extract',request(opened))['candidate']
        assert call()['data']['candidate_id']==candidate['id']
        process.kill();process.wait(timeout=5)
        assert call()['data']['candidate_id']==candidate['id']
        assert worker.process.pid!=process.pid
        current=worker.process
    finally:pool.close()
    assert current.poll() is not None


def test_readonly_hint_preserves_unicode_branch_routing(tmp_path):
    import sqlite3
    runtime=tmp_path/'目录 æ #';runtime.mkdir()
    db=tmp_path/'owner.sqlite'
    with sqlite3.connect(db) as cx:
        cx.execute('CREATE TABLE branch_x__material_candidates(id TEXT,data TEXT)')
        cx.execute('INSERT INTO branch_x__material_candidates VALUES(?,?)',('x',json.dumps({'status':'running'})))
        cx.execute('CREATE TABLE material_candidates(id TEXT,data TEXT)')
    alias(runtime,'workflow.sqlite',db,'branch_x__')
    assert pending_work(runtime)=={'run':True,'resolve':False}
    assert not (runtime/'workflow.sqlite').exists()
