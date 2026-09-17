import pathlib,sqlite3,json,hashlib,contextlib,datetime
root=pathlib.Path('/Users/tang/Desktop/smarter-compliance-aquaculture/05_Working area of requirements side')
dest=pathlib.Path('/tmp/sc-full-backup-20260914/consistent-databases')
paths=['system1/Code/runtime/governance.sqlite','system1/Code/runtime/logs/source-assessments.sqlite','system1/Code/runtime/logs/leader_state.sqlite','system2/runtime/workflow/workflow.sqlite','workbench/runtime/workbench.sqlite','system2/runtime/jobs.sqlite3']
paths += [str(p.relative_to(root)) for p in (root/'workbench/runtime/collaboration/personal').rglob('workflow.sqlite')]
paths=[p for p in paths if (root/p).exists()]
report={'started_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'method':'Simultaneous SQLite writer reservations across current owning stores, separate read-only online backups, integrity_check on each snapshot','stores':[]}
with contextlib.ExitStack() as stack:
    for f in sorted(paths):
        db=sqlite3.connect((root/f).as_uri()+'?mode=rw',uri=True,timeout=5);stack.callback(db.close);db.execute('BEGIN IMMEDIATE')
    for f in paths:
        target=dest/f;target.parent.mkdir(parents=True,exist_ok=True)
        with contextlib.closing(sqlite3.connect((root/f).as_uri()+'?mode=ro',uri=True)) as src,contextlib.closing(sqlite3.connect(target)) as out:
            src.backup(out);check=out.execute('PRAGMA integrity_check').fetchall();assert check==[('ok',)],check
            tables=[r[0] for r in out.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
            counts={t:out.execute('SELECT COUNT(*) FROM "'+t.replace('"','""')+'"').fetchone()[0] for t in tables}
            extra={}
            if 'actors' in tables:extra['actors']=[r[0] for r in out.execute('SELECT name FROM actors ORDER BY name')]
            if 'history' in tables and 'actor' in [r[1] for r in out.execute('PRAGMA table_info(history)')]:extra['history_by_actor']=[list(r) for r in out.execute('SELECT actor,COUNT(*) FROM history GROUP BY actor')]
        report['stores'].append({'path':f,'bytes':target.stat().st_size,'sha256':hashlib.sha256(target.read_bytes()).hexdigest(),'integrity':'ok','table_counts':counts,**extra})
        print('SNAPSHOT',f,target.stat().st_size,flush=True)
report['completed_at']=datetime.datetime.now(datetime.timezone.utc).isoformat()
(dest/'DATABASE-SNAPSHOT.json').write_text(json.dumps(report,indent=2)+'\n')
print('COMPLETE',len(paths),flush=True)
