"""Read-only cross-store checks and authoritative human-history projection."""
from contextlib import ExitStack, closing
import hashlib
import json
import sqlite3
from pathlib import Path
from backend.shared.workspace import DATABASES
from local_workbench.workspace_migration import sha


def canonical(value):return json.dumps(value,sort_keys=True,ensure_ascii=False,separators=(',',':'))
def tables(db):return {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
def rows(db,table):
    if table not in tables(db):return []
    return [dict(r) for r in db.execute('SELECT * FROM "'+table+'"')]


def validate_logical(databases, payload, manifest):
    """Reject a logical merge whose saved content differs from its snapshots.

    Prior sync nodes remain valid retained branches. Newly projected heads must
    be backed by owning saved rows; imported SQLite is opened read-only only.
    """
    from backend.shared.collaboration_exchange import unpack
    from local_workbench.snapshot_workspace import material_value
    from local_workbench.snapshot_graph import validate_graph
    package=unpack(payload);meta=package['metadata']
    if meta.get('id')!=manifest['id'] or meta.get('actor')!=manifest['actor'] or meta.get('at')!=manifest['at']:
        raise ValueError('Logical package identity differs from snapshot.')
    validate_graph(meta['nodes'],meta['heads'])
    with ExitStack() as stack:
        stores={}
        for name in DATABASES:
            db=stack.enter_context(closing(sqlite3.connect((Path(databases)/(name+'.sqlite')).resolve().as_uri()+'?mode=ro&immutable=1',uri=True)))
            db.row_factory=sqlite3.Row;db.execute('PRAGMA trusted_schema=OFF');db.execute('PRAGMA query_only=ON')
            stores[name]=db
        s1,s2,req,scd=(stores[n] for n in DATABASES)
        objects=rows(s2,'collaboration_objects')+rows(s1,'source_workspace_objects')
        retained={canonical(json.loads(r['data'])['value']) for r in objects if r['kind']=='sync_node'}
        materials={canonical(material_value(json.loads(r['data']))) for t in tables(s2) if t=='material_revisions' or t.endswith('__material_revisions') for r in rows(s2,t)}
        steps={canonical(json.loads(r['body'])) for r in rows(req,'requirement_steps')}
        interpretations={canonical(json.loads(r['body'])) for r in rows(scd,'interpretation_history')}
        sources={r['id']:{k:v[1] for k,v in json.loads(r['data']).items()} for r in rows(s1,'sources')}
        hashes={entry['sha256'] for entry in manifest['originals']}
        for path,raw in package['files'].items():
            digest=hashlib.sha256(raw).hexdigest()
            if path!='originals/'+digest or digest not in hashes:raise ValueError('Logical original is absent from source snapshots.')
        for key,heads in meta['heads'].items():
            for head in heads:
                value=meta['nodes'][head]['value']
                if canonical(value) in retained:continue
                if key.startswith('material:') and canonical(value) not in materials:
                    raise ValueError('Logical material differs from saved database history.')
                if key.startswith('requirements:'):
                    for session in value['sessions']:
                        for d in [session['document'],*[s['document'] for s in session['steps']]]:
                            if canonical(d) not in steps:raise ValueError('Logical Requirement differs from its owning database.')
                    for item in value['interpretations']:
                        for entry in item['history']:
                            if canonical(entry['document']) not in interpretations:raise ValueError('Logical S/C/D differs from its owning database.')
                if key.startswith('source:') and value.get('source_id') in sources:
                    source=sources[value['source_id']]
                    for field in ('source_id','content_hash','snapshot_id','stored_filename'):
                        if (value.get(field) or '')!=(source.get(field) or ''):raise ValueError('Logical source binding differs from its owning database.')


def inspect(databases, sources=None):
    """Validate saved bindings, including old SCD -> old Requirement revisions."""
    report={'schema':'workspace-integrity/1','databases':{},'bindings':[],'originals':[],'history':{}}
    with ExitStack() as stack:
        stores={}
        for name in DATABASES:
            path=Path(databases)/(name+'.sqlite')
            db=stack.enter_context(closing(sqlite3.connect(path.resolve().as_uri()+'?mode=ro&immutable=1',uri=True)))
            db.row_factory=sqlite3.Row
            db.execute('PRAGMA trusted_schema=OFF');db.execute('PRAGMA query_only=ON')
            if db.execute('PRAGMA integrity_check').fetchone()[0]!='ok':raise ValueError('Database integrity failed: '+name)
            if db.execute('PRAGMA foreign_key_check').fetchall():raise ValueError('Database foreign keys failed: '+name)
            schema=[tuple(r) for r in db.execute("SELECT type,name,sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type,name")]
            report['databases'][name]={'schema_version':db.execute('PRAGMA user_version').fetchone()[0],
                'schema_sha256':hashlib.sha256(canonical(schema).encode()).hexdigest(),
                'tables':{t:db.execute('SELECT count(*) FROM "'+t+'"').fetchone()[0] for t in sorted(tables(db)) if not t.startswith('sqlite_')}}
            stores[name]=db
        s1=stores['system1'];s2=stores['system2'];req=stores['system3_requirements'];scd=stores['system3_scd']
        if sources is not None:
            root=Path(sources).resolve()
            for row in rows(s2,'received_assets'):
                asset=json.loads(row['body']);p=(root/asset['path']).resolve()
                if not p.is_relative_to(root) or not p.is_file() or sha(p)!=asset['sha256']:
                    raise ValueError('Missing or changed retained attachment: '+asset['path'])
        versions=rows(s1,'source_versions')
        for row in rows(s1,'received_sources'):
            v=json.loads(row['body'])
            versions.append(dict(source_id=v['source_id'],snapshot_id=v['snapshot_id'],path=v['path'],sha256=v['sha256'],received=True))
        for v in versions:
            relative=('' if v.get('received') else 'system1/')+v['path'].replace('\\','/')
            if sources is not None:
                root=Path(sources).resolve();p=(root/relative).resolve()
                if not p.is_relative_to(root) or not p.is_file() or sha(p)!=v['sha256']:raise ValueError('Missing or changed source original: '+relative)
            report['originals'].append({'source_id':v['source_id'],'snapshot_id':v['snapshot_id'],'path':relative,'sha256':v['sha256']})
        material_versions={}
        for table in sorted(tables(s2)):
            if table=='material_revisions' or table.endswith('__material_revisions'):
                branch=table.removesuffix('material_revisions').removesuffix('__') or 'main'
                for row in rows(s2,table):
                    m=json.loads(row['data']);key=(m['id'],m['revision']);material_versions.setdefault(key,[]).append((branch,m))
                    source=m['source']
                    if not any(v['source_id']==source['source_id'] and v['sha256']==source['content_hash'] and v['snapshot_id']==source['snapshot_id'] for v in versions):
                        # An offline collaborator may retain source evidence in
                        # the shared catalog before it is adopted by System1.
                        retained=rows(s2,'collaboration_objects')+rows(s1,'source_workspace_objects')
                        if not any(source['content_hash'] in r['data'] and source['source_id'] in r['data'] for r in retained if r['kind'] in {'source_catalog','sync_source','baseline','work','sync_evidence'}):
                            raise ValueError('Material references an unknown source version: '+m['id'])
        steps={}
        for row in rows(req,'requirement_steps'):
            d=json.loads(row['body']);steps[(row['session_id'],row['revision'])]=d
            candidates=material_versions.get((d['material_id'],d['material_revision']),[])
            matches=[]
            for branch,m in candidates:
                blocks={b['id']:b for b in m['blocks']}
                parts=d.get('source_segments') or [{'block_id':d['block_id'],'text':d['text'],'source_refs':d.get('source_refs',[])}]
                if m['source']==d['source'] and all(p['block_id'] in blocks and blocks[p['block_id']]['text']==p['text'] and blocks[p['block_id']].get('source_refs',[])==p.get('source_refs',[]) for p in parts):matches.append(branch)
            if not matches:raise ValueError('Requirement has no matching saved material revision: '+d['id']+'/'+str(d['revision']))
            report['bindings'].append({'kind':'requirement','id':d['id'],'revision':d['revision'],'material_id':d['material_id'],'material_revision':d['material_revision'],'material_branches':matches,'source':d['source']})
        for row in rows(scd,'interpretation_history'):
            d=json.loads(row['body']);split=steps.get((d['session_id'],d['session_revision']))
            if not split or d['unit_id'] not in split['units']:raise ValueError('S/C/D references a missing Requirement version: '+d['unit_id'])
            report['bindings'].append({'kind':'scd','id':d['unit_id'],'revision':d['revision'],'session_id':d['session_id'],'session_revision':d['session_revision'],'material_id':split['material_id']})
        def event(actor,at,kind,identity,action,before,after,operation,evidence):
            return dict(actor=actor,at=at,object_type=kind,object_id=identity,action=action,before_version=before,after_version=after,operation_id=operation,evidence=evidence)
        history=[]
        for row in rows(s1,'history'):
            history.append(event(row['actor'],row['at'],row['entity'],row['entity_id'],'saved',max(0,row['revision']-1),row['revision'],'system1-history:'+str(row['sequence']),row))
        for row in rows(s1,'source_workspace_objects'):
            value=json.loads(row['data'])
            for i,h in enumerate(value.get('history',[])):
                if not isinstance(h,dict):continue
                revision=h.get('revision',i+1)
                history.append(event(h.get('actor',value.get('actor')),h.get('at'),row['kind'],row['key'],'saved',max(0,revision-1),revision,h.get('request_id') or row['kind']+':'+row['key']+':'+str(revision),h))
            if not value.get('history') and value.get('actor') and value.get('at'):
                history.append(event(value['actor'],value['at'],row['kind'],row['key'],'saved',None,value.get('revision'),value.get('request_id') or row['kind']+':'+row['key'],value))
        # Source drafts and exchange decisions retain their own author/time.
        report['history']['system1']=history
        history=[]
        for key,versions_ in material_versions.items():
            for branch,m in versions_:
                a=m.get('last_action',{})
                history.append(event(a.get('actor'),a.get('at'), 'material',m['id'],a.get('kind','retained'),max(0,m['revision']-1),m['revision'],m.get('request_id') or branch+':'+m['id']+':'+str(m['revision']),{'branch':branch,'data':m}))
        report['history']['system2']=history
        report['history']['system3_requirements']=[event(d.get('edited_by',d.get('created_by')),r['at'],'requirement',d['id'],r['action'],max(0,r['revision']-1),r['revision'],d.get('request_id') or d['id']+':'+str(r['revision']),d) for r in rows(req,'requirement_steps') for d in [json.loads(r['body'])]]
        report['history']['system3_scd']=[event(d.get('edited_by',r['actor']),r['at'],'scd',r['unit_id'],r['action'],max(0,r['revision']-1),r['revision'],d.get('request_id') or r['actor']+':'+r['unit_id']+':'+str(r['revision']),d) for r in rows(scd,'interpretation_history') for d in [json.loads(r['body'])]]
        for name,db in stores.items():
            own=report['history'][name]
            combined={canonical(e):e for e in [*own,*[json.loads(r['event_json']) for r in rows(db,'received_history')]]}
            report['history'][name]=[combined[k] for k in sorted(combined)]
    return report
