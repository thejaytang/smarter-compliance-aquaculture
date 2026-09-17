"""Add registered synthetic scale sources and version histories to round-two only."""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
import shutil
import sys
import time
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'workbench/backend/system2/src'))
from pdf_extraction.orchestration.material_service import MaterialService

TARGET = ROOT/'workbench/runtime/round2-acceptance'


def seed():
    output = TARGET/'scale-materials.json'
    if output.exists(): raise ValueError('Scale fixture already seeded; preserve it')
    with sqlite3.connect(TARGET/'governance/governance.sqlite') as db:
        original = json.loads(db.execute("SELECT data FROM sources WHERE id='TS003'").fetchone()[0])
        for i in range(1, 101):
            record = deepcopy(original); sid = f'BB{i:03d}'; snapshot = sid+'-001'
            for k,v in dict(source_id=sid,snapshot_id=snapshot,source_title='ENGINEERING SCALE MATERIAL '+sid).items():record[k]=['value',v]
            filename=snapshot+'_material.pdf'
            source=TARGET/'Data'/record['folder_code'][1]/record['stored_filename'][1]
            target=source.parent/filename
            if not target.exists(): shutil.copy2(source,target)
            record['stored_filename']=['value',filename]
            rel=record['folder_code'][1]+'/'+filename
            db.execute('INSERT OR REPLACE INTO sources VALUES(?,?,?,?,?)',(sid,100+i,1,'INCLUDE',json.dumps(record)))
            db.execute('INSERT OR REPLACE INTO artifacts VALUES(?,?,?)',(rel,record['content_hash'][1],target.stat().st_size))
            db.execute('INSERT OR REPLACE INTO source_versions VALUES(?,?,?,?,?)',(sid,snapshot,rel,record['content_hash'][1],1))
    service = MaterialService(TARGET/'workbench/runtime/system2-workflow',ROOT/'system1',TARGET/'config/config.json')
    materials = []; start=time.perf_counter()
    for i in range(1,101):
        sid=f'BB{i:03d}'
        opened=service.open(dict(request_id=str(uuid.uuid4()),actor='Engineering fixture',source_id=sid))
        m=opened.get('material',opened)
        blocks=[dict(id=f'b{n}',type='text',text=f'ENGINEERING content block {n}',source_refs=[{'scope_id':f'page:{n%3+1}','page':n%3+1}]) for n in range(10000 if i==1 else 30)]
        for revision in range(1,20):
            blocks[0]['text']=f'ENGINEERING version {revision}'
            m=service.store.save(dict(request_id=str(uuid.uuid4()),actor='Engineering fixture',material_id=m['id'],expected_revision=m['revision'],blocks=deepcopy(blocks)))['material']
        materials.append(dict(id=m['id'],source_id=sid,revision=m['revision'],blocks=len(blocks)))
        if i%10==0: print('Seeded',i,'materials',round(time.perf_counter()-start,2),'seconds',flush=True)
    output.write_text(json.dumps(materials,indent=2))
    print('Scale seed complete',flush=True)


if __name__=='__main__': seed()
