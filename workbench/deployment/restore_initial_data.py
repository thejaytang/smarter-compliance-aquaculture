"""Verify and explicitly restore an initial seed into a fresh workspace."""
from io import BytesIO
import os
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile

def restore(root,archive,expected_sha256):
    root=Path(root).resolve();wb=root/'workbench'
    if Path(archive).stat().st_size>512*1024*1024:raise ValueError('Initial data is too large.')
    raw=Path(archive).read_bytes()
    if hashlib.sha256(raw).hexdigest()!=expected_sha256.strip().lower():raise ValueError('Initial data checksum differs.')
    with zipfile.ZipFile(BytesIO(raw)) as package:
        if package.getinfo('manifest.json').file_size>8*1024*1024:raise ValueError('Initial manifest is too large.')
        if json.loads(package.read('manifest.json')).get('schema')=='workbench-business-package/1':
            return restore_business(root,raw,expected_sha256.strip().lower())
    if (wb/'runtime/state/layout.json').exists() or any((wb/'workspace/databases').glob('*.sqlite')):
        raise ValueError('This installation already has work. Use Collaboration; initial data never overwrites saved work.')
    stage=wb/'runtime/backups/initial-import';stage.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(archive) as z:
        if len(z.namelist())!=len(set(z.namelist())):raise ValueError('Duplicate initial package entries.')
        m=json.loads(z.read('manifest.json'))
        if m.get('schema')!='source-initial-data/1' or set(z.namelist())!={'manifest.json',*m['files']}:raise ValueError('Invalid initial manifest.')
        if sum(i.file_size for i in z.infolist())>512*1024*1024:raise ValueError('Initial data is too large.')
        prepared=[]
        for name,e in m['files'].items():
            p=PurePosixPath(name)
            allowed=name.startswith('system1/Data/') or name in {'system1/Code/runtime/governance.sqlite','system1/Code/runtime/governance-migration-input.xlsx','system1/Code/runtime/logs/source-assessments.sqlite','system1/Requirement_Source_Registry.xlsx','workbench/runtime/workbench.sqlite'}
            if not allowed or p.is_absolute() or '..' in p.parts or '\\' in name:raise ValueError('Unexpected initial data path.')
            data=z.read(name)
            if len(data)!=e['bytes'] or hashlib.sha256(data).hexdigest()!=e['sha256']:raise ValueError('Initial content checksum differs.')
            target=stage/name
            if target.exists() and target.read_bytes()!=data:raise ValueError('An earlier initial-data attempt differs; preserve it before retrying.')
            prepared.append((target,data))
        for target,data in prepared:
            target.parent.mkdir(parents=True,exist_ok=True)
            if not target.exists():target.write_bytes(data)
    cfg=stage/'system1/Code/config';cfg.mkdir(parents=True,exist_ok=True)
    for name in ('config','schedule'):
        target=cfg/(name+'.json')
        if target.exists():continue
        value=json.loads((root/'workbench/config/system1'/(name+'.example.json')).read_text())
        if name=='config':
            value['governance_db']='../runtime/governance.sqlite';value.setdefault('random_qa',{})['enabled']=False
        else:value['enabled']=False
        target.write_text(json.dumps(value,indent=2))
    sys.path.insert(0,str(root/'workbench/backend/application'))
    from local_workbench.workspace_migration import migrate
    result=migrate(stage,wb,legacy_workbench=stage/'workbench')
    return {'status':'restored-and-migrated','files':len(prepared),'layout':result['schema'],'source_revision':m.get('source_revision')}


def restore_business(root, raw, digest):
    """Explicit first import of the four-store seed; never an update action."""
    from backend.shared.platform_support import exclusive_lock
    from backend.shared.workspace import Workspace
    from backend.shared.workspace_storage import alias
    from local_workbench.workspace_package import validate
    from local_workbench.workspace_migration import clone_file
    from local_workbench.workspace_integrity import inspect
    wb=root/'workbench';marker=wb/'runtime/state/layout.json'
    receipt=wb/'runtime/backups/initial-import/receipt.json'
    with exclusive_lock(wb/'runtime/initial-import.lock'):
        if marker.exists():raise ValueError('This installation already has work. Use Collaboration.')
        if receipt.exists():
            if json.loads(receipt.read_text()).get('sha256')!=digest:raise ValueError('An earlier initial import differs; preserve it before retrying.')
        elif any((wb/'workspace/databases').glob('*.sqlite')):
            raise ValueError('This installation already has work. Initial data never overwrites saved work.')
        _, manifest=validate(raw,allow_delivery=True)
        stage=receipt.parent/'prepared';stage.mkdir(parents=True,exist_ok=True)
        receipt.parent.mkdir(parents=True,exist_ok=True)
        temporary=receipt.with_suffix('.tmp');temporary.write_text(json.dumps({'sha256':digest,'package_id':manifest['id']}));temporary.replace(receipt)
        w=Workspace(wb)
        with zipfile.ZipFile(BytesIO(raw)) as package:
            for name in manifest['files']:
                if not name.startswith(('databases/','sources/','logs/')):continue
                target=stage/name;data=package.read(name)
                # Rebase local descriptors before staging, making retry byte-identical.
                if name.endswith('/offline-source.json'):
                    value=json.loads(data);value['source_root']=str(w.workspace/'sources/system1')
                    data=json.dumps(value).encode()
                elif name.startswith('sources/uploads/') and name.endswith('.json'):
                    value=json.loads(data)
                    if value.get('path'):
                        filename=str(value['path']).replace('\\','/').rsplit('/',1)[-1]
                        value['path']=str(w.workspace/Path(name).parent/filename)
                        data=json.dumps(value).encode()
                if target.exists() and target.read_bytes()!=data:raise ValueError('Prepared initial content differs.')
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        for source in stage.rglob('*'):
            if source.is_file():clone_file(source,w.workspace/source.relative_to(stage))
        cfg=json.loads((root/'workbench/config/system1/config.example.json').read_text())
        locations={'source_root':w.workspace/'sources/system1','manual_intake_root':w.workspace/'sources/system1/00_Human_Intake',
            'manual_intake_archive_root':w.workspace/'sources/intake-history','backup_root':w.runtime/'backups/system1',
            'log_root':w.runtime/'state/system1','workbook':w.runtime/'cache/Requirement_Source_Registry.xlsx',
            'discovery_candidate_inbox':w.runtime/'state/system1/discovery_candidates.json','governance_db':w.database('system1')}
        cfg.update({key:os.path.relpath(value,w.source_config.parent) for key,value in locations.items()})
        cfg['assessment_db']=cfg['governance_db'];cfg.setdefault('random_qa',{})['enabled']=False
        w.source_config.parent.mkdir(parents=True,exist_ok=True)
        if not w.source_config.exists():w.source_config.write_text(json.dumps(cfg,indent=2))
        schedule=w.source_config.with_name('schedule.json')
        if not schedule.exists():
            value=json.loads((root/'workbench/config/system1/schedule.example.json').read_text());value['enabled']=False
            schedule.write_text(json.dumps(value,indent=2))
        w.material_branch(w.materials)
        alias(w.runtime/'state/system1','source-assessments.sqlite',w.database('system1'))
        for branch in (w.workspace/'sources/collaboration/personal').iterdir() if (w.workspace/'sources/collaboration/personal').exists() else ():
            if branch.is_dir():w.material_branch(branch,'branch_'+branch.name.replace('-','')+'__')
        report=inspect(w.databases,w.workspace/'sources')
        result={'schema':'workbench-layout/1','status':'complete','initial_package_id':manifest['id'],
                'initial_sha256':digest,'verified_originals':len(report['originals']),'verified_bindings':len(report['bindings'])}
        temporary=marker.with_suffix('.tmp');temporary.write_text(json.dumps(result,indent=2));temporary.replace(marker)
        return dict(result,status='restored')
