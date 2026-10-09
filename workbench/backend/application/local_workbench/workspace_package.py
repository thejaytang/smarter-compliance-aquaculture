"""Coordinated business snapshots with a logical, non-overwriting merge payload."""
from contextlib import closing
from datetime import datetime, timezone
from io import BytesIO
from pathlib import PurePosixPath
from backend.shared.filesystem import FilePath as Path, temporary_directory
import hashlib
import json
import os
import sqlite3
import uuid
import zipfile
from backend.shared.workspace import DATABASES, Workspace
from local_workbench.workspace_migration import clone_file, sha
from local_workbench.workspace_integrity import inspect, canonical, validate_logical
from backend.shared.collaboration_exchange import pack
from backend.shared.collaboration_package import _path

SCHEMA='workbench-business-package/1'
MAX_BYTES=512*1024*1024


class DeliveryPackage:
    def __init__(self,c):self.c=c
    def export(self,actor,request):
        from local_workbench.collaboration import named
        actor=named(actor);identity=str(uuid.UUID(request['request_id']))
        with self.c.lock:
            self.c.claim_request('delivery-export',identity,'full',actor)
            old=self.c.get('delivery_export',identity)
            if old:return old
            raw,m=capture(self.c,actor,identity,'delivery')
            folder=self.c.layout.workspace/'packages/delivery';path=folder/(identity+'.zip')
            tmp=path.with_suffix('.tmp');tmp.write_bytes(raw);tmp.replace(path)
            result={'id':identity,'filename':'workbench-delivery-'+identity[:8]+'.zip','bytes':len(raw),
                'originals':len(m['originals']),'actor':actor,'at':m['at']}
            self.c.put('delivery_export',identity,result);return result
    def download(self,actor,identity):
        from local_workbench.collaboration import named
        named(actor);identity=str(uuid.UUID(identity));info=self.c.get('delivery_export',identity)
        if not info:raise ValueError('Prepare a downstream delivery first.')
        return (self.c.layout.workspace/'packages/delivery'/(identity+'.zip')).read_bytes(),info['filename']


def is_bundle(raw):
    if len(raw)>MAX_BYTES:raise ValueError('Business package is too large.')
    try:
        with zipfile.ZipFile(BytesIO(raw)) as z:
            if z.getinfo('manifest.json').file_size>8*1024*1024:raise ValueError('Manifest is too large.')
            return json.loads(z.read('manifest.json')).get('schema')==SCHEMA
    except (KeyError,ValueError,zipfile.BadZipFile):return False


def capture(c,actor,identity,kind='collaboration'):
    if kind not in {'collaboration','delivery'}:raise ValueError('Unknown package purpose.')
    w=c.layout
    if not w:raise ValueError('Migrate this workspace before exporting four business databases.')
    from local_workbench.server import Application
    from local_workbench.full_snapshot import FullSnapshot, SCHEMA as LOGICAL_SCHEMA, PROJECT
    with c.lock,temporary_directory(prefix='wbs-') as temporary:
        stage=Path(temporary);export=stage/'export';frozen=Workspace(stage/'workbench')
        (export/'databases').mkdir(parents=True)
        # Every write reservation is held until every DB and source is copied.
        with w.freeze():
            for name in DATABASES:
                dest=export/'databases'/(name+'.sqlite')
                with closing(sqlite3.connect(w.database(name))) as src,closing(sqlite3.connect(dest)) as out:src.backup(out)
                clone_file(dest,frozen.database(name))
            for p in (w.workspace/'sources').rglob('*'):
                if not p.is_file() or p.name.startswith('.') or p.name.endswith(('.lock','-wal','-shm','.tmp','.log')):continue
                rel=p.relative_to(w.workspace/'sources')
                if rel.parts[0]=='processing' and p.name in {'workbook.json','source-version.json'}:continue
                if p.suffix in {'.sqlite','.sqlite3'}:raise ValueError('Unexpected database among source attachments: '+str(rel))
                clone_file(p,export/'sources'/rel);clone_file(p,frozen.workspace/'sources'/rel)
        report=inspect(export/'databases',export/'sources')
        # The logical merge is derived from the frozen copies, so it cannot
        # race a later live save. Its working journals are never exported.
        config=json.loads(w.source_config.read_text())
        for key in ('source_root','manual_intake_root','manual_intake_archive_root','backup_root','log_root','workbook','discovery_candidate_inbox','governance_db','assessment_db'):
            if key in config:
                original=(w.source_config.parent/config[key]).resolve()
                if original.is_relative_to(w.root):config[key]=str(frozen.root/original.relative_to(w.root))
        frozen.source_config.parent.mkdir(parents=True,exist_ok=True)
        frozen.source_config.write_text(json.dumps(config))
        (frozen.runtime/'state/layout.json').write_text('{"schema":"workbench-layout/1"}')
        frozen.material_branch(frozen.materials)
        # Local path descriptors are operational pointers, not authored evidence.
        for p in (frozen.workspace/'sources').rglob('offline-source.json'):
            descriptor=json.loads(p.read_text());old=Path(descriptor.get('source_root',''))
            if old.is_absolute() and old.is_relative_to(w.root):descriptor['source_root']=str(frozen.root/old.relative_to(w.root))
            p.write_text(json.dumps(descriptor))
        app=Application(frozen.root,code_root=c.app.code_root,start_workers=False,reviewer=c.app.reviewer)
        try:
            current=FullSnapshot(app.collaboration).capture(actor)
            metadata={'id':identity,'schema':LOGICAL_SCHEMA,'project':PROJECT,'actor':actor,'at':datetime.now(timezone.utc).isoformat(),
                'nodes':current['nodes'],'heads':current['heads'],'evidence':current['evidence'],'history':FullSnapshot(app.collaboration).history()}
            logical=pack('collection',metadata,current['files'])
        finally:app.close()
        (export/'logical-workspace.zip').write_bytes(logical)
        (export/'logs').mkdir()
        for name,events in report.pop('history').items():
            (export/'logs'/(name+'.jsonl')).write_bytes(''.join(canonical(e)+'\n' for e in events).encode('utf-8'))
        readme='''WORKBENCH SAVED BUSINESS SNAPSHOT

Read the four databases with any SQLite reader in read-only mode; Workbench is
not required. Manifest file sizes and SHA-256 values verify the exact contents.
Its database entries give user_version, schema hashes and table inventories.
The full schema is readable in each file's sqlite_master table.

OWNERS
system1.sqlite: sources, source_versions, operations, source history/assessments.
system2.sqlite: material_revisions and retained branch-prefixed material tables.
system3_requirements.sqlite: requirement_steps and current Requirement heads.
system3_scd.sqlite: interpretation_history, saved S/C/D heads and source indexes.

TRACE A SAVED CHECK DESIGN
1. Read interpretation_history.body (JSON) in system3_scd.sqlite.
2. Use session_id and session_revision to find the exact requirement_steps row
   in system3_requirements.sqlite. Its body preserves units, Groups and links.
3. Follow material_id/material_revision to System2 material_revisions.data,
   including the branch tables listed in the manifest binding. Source segments
   identify the contributing blocks and their original location references.
4. Follow source_id, snapshot_id and content_hash to System1 source_versions;
   the manifest originals list supplies the matching file under sources/.
5. Foreign versions retain their original authors/time in received_history.
   received_sources and received_assets bind retained content-addressed files.

Saved JSON/history is authoritative; structure/citation tables are derived
indexes. Each logs/*.jsonl file is derived from the corresponding database and
contains actor, time, object identity, action, versions and operation identity.

S/C/D IS A CHECK DESIGN, NOT AN EXECUTED COMPLIANCE RESULT.
A delivery is a fixed artifact and cannot be merged through Collaboration.
A collaboration package must use preview/conflict resolution and explicit
apply in Workbench. Never replace local databases with these snapshots.
Credentials, local runtime configuration and diagnostic logs are excluded.
'''
        (export/'README.txt').write_text(readme)
        files={p.relative_to(export).as_posix():p for p in export.rglob('*') if p.is_file()}
        inventory={name:{'bytes':p.stat().st_size,'sha256':sha(p)} for name,p in files.items()}
        if sum(v['bytes'] for v in inventory.values())>MAX_BYTES:raise ValueError('Business package exceeds the supported 512 MiB limit.')
        manifest={'schema':SCHEMA,'format_version':1,'kind':kind,'id':identity,'actor':actor,'at':metadata['at'],
            'files':inventory,'databases':report['databases'],'bindings':report['bindings'],'originals':report['originals'],
            'missing_originals':[],'logical_payload':'logical-workspace.zip','check_design_executed':False}
        out=BytesIO()
        with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as archive:
            archive.writestr('manifest.json',canonical(manifest))
            for name,path in sorted(files.items()):archive.write(path,name)
        # A derived, immutable local projection for this exact package version.
        # Editing these files never edits the authoritative database history.
        history_root=w.workspace/'logs'/identity
        for p in (export/'logs').iterdir():clone_file(p,history_root/p.name)
        return out.getvalue(),manifest


def validate(raw,allow_delivery=False):
    if len(raw)>MAX_BYTES:raise ValueError('Business package is too large.')
    with zipfile.ZipFile(BytesIO(raw)) as z:
        names=z.namelist()
        if len(names)!=len(set(names)) or len(names)>20000:raise ValueError('Duplicate or excessive package entries.')
        seen=set()
        for n in names:
            normal=_path(n)
            if normal in seen:raise ValueError('Package path collision.')
            seen.add(normal)
        if sum(i.file_size for i in z.infolist())>MAX_BYTES:raise ValueError('Expanded package is too large.')
        if z.getinfo('manifest.json').file_size>8*1024*1024:raise ValueError('Manifest is too large.')
        m=json.loads(z.read('manifest.json'))
        if m.get('schema')!=SCHEMA or m.get('format_version')!=1 or m.get('kind') not in {'collaboration','delivery'}:raise ValueError('Unsupported business package.')
        if m['kind']=='delivery' and not allow_delivery:raise ValueError('This is a fixed downstream delivery. Use a Collaboration package to merge work.')
        if str(uuid.UUID(m['id']))!=m['id']:raise ValueError('Invalid package identity.')
        if set(names)!={'manifest.json',*m['files']}:raise ValueError('Package inventory differs.')
        files={}
        for name,entry in m['files'].items():
            if name not in {'README.txt','logical-workspace.zip'} and not name.startswith(('databases/','sources/','logs/')):raise ValueError('Local runtime/settings are forbidden in business packages.')
            data=z.read(name)
            if len(data)!=entry['bytes'] or hashlib.sha256(data).hexdigest()!=entry['sha256']:raise ValueError('Package checksum differs: '+name)
            files[name]=data
        required={'databases/'+n+'.sqlite' for n in DATABASES}
        if {n for n in files if n.startswith('databases/')}!=required:raise ValueError('Four declared business databases are required.')
        with temporary_directory(prefix='wbv-') as temp:
            root=Path(temp)
            for name,data in files.items():
                if name.startswith(('databases/','sources/')):
                    p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(data)
            report=inspect(root/'databases',root/'sources')
            for key in ('databases','bindings','originals'):
                if canonical(report[key])!=canonical(m.get(key)):raise ValueError('Snapshot '+key+' differs from manifest.')
            for name,events in report['history'].items():
                expected=''.join(canonical(e)+'\n' for e in events).encode()
                if files.get('logs/'+name+'.jsonl')!=expected:raise ValueError('Human history differs from its owning database.')
            validate_logical(root/'databases',files['logical-workspace.zip'],m)
        if m.get('check_design_executed') is not False:raise ValueError('A check design is not a compliance conclusion.')
        return files['logical-workspace.zip'],m


def retain_history(c,raw):
    """After explicit merge, retain foreign historical evidence without replacing
    local databases, versions or author identities. Replays deduplicate by hash.
    """
    if not c.layout:return
    logical,m=validate(raw)
    with zipfile.ZipFile(BytesIO(raw)) as z:
        events={name:[json.loads(line) for line in z.read('logs/'+name+'.jsonl').decode().splitlines() if line] for name in DATABASES}
        assets=[];attachments=[]
        for name,entry in m['files'].items():
            if not name.startswith('sources/'):continue
            digest=entry['sha256'];content=z.read(name)
            target=c.layout.workspace/'sources/received-assets'/digest
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists() and sha(target)!=digest:raise ValueError('Retained attachment differs.')
            if not target.exists():
                temporary=target.with_suffix('.tmp');temporary.write_bytes(content);temporary.replace(target)
            attachments.append({'package_id':m['id'],'original_path':name,'path':'received-assets/'+digest,'sha256':digest})
        for entry in m['originals']:
            content=z.read('sources/'+entry['path']);digest=entry['sha256']
            target=c.layout.workspace/'sources/received-files'/digest
            target.parent.mkdir(parents=True,exist_ok=True)
            if target.exists() and sha(target)!=digest:raise ValueError('Retained historical original differs.')
            if not target.exists():
                temporary=target.with_suffix('.tmp');temporary.write_bytes(content);temporary.replace(target)
            assets.append({**entry,'path':'received-files/'+digest})
        with c.db() as db:
            db.execute('BEGIN IMMEDIATE')
            for name,schema in [('system1','sources'),('system2','materials'),('system3_requirements','requirements'),('system3_scd','scd')]:
                db.execute(f'CREATE TABLE IF NOT EXISTS {schema}.received_history(id TEXT PRIMARY KEY,event_json TEXT NOT NULL)')
                for event in events[name]:
                    value=canonical(event);identity=hashlib.sha256(value.encode()).hexdigest()
                    db.execute(f'INSERT OR IGNORE INTO {schema}.received_history VALUES(?,?)',(identity,value))
            db.execute('CREATE TABLE IF NOT EXISTS sources.received_sources(id TEXT PRIMARY KEY,body TEXT NOT NULL)')
            for entry in assets:
                value=canonical(entry);identity=hashlib.sha256(value.encode()).hexdigest()
                db.execute('INSERT OR IGNORE INTO sources.received_sources VALUES(?,?)',(identity,value))
            db.execute('CREATE TABLE IF NOT EXISTS materials.received_assets(id TEXT PRIMARY KEY,body TEXT NOT NULL)')
            for entry in attachments:
                value=canonical(entry);identity=hashlib.sha256(value.encode()).hexdigest()
                db.execute('INSERT OR IGNORE INTO materials.received_assets VALUES(?,?)',(identity,value))
