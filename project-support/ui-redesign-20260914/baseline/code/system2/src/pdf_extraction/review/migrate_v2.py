"""Explicit maintenance migration, preserving the original database and review history."""
import json
from copy import deepcopy
from .workflow import Workflow
from . import row_store
from ..domains.requirements.review_groups import group_units, order_units
from ..contracts.hashing import digest


def migrate(root):
    store=Workflow(root);mappings=[]
    def regroup(db,doc):
        if not doc['units'] or all(u.get('grouping_version') for u in doc['units']):return doc
        old=doc['units'];by_id={u['id']:u for u in old}
        from pathlib import Path
        canonicals={r['sha256']:json.loads(Path(r['path']).read_bytes()) for r in doc['canonical']}
        grouped=group_units(order_units(old,canonicals))
        for u in grouped:
            if u['id'] not in by_id:
                u.update(version=1,edits={},touched=False,content_human=False,requirement_human=False,classification='undetermined',content_status='pending',requirement_status='blocked')
            elif u.get('dependencies',[])!=by_id[u['id']].get('dependencies',[]):
                u['requirement_human']=False;u['requirement_parts']=[]
            u['grouping_version']='source-position/1'
        mapping={m['id']:u['id'] for u in grouped for m in u.get('members',[])}
        doc['units']=grouped;doc['revision']+=1
        store._event(db,doc['id'],'review_group_migration',{'method':'source-position/1','mapping':mapping,'previous_unit_count':len(old),'current_unit_count':len(grouped),'historical_decisions_preserved':True})
        store._recompute(db,doc,store.policy(db))
        mappings.append({'document_id':doc['id'],'source_id':doc['source']['source_id'],'before':len(old),'after':len(grouped)})
        return doc
    receipt=row_store.migrate(store,regroup)
    if receipt['status']=='already_current':
        with store.transaction() as db:
            for (did,) in db.execute('SELECT id FROM documents').fetchall():
                doc=store._load(db,did)
                if doc['units'] and not all(u.get('grouping_version') for u in doc['units']):store._save(db,regroup(db,doc))
    return dict(receipt,groups=mappings)


if __name__=='__main__':
    import sys
    print(json.dumps(migrate(sys.argv[1]),indent=2))
