"""Explicit stopped-service migration; old files are retained as recovery evidence."""
from contextlib import ExitStack, closing
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import os
import shutil
import sqlite3
from backend.shared.workspace import Workspace, owner, DATABASES
from backend.shared.platform_support import exclusive_lock, process_alive
from backend.shared.workspace_storage import copy_tables, alias

SCHEMA='workbench-layout/1'


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        remaining=os.fstat(stream.fileno()).st_size
        while remaining:
            chunk=stream.read(min(remaining,1024*1024))
            if not chunk:raise OSError('Incomplete file read: '+str(path))
            h.update(chunk);remaining-=len(chunk)
    return h.hexdigest()


def clone_file(source,target):
    target.parent.mkdir(parents=True,exist_ok=True)
    if target.exists():
        if sha(source)!=sha(target):raise ValueError('Migration destination already differs: '+str(target))
        return
    tmp=target.with_name(target.name+'.migration-tmp')
    with source.open('rb') as src,tmp.open('wb') as dst:
        left=source.stat().st_size
        while left:
            chunk=src.read(min(left,1024*1024))
            if not chunk:raise OSError('Incomplete source read')
            dst.write(chunk);left-=len(chunk)
        dst.flush();os.fsync(dst.fileno())
    if sha(tmp)!=sha(source):raise ValueError('Source changed during migration.')
    tmp.replace(target)


def migrate(project, workbench=None, system1=None, config=None, system2=None, legacy_workbench=None):
    project=Path(project).resolve();w=Workspace(workbench or project/'workbench')
    marker=w.runtime/'state/layout.json'
    if marker.exists():
        report=json.loads(marker.read_text())
        if report.get('schema')!=SCHEMA:raise ValueError('Unsupported workspace layout.')
        return dict(report,replayed=True)
    for service in (w.runtime/'server.json',w.runtime/'state/server.json'):
        if service.exists() and process_alive(json.loads(service.read_text())['pid']):
            raise ValueError('Stop the Workbench before migrating saved data.')
    source=Path(system1 or project/'system1')
    cfg_path=Path(config or source/'Code/config/config.json')
    cfg=json.loads(cfg_path.read_text())
    def old(key):return (cfg_path.parent/cfg[key]).resolve()
    legacy_runtime=Path(legacy_workbench or w.root)/'runtime'
    legacy=legacy_runtime/'workbench.sqlite'
    workflow=Path(system2 or project/'system2/runtime/workflow')
    stores={'system1':old('governance_db'),'system2':workflow/'workflow.sqlite','application':legacy}
    assessment=old('log_root')/'source-assessments.sqlite'
    if assessment.exists():stores['assessments']=assessment
    branches={p.parent.name:p for p in (legacy_runtime/'collaboration/personal').glob('*/workflow.sqlite')}
    stores.update({'branch_'+k:v for k,v in branches.items()})
    recovery=w.runtime/'backups/architecture-v1';snapshots=recovery/'databases';stage=recovery/'prepared'
    for folder in (snapshots,stage):folder.mkdir(parents=True,exist_ok=True)
    report_path=recovery/'migration.json'
    with ExitStack() as stack:
        stack.enter_context(exclusive_lock(w.runtime/'service.lock'))
        stack.enter_context(exclusive_lock(w.runtime/'state/service.lock'))
        for path in sorted(set(p for p in stores.values() if p.exists())):
            db=stack.enter_context(closing(sqlite3.connect(path,timeout=2)));db.execute('BEGIN IMMEDIATE')
        # A completed preparation is reused, rather than copying changed old
        # stores over a partly promoted migration after an interruption.
        if report_path.exists():
            report=json.loads(report_path.read_text())
        else:
            report={'schema':SCHEMA,'at':datetime.now(timezone.utc).isoformat(),'tables':{},'files':{},'legacy_stores':{k:str(v) for k,v in stores.items()},'status':'prepared'}
            for key,path in stores.items():
                if not path.exists():continue
                snap=snapshots/(key+'.sqlite')
                if snap.exists():snap.unlink() # only unpublished staging from an interrupted preparation
                with closing(sqlite3.connect(path)) as src,closing(sqlite3.connect(snap)) as dst:src.backup(dst)
            for path in stage.glob('*.sqlite'):path.unlink()
            for name in DATABASES:
                with closing(sqlite3.connect(stage/(name+'.sqlite'))) as db:db.execute('PRAGMA user_version=1')
            report['tables']['system1']=copy_tables(snapshots/'system1.sqlite',stage/'system1.sqlite')
            if (snapshots/'assessments.sqlite').exists():
                report['tables']['assessments']=copy_tables(snapshots/'assessments.sqlite',stage/'system1.sqlite')
            if (snapshots/'system2.sqlite').exists():report['tables']['system2']=copy_tables(snapshots/'system2.sqlite',stage/'system2.sqlite')
            for identity in branches:
                report['tables'][identity]=copy_tables(snapshots/('branch_'+identity+'.sqlite'),stage/'system2.sqlite',prefix='branch_'+identity.replace('-','')+'__')
            if (snapshots/'application.sqlite').exists():
                for name,key in (('system3_requirements','requirements'),('system3_scd','scd'),('system2','materials'),('application',None)):
                    report['tables'][name+'-application']=copy_tables(snapshots/'application.sqlite',stage/(name+'.sqlite'),include=lambda t,k=key:owner(t)==k,drop_cross_fk=key=='scd')
            else:
                with closing(sqlite3.connect(stage/'application.sqlite')):pass
            # Source companion is an explicit dependency, not a hidden fifth DB.
            with closing(sqlite3.connect(stage/'system1.sqlite')) as db:
                archive=db.execute('SELECT archive FROM state').fetchone()[0]
                clone_file(stores['system1'].parent/archive,w.workspace/'sources/governance-template.xlsx')
                db.execute("UPDATE state SET archive='../sources/governance-template.xlsx'");db.commit()
            copies=[(old('source_root'),w.workspace/'sources/system1'),(workflow,w.materials),
                    (legacy_runtime/'collaboration',w.workspace/'sources/collaboration'),
                    (legacy_runtime/'uploads',w.workspace/'sources/uploads')]
            for original,destination in copies:
                if not original.exists():continue
                for p in original.rglob('*'):
                    if not p.is_file() or p.name.endswith(('.sqlite','.sqlite3','-wal','-shm','.lock','.tmp')):continue
                    if 'packages' in p.relative_to(original).parts:continue
                    target=destination/p.relative_to(original)
                    if original==legacy_runtime/'uploads' and p.suffix=='.json':
                        value=json.loads(p.read_text());prior=Path(value.get('path',''))
                        if prior.is_absolute() and prior.parent==original:value['path']=str(target.parent/prior.name)
                        raw=json.dumps(value,ensure_ascii=False)+'\n'
                        target.parent.mkdir(parents=True,exist_ok=True)
                        if target.exists() and target.read_text()!=raw:raise ValueError('Migrated upload descriptor differs.')
                        target.write_text(raw)
                    else:clone_file(p,target)
                    report['files'][str(target.relative_to(w.root))]=sha(target)
            for p in (legacy_runtime/'collaboration/packages').glob('*.zip'):
                clone_file(p,w.workspace/'packages/collaboration'/p.name)
            # Local-only files stay local; record no credentials in the report.
            for p in legacy_runtime.glob('*.json'):
                if p.name=='server.json':continue
                folder='state' if p.name=='listen-port.json' else 'settings'
                clone_file(p,w.runtime/folder/p.name)
            for p in cfg_path.parent.glob('*.json'):
                if p.name in {'config.json','schedule.json'}:continue
                clone_file(p,w.source_config.parent/p.name)
            newcfg=dict(cfg)
            for key in ('source_root','manual_intake_root','manual_intake_archive_root','backup_root','log_root','workbook','discovery_candidate_inbox','governance_db'):
                locations={'source_root':w.workspace/'sources/system1','manual_intake_root':w.workspace/'sources/system1/00_Human_Intake',
                    'manual_intake_archive_root':w.workspace/'sources/intake-history','backup_root':w.runtime/'backups/system1',
                    'log_root':w.runtime/'state/system1','workbook':w.runtime/'cache/Requirement_Source_Registry.xlsx',
                    'discovery_candidate_inbox':w.runtime/'state/system1/discovery_candidates.json','governance_db':w.database('system1')}
                newcfg[key]=os.path.relpath(locations[key],w.source_config.parent)
            newcfg['assessment_db']=newcfg['governance_db']
            w.source_config.parent.mkdir(parents=True,exist_ok=True)
            cfg_target=stage/'config.json';cfg_target.write_text(json.dumps(newcfg,indent=2)+'\n')
            for p in old('log_root').glob('*'):
                if p.is_file() and p.name!='source-assessments.sqlite' and not p.name.endswith(('-wal','-shm','.lock')):
                    target=w.runtime/'state/system1'/p.name
                    target.parent.mkdir(parents=True,exist_ok=True)
                    if p.suffix in {'.sqlite','.sqlite3'}:
                        with closing(sqlite3.connect(p)) as src,closing(sqlite3.connect(target)) as dst:src.backup(dst)
                    else:clone_file(p,target)
            schedule=cfg_path.with_name('schedule.json')
            if schedule.exists():clone_file(schedule,w.source_config.with_name('schedule.json'))
            report['prepared_hashes']={p.name:sha(p) for p in stage.iterdir() if p.is_file()}
            report_path.write_text(json.dumps(report,indent=2)+'\n')
        for name in DATABASES:
            p=stage/(name+'.sqlite')
            if sha(p)!=report['prepared_hashes'][p.name]:raise ValueError('Prepared migration changed.')
            with closing(sqlite3.connect(p)) as db:
                if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok' or db.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Prepared database integrity failed: '+name)
            clone_file(p,w.database(name))
        clone_file(stage/'application.sqlite',w.journal)
        clone_file(stage/'config.json',w.source_config)
        w.material_branch(w.materials)
        alias(w.runtime/'state/system1','source-assessments.sqlite',w.database('system1'))
        for identity in branches:w.material_branch(w.workspace/'sources/collaboration/personal'/identity,'branch_'+identity.replace('-','')+'__')
        from local_workbench.workspace_integrity import inspect
        verified=inspect(w.databases,w.workspace/'sources')
        report['verified_bindings']=len(verified['bindings'])
        report['verified_originals']=len(verified['originals'])
        report['status']='complete'
        temporary=marker.with_suffix('.tmp');temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(marker)
        return report
