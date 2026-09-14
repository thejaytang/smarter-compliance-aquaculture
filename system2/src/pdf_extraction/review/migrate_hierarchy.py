"""Backed-up Canonical hierarchy projection. Existing originals and patches stay intact."""
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import sqlite3
from pdf_extraction.sqlite_support import connect as connect_sqlite
from ..domains.requirements.review_hierarchy import project
from .workflow import Workflow
from .repairs import invalidate


def populate(doc,root):
    canonicals={}
    for ref in doc['canonical']:
        path=Path(ref['path']).resolve()
        if not path.is_relative_to(root):raise ValueError('canonical_artifact_mismatch')
        raw=path.read_bytes()
        if sha256(raw).hexdigest()!=ref['sha256']:raise ValueError('canonical_artifact_mismatch')
        canonicals[ref['sha256']]=json.loads(raw)
    before={u['id']:u.get('source_hierarchy') for u in doc['units']}
    doc['hierarchy_containers']=project(doc['units'],canonicals)
    changed=[u['id'] for u in doc['units'] if u.get('source_hierarchy')!=before[u['id']]]
    units={u['id']:u for u in doc['units']}
    for u in doc['units']:
        parent=u.get('hierarchy_edit',{}).get('parent_id',u.get('source_hierarchy',{}).get('parent_id'))
        if parent in units and parent not in u.get('dependencies',[]):u.setdefault('dependencies',[]).append(parent)
    doc['hierarchy_version']='canonical-hierarchy/1'
    return changed


def migrate(root):
    store=Workflow(root)
    backup=store.root/('workflow-before-hierarchy-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.sqlite')
    with store.connect() as db,connect_sqlite(backup) as target:db.backup(target)
    result=[]
    with store.transaction() as db:
        for row in db.execute('SELECT id,data FROM documents').fetchall():
            meta=json.loads(row['data'])
            if meta['source'].get('file_format')!='pdf' or meta.get('hierarchy_version'):continue
            doc=store._load(db,row['id']);changed=populate(doc,store.root)
            affected=invalidate({u['id']:u for u in doc['units']},changed)
            doc['revision']+=1
            record={'changed':len(changed),'containers':len(doc['hierarchy_containers']),'affected':affected,'backup':str(backup)}
            store._event(db,doc['id'],'hierarchy_projection',record);store._recompute(db,doc,store.policy(db));store._save(db,doc)
            result.append(dict(record,document_id=doc['id']))
    return {'backup':str(backup),'documents':result}
