"""Isolated recovery exercise using retained engineering fixtures, never live decisions."""
from pathlib import Path
import hashlib
import argparse
from contextlib import closing
import json
import os
import shutil
import signal
import sqlite3
import subprocess
import sys
import time
from urllib.request import urlopen

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT/'workbench/backend/application'))
from local_workbench.recovery import backup, restore, digest, SOURCE_DECLARATIONS, extract_code


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('--destination', type=Path, default=ROOT/'workbench/runtime/round2-recovery-exercise')
    area = parser.parse_args().destination.resolve()
    area.mkdir(exist_ok=False)
    source = area/'source-project'; source.mkdir()
    prior = ROOT/'workbench/runtime/human-led-acceptance'
    config = json.loads((ROOT/'workbench/backend/system1/Code/config/config.json').read_text()); config['random_qa']={'enabled': False}
    path=source/'workbench/backend/system1/Code/config/config.json'; path.parent.mkdir(parents=True); path.write_text(json.dumps(config))
    for old, new in [(prior/'Data',source/'system1/Data'),(prior/'governance',source/'workbench/backend/system1/Code/runtime'),
                     (prior/'workbench/runtime/system2-workflow',source/'system2/runtime/workflow')]:
        shutil.copytree(old,new)
    shutil.copy2(prior/'source-register.xlsx', source/'system1/Requirement_Source_Registry.xlsx')
    path=source/'workbench/runtime/workbench.sqlite'; path.parent.mkdir(parents=True)
    shutil.copy2(prior/'workbench/runtime/workbench.sqlite',path)
    # Empty supplemental stores are explicit engineering fixtures; no normal data copied.
    for relative in ('workbench/backend/system1/Code/runtime/logs/source-assessments.sqlite','workbench/backend/system1/Code/runtime/logs/leader_state.sqlite','system2/runtime/jobs.sqlite3'):
        target=source/relative; target.parent.mkdir(parents=True,exist_ok=True)
        with sqlite3.connect((ROOT/relative).as_uri()+'?mode=ro',uri=True) as original, sqlite3.connect(target) as db:
            for (sql,) in original.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY type DESC"):
                db.execute(sql)
    # Establish paths for this NEW fixture, before taking its recovery baseline.
    path=source/'system2/runtime/workflow/workflow.sqlite'
    with sqlite3.connect(path) as db:
        for table in ('material_documents','material_revisions','material_candidates','material_receipts','material_conflicts'):
            columns=list(db.execute('PRAGMA table_info('+table+')'))
            for col in columns:
                if col[2].upper() == 'TEXT':
                    name='"'+col[1]+'"'
                    db.execute('UPDATE '+table+' SET '+name+'=replace('+name+',?,?)',
                        (str(prior/'workbench/runtime/system2-workflow'),str(source/'system2/runtime/workflow')))
        materials=[json.loads(row[0]) for row in db.execute('SELECT data FROM material_documents')]
        material=next(item for item in materials if item['source']['source_id']=='TS003')
    for rel in ('workbench/backend/system1/Code/src', 'workbench/backend/system2/src', 'workbench/backend/application', 'workbench/ui'):
        (source/rel).symlink_to(ROOT/rel, target_is_directory=True)
    for relative in SOURCE_DECLARATIONS:
        if (ROOT/relative).is_file():
            target=source/relative; target.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(ROOT/relative,target)
    shutil.copytree(ROOT/'system2/config/schemas',source/'system2/config/schemas')
    package=area/'backup'; restored=area/'restored'
    before=backup(source,package); restoration=restore(package,restored)
    code=area/'matching-code'; source_result=extract_code(package,code)
    for relative in ('workbench/backend/system1/Code/.venv', 'system2/.venv', 'workbench/.venv'):
        (code/relative).symlink_to(ROOT/relative, target_is_directory=True)
    # The original fixture root and package asset tree are unavailable throughout HTTP reads.
    source.rename(area/'source-offline'); (package/'files').rename(package/'files-offline')
    command=[str(ROOT/'workbench/.venv/bin/python'),'-m','local_workbench.recovery','serve-restored',str(restored),'--code-root',str(code)]
    with (area/'server.log').open('w') as log:
        process=subprocess.Popen(command,stdout=log,stderr=log,env=dict(os.environ,PYTHONPATH=str(code/'workbench/backend/application')))
    evidence={'scope':'isolated_engineering_only','backup':before,'restore':restoration,'source_snapshot':source_result,'source_loaded_from_archive':True,'environments_reused_readonly':True,'original_root_available':source.exists(),'package_files_available':(package/'files').exists()}
    try:
        marker=restored/'workbench/runtime/server.json'
        for _ in range(150):
            if marker.exists():break
            if process.poll() is not None:raise RuntimeError((area/'server.log').read_text())
            time.sleep(.1)
        state=json.loads(marker.read_text()); url=f"http://127.0.0.1:{state['port']}"
        with urlopen(url+'/api/material?id='+material['id']) as response: actual=json.load(response)
        evidence['all_materials'] = []
        for saved in materials:
            with urlopen(url+'/api/material?id='+saved['id']) as response: reopened=json.load(response)
            with urlopen(url+'/api/material/history?id='+saved['id']) as response: history=json.load(response)
            evidence['all_materials'].append({'id': saved['id'], 'body_preserved': reopened['blocks']==saved['blocks'],
                'confirmation_preserved': reopened.get('confirmation')==saved.get('confirmation'),
                'has_confirmation': bool(saved.get('confirmation')), 'history_count': history.get('total')})
        evidence['material_identity_preserved']=actual['id']==material['id']
        evidence['body_preserved']=actual['blocks']==material['blocks']
        evidence['confirmation_preserved']=actual.get('confirmation')==material.get('confirmation')
        with urlopen(url+'/api/material/original?id='+material['id']) as response:
            evidence['original_sha256']=hashlib.sha256(response.read()).hexdigest()
        evidence['original_identity_preserved']=evidence['original_sha256']==material['source']['content_hash']
        with urlopen(url+'/api/material/reader?id='+material['id']+'&page=1') as response:
            reader=json.load(response); evidence['reader_kind']=reader['kind']; evidence['page_image_present']=bool(reader.get('image') or reader.get('image_data') or reader.get('image_base64') or reader.get('image_data_url') or reader.get('page_image'))
            evidence['reader_keys']=list(reader)
        evidence['restored_filesystem_aliases']=[str(path.relative_to(restored)) for path in restored.rglob('*') if path.is_symlink()]
        evidence['personal_workspace_created']=(restored/'workbench/runtime/collaboration/personal').exists()
        evidence['all_required_reads_pass']=not evidence['restored_filesystem_aliases'] and not evidence['personal_workspace_created'] and all(item['body_preserved'] and item['confirmation_preserved'] for item in evidence['all_materials']) and all(evidence[k] for k in ('material_identity_preserved','body_preserved','confirmation_preserved','original_identity_preserved'))
    finally:
        process.terminate();process.wait(timeout=15)
        (area/'evidence.json').write_text(json.dumps(evidence,indent=2))
    print(json.dumps(evidence))

if __name__=='__main__':main()
