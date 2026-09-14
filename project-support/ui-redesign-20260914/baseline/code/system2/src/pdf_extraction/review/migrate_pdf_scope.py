"""Explicit backed-up maintenance; callers must quiesce parsing and review writes."""
from datetime import datetime,timezone
import json
from pathlib import Path
import sqlite3
from .workflow import Workflow
from .repairs import invalidate
from ..domains.requirements.pdf_review_scope import localize


def changes(doc):
    revised=localize(doc['units'],doc.get('processed_pages',[]))
    old={u['id']:u for u in doc['units']}
    edges=[{'unit_id':u['id'],'before':old[u['id']].get('dependencies',[]),'after':u.get('dependencies',[])}
           for u in revised if u['id'] in old and u.get('dependencies',[])!=old[u['id']].get('dependencies',[])]
    return revised,edges,[u['id'] for u in revised if u['id'] not in old]


def migrate(root,apply=False):
    store=Workflow(root);reports=[];backup=None
    # Backup precedes mutation. The maintenance caller owns the stopped-write checkpoint.
    if apply:
        backup=store.root/('workflow-before-pdf-scope-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')+'.sqlite')
        with store.connect() as db,sqlite3.connect(backup) as target:db.backup(target)
    with store.transaction() as db:
        for row in db.execute('SELECT id,data FROM documents').fetchall():
            meta=json.loads(row['data'])
            if meta['source'].get('file_format')!='pdf' or meta.get('pdf_scope_version')=='pdf-pages/1':continue
            doc=store._load(db,row['id']);revised,edges,added=changes(doc)
            report={'document_id':doc['id'],'source_id':doc['source']['source_id'],
                'changed_units':len(edges),'new_page_checks':len(added),'edge_changes':edges}
            reports.append(report)
            if not apply:continue
            for u in revised:
                if u['id'] in added:u.update(version=1,edits={},touched=False,content_human=False,requirement_human=False,
                    classification='undetermined',content_status='pending',requirement_status='blocked')
            doc['units']=revised
            report['invalidated_units']=invalidate({u['id']:u for u in revised},[e['unit_id'] for e in edges])
            doc['revision']+=1;doc['pdf_scope_version']='pdf-pages/1'
            store._event(db,doc['id'],'pdf_coverage_scope_migration',dict({k:v for k,v in report.items() if k!='document_id'},method='pdf-pages/1',backup=str(backup)))
            store._recompute(db,doc,store.policy(db));store._save(db,doc)
    return {'status':'applied' if apply else 'preview','backup':str(backup) if backup else None,'documents':reports}


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('root',type=Path);p.add_argument('--apply',action='store_true')
    args=p.parse_args();print(json.dumps(migrate(args.root,args.apply),indent=2))
