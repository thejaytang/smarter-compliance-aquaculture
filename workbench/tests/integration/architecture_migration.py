"""Populated legacy migration and fault recovery using real owning services."""
from pathlib import Path
from tempfile import TemporaryDirectory
from contextlib import closing
from unittest.mock import patch
import json
import sqlite3
import uuid
from colleague_handoff import initial_seed,ROOT,ACTORS,TEXT
from local_workbench.server import Application
from backend.system3.requirements import Requirements
from backend.system3.interpretations import Interpretations,KEYS
from local_workbench.workspace_migration import migrate
from local_workbench.workspace_integrity import inspect
from local_workbench.workspace_package import capture,validate


def exercise(root):
    initial_seed(root);source=root/'seed-source';wb=root/'legacy-workbench'
    config=source/'system1/Code/config/config.json'
    app=Application(wb,system_root=ROOT/'workbench/backend/system1',config=config,start_workers=False)
    c=app.collaboration;actor=ACTORS[0]
    m=c.material_action(actor,'open',{'request_id':str(uuid.uuid4()),'source_id':'CS901'})
    ref=dict(m['scope'][0]['location'],scope_id=m['scope'][0]['id'])
    m=c.material_action(actor,'save',{'request_id':str(uuid.uuid4()),'material_id':m['id'],'expected_revision':m['revision'],
        'blocks':[{'id':'passage','type':'text','text':TEXT,'source_refs':[ref]}]})['material']
    r=Requirements(c);d=r.apply(actor,dict(request_id=str(uuid.uuid4()),action='start',material_id=m['id'],material_revision=m['revision'],block_id='passage'))['document']
    uid=next(iter(d['units']))
    for field,a,b in [('Subject',0,13),('Main Verb',19,24)]:
        d=r.apply(actor,dict(request_id=str(uuid.uuid4()),action='assign',session_id=d['id'],expected_revision=d['revision'],unit_id=uid,field=field,start=a,end=b))['document']
    s=Interpretations(c);fields={k:dict(value='',basis='unresolved',references=[],gaps=[]) for k in KEYS}
    fields['verification']['value']='Retain this exact human wording.'
    s.save(actor,dict(request_id=str(uuid.uuid4()),unit_id=uid,expected_revision=0,context_fingerprint=s.context(actor,uid)['fingerprint'],fields=fields))
    d=r.apply(actor,dict(request_id=str(uuid.uuid4()),action='assign',session_id=d['id'],expected_revision=3,unit_id=uid,field='Object',start=25,end=34))['document']
    with c.db() as db:
        before={t:list(db.execute('SELECT * FROM '+t)) for t in ('requirement_sessions','requirement_steps','requirement_units','requirement_interpretations','interpretation_history')}
    workflow=app.system2.runtime;app.close()
    # Fail after one destination DB is promoted. Retrying must complete the
    # same prepared migration, not replace data with an unrelated new snapshot.
    import local_workbench.workspace_migration as migration
    copy=migration.clone_file
    def fault(src,dst):
        if str(dst).endswith('workspace/databases/system2.sqlite'):raise OSError('injected interruption')
        return copy(src,dst)
    with patch.object(migration,'clone_file',side_effect=fault):
        try:migrate(source,wb,config=config,system2=workflow)
        except OSError as e:assert 'injected interruption' in str(e)
        else:raise AssertionError('Failure injection did not run')
    assert not (wb/'runtime/state/layout.json').exists()
    result=migrate(source,wb,config=config,system2=workflow)
    assert result['status']=='complete'
    assert migrate(source,wb,config=config,system2=workflow)['replayed']
    app=Application(wb,start_workers=False)
    try:
        with app.collaboration.db() as db:
            for table,old in before.items():assert list(db.execute('SELECT * FROM '+table))==old,table
        saved=Interpretations(app.collaboration).read(ACTORS[1],uid)
        assert saved['session_revision']==3 and saved['stale'] and saved['fields']['verification']['value']==fields['verification']['value']
        report=inspect(app.layout.databases,app.layout.workspace/'sources')
        assert len([b for b in report['bindings'] if b['kind']=='scd'])==1
        # A real package must carry all four snapshots and exactly their history.
        (app.layout.runtime/'settings/ai-provider.json').write_text('{"api_key":"secret-do-not-export"}')
        (app.layout.materials/'source-version.json').write_text('{"local_only_marker":true}')
        raw,manifest=capture(app.collaboration,actor,str(uuid.uuid4()),'delivery')
        import zipfile,io
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            assert not any(n.endswith(('source-version.json','workbook.json')) for n in z.namelist())
        logical,_=validate(raw,allow_delivery=True)
        assert b'secret-do-not-export' not in raw
        try:validate(raw)
        except ValueError as e:assert 'downstream delivery' in str(e)
        else:raise AssertionError('Delivery was incorrectly allowed as Collaboration')
        print(json.dumps({'status':'passed','populated_migration':True,'interrupted_promotion_recovered':True,'row_json_author_time_preserved':True,
            'old_scd_binding_preserved':True,'four_databases':True,'bindings':len(report['bindings']),'delivery_validated':True},indent=2))
    finally:app.close()

if __name__=='__main__':
    with TemporaryDirectory(prefix='workbench-migration-') as root:exercise(Path(root))
